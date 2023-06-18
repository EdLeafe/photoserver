from __future__ import absolute_import, print_function, unicode_literals

import pytest

import entities


def test_image_create(test_db_cursor, image):
    img = entities.Image.get(image)
    assert img.pkid == image


@pytest.mark.parametrize(
    "name, height, width",
    [("fred", 11, 22), ("akjsdhjkahs", 2634652, 823748372), ("douglas", 42, 24)],
)
def test_image_update(test_db_cursor, image, name, height, width):
    image_obj = entities.Image.get(image)
    image_obj.name = name
    image_obj.height = height
    image_obj.width = width
    image_obj.save()
    # Re-fetch the object, and verify that its attributes have been updated
    new_image_obj = entities.Image.get(image)
    assert new_image_obj.name == name
    assert new_image_obj.height == height
    assert new_image_obj.width == width
