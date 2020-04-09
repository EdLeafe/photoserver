from __future__ import absolute_import, print_function, unicode_literals

import pytest

import entities


def test_image_create(image):
    img = entities.Image.get(image)
    assert img.pkid == image
