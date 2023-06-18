from __future__ import absolute_import, print_function, unicode_literals

import pytest

import entities


@pytest.fixture
def test_frameset_create(frameset_factory, test_db_cursor):
    pkid = frameset_factory("test")
    assert isinstance(pkid, str)
    test_db_cursor.execute("select * from frameset;")
    rec = test_db_cursor.fetchone()
    assert rec["pkid"] == pkid


def test_frameset_obj(frameset, test_db_cursor):
    fs = entities.Frameset.get(frameset)
    assert fs.pkid == frameset


@pytest.mark.usefixtures("mock_etcd")
def test_assign_frames_to_frameset(frameset_with_6_frames):
    fs = entities.Frameset(frameset_with_6_frames)
    child_frames = fs.child_frames
    assert len(child_frames) == 6


def test_frameset_obj_list(frameset_factory, test_db_cursor):
    fs_red = frameset_factory("red", orientation="H")
    fs_blue = frameset_factory("blue", orientation="H")
    fs_green = frameset_factory("green", orientation="V")
    all_fs = entities.Frameset.list()
    assert len(all_fs) == 3
    horiz_fs = entities.Frameset.list(orientation="H")
    assert len(horiz_fs) == 2
    horiz_names = [fs.name for fs in horiz_fs]
    assert "red" in horiz_names
    assert "blue" in horiz_names
    assert "green" not in horiz_names


def test_assign_album_to_frameset(frameset, album, test_db_cursor):
    fs = entities.Frameset.get(frameset)
    assert not fs.album_id
    fs.assign_album(album)
    # Reload the frameset
    fs = entities.Frameset.get(frameset)
    assert fs.album_id == album


@pytest.mark.usefixtures("mock_etcd")
def test_assign_album_to_frameset_subalbums(frameset, frameset_with_6_frames, album):
    fs = entities.Frameset.get(frameset)
    assert not fs.album_id
    ab = entities.Album.get(album)
    fs.assign_album(ab)
    # Get all the current albums
    album_names = [a.name for a in entities.Album.list()]
    for child in fs.child_frames:
        subalbum_name = ab.generate_subalbum_name(child.pkid)
        assert subalbum_name in album_names
    # Now un-assign the album
    fs.assign_album(None)
    # Get all the current albums
    album_names = [a.name for a in entities.Album.list()]
    for child in fs.child_frames:
        subalbum_name = ab.generate_subalbum_name(child.pkid)
        assert subalbum_name not in album_names


def test_new_frameset(test_db_cursor):
    fs = entities.Frameset(name="A New Frame")
    assert not fs.pkid
    fs.save()
    assert fs.pkid
