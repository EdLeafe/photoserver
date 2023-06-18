from __future__ import absolute_import, print_function, unicode_literals

from collections import defaultdict
import random

import pytest

import entities
import exceptions as exc


@pytest.fixture
def random_1_to_50():
    yield random.randint(1, 50)


@pytest.fixture
def random_set_of_images(image_factory, random_1_to_50):
    yield [image_factory("img{}".format(num)) for num in range(random_1_to_50)]


@pytest.fixture
def set_of_20_images(image_factory):
    image_ids = [image_factory(name="Image {}".format(num)) for num in range(20)]
    yield image_ids


@pytest.fixture
def album_with_random_images(album, random_set_of_images, random_1_to_50):
    album_obj = entities.Album(album)
    assert album_obj.image_count == 0
    # Now add the images to the album
    album_obj.add_images(random_set_of_images)
    assert album_obj.image_count == random_1_to_50
    yield album_obj.pkid


@pytest.fixture
def album_with_20_images(album, set_of_20_images):
    album_obj = entities.Album(album)
    assert album_obj.image_count == 0
    # Now add the images to the album
    album_obj.add_images(set_of_20_images)
    yield album_obj.pkid


@pytest.fixture
def album_with_20_images_and_sub_albums(album_with_20_images, frameset_with_6_frames):
    album_obj = entities.Album(album_with_20_images)
    fs = entities.Frameset(frameset_with_6_frames)
    # Assign the album to the fs
    fs.assign_album(album_obj)
    # verify that it now has sub_albums
    assert album_obj.sub_albums
    yield album_obj.pkid


def test_add_image_to_album(image, album_with_random_images):
    album_obj = entities.Album(album_with_random_images)
    orig_count = album_obj.image_count
    album_obj.add_image(image)
    assert album_obj.image_count == orig_count + 1


def test_remove_image_from_album(album_with_random_images, random_set_of_images):
    album_obj = entities.Album(album_with_random_images)
    orig_count = album_obj.image_count
    image_id = random.choice(random_set_of_images)
    album_obj.remove_image(image_id)
    assert album_obj.image_count == orig_count - 1


def test_album_images(album_with_random_images, random_1_to_50):
    album_obj = entities.Album(album_with_random_images)
    images = album_obj.images
    assert len(images) == random_1_to_50
    for img in images:
        assert isinstance(img, entities.Image)


def test_album_image_ids(album_with_random_images, random_1_to_50):
    album_obj = entities.Album(album_with_random_images)
    image_ids = album_obj.image_ids
    assert len(image_ids) == random_1_to_50
    for img_id in image_ids:
        assert isinstance(img_id, str)
        assert len(img_id) == 36


def test_delete_album_by_name(album_factory):
    album_ids = [album_factory(name="album-{}".format(num)) for num in range(10)]
    id_to_delete = random.choice(album_ids)
    # Show that `get()` works for this ID
    album_to_delete = entities.Album.get(id_to_delete)
    name_to_delete = album_to_delete.name
    entities.Album.delete_by_name(name_to_delete)

    # Demonstrate the album for the deleted ID no longer exists
    with pytest.raises(exc.NotFound):
        deleted_album = entities.Album.get(id_to_delete)


@pytest.mark.usefixtures("mock_etcd")
def test_split_frameset(frameset_with_6_frames, album_with_20_images):
    fs = entities.Frameset.get(frameset_with_6_frames)
    assert not fs.album_id
    fs.assign_album(album_with_20_images)
    album_obj = entities.Album.get(album_with_20_images)
    # There should be 2 frames with 4 images, and 4 with 3 images
    image_count = defaultdict(int)
    for frame in fs.child_frames:
        frame_album_obj = entities.Album.get(frame.album_id)
        assert frame_album_obj.name == album_obj.generate_subalbum_name(frame.pkid)
        image_count[frame_album_obj.image_count] += 1
    assert set(image_count.keys()) == {3, 4}
    assert image_count[3] == 4
    assert image_count[4] == 2


@pytest.mark.usefixtures("mock_etcd")
def test_sub_albums_split_images(album_with_20_images_and_sub_albums):
    album_obj = entities.Album.get(album_with_20_images_and_sub_albums)
    sas = album_obj.sub_albums
    all_images = set(album_obj.image_ids)
    sub_images = set()
    for sa in album_obj.sub_albums:
        sub_images.update(sa.image_ids)
    assert sub_images == all_images


@pytest.mark.usefixtures("mock_etcd")
def test_album_reallocation(album_with_20_images_and_sub_albums, image_factory):
    album_obj = entities.Album.get(album_with_20_images_and_sub_albums)
    sas = album_obj.sub_albums
    # 4 of the sub_albums should have 3 images, and the other two should have 4
    image_counts = sorted([ab.image_count for ab in sas])
    assert image_counts == [3, 3, 3, 3, 4, 4]
    new_image_id = image_factory("New Image")
    album_obj.add_image(new_image_id)
    # Verify that the image was added to one of the sub_albums that had 3
    image_counts = sorted([ab.image_count for ab in sas])
    assert image_counts == [3, 3, 3, 4, 4, 4]


@pytest.mark.usefixtures("mock_etcd")
def test_album_deallocation(album_with_20_images_and_sub_albums, image_factory):
    album_obj = entities.Album.get(album_with_20_images_and_sub_albums)
    sas = album_obj.sub_albums
    sorted_low_to_hi = sorted(album_obj.sub_albums, key=lambda x: x.image_count)
    # Find an image that is in one of the larger sub_albums
    big_album = sorted_low_to_hi[-1]
    img = random.choice(big_album.images)
    assert img in big_album.images
    # Remove it from the parent album
    album_obj.remove_image(img)
    # Verify that it has been removed from big_album too
    assert img not in big_album.images
    # Now there should only be one sub_album with 4 images.
    sorted_low_to_hi = sorted(album_obj.sub_albums, key=lambda x: x.image_count)
    counts = [ab.image_count for ab in sorted_low_to_hi]
    assert counts == [3, 3, 3, 3, 3, 4]
    # Select an image from a small album
    small_album = sorted_low_to_hi[0]
    assert small_album.image_count == 3
    img = random.choice(small_album.images)
    assert img in small_album.images
    big_album = sorted_low_to_hi[-1]
    assert big_album.image_count == 4
    # Remove the image from the parent
    album_obj.remove_image(img)
    # Verify that the image was removed from the small_album
    assert img not in small_album.images
    # Verify that small_album's image_count was not reduced
    assert small_album.image_count == 3
    # Verify that an image was removed from big_album
    assert big_album.image_count == 3
