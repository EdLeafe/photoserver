from __future__ import absolute_import, print_function, unicode_literals

import pytest

import entities


@pytest.mark.usefixtures("mock_etcd")
def test_frame_create(frame_factory, test_db_cursor):
    pkid = frame_factory("test", description="Just testing")
    assert isinstance(pkid, str)
    test_db_cursor.execute("select * from frame;")
    rec = test_db_cursor.fetchone()
    assert rec["pkid"] == pkid
    assert rec["description"] == "Just testing"


@pytest.mark.usefixtures("mock_etcd")
def test_frame_set_album(frame_obj, album_obj, test_db_cursor):
    assert not frame_obj.album_id
    frame_obj.set_album(album_obj)
    assert frame_obj.album_id == album_obj.pkid


@pytest.mark.usefixtures("mock_etcd")
def test_after_get_no_frameset(frame_obj, test_db_cursor):
    """Ensure that the frame object with no frameset has an empty frameset name"""
    assert frame_obj.frameset_name == ""


@pytest.mark.usefixtures("mock_etcd")
def test_after_get_with_frameset(frameset_with_6_frames, test_db_cursor):
    """Ensure that the frame object contains its frameset name, if any."""
    frameset_obj = entities.Frameset.get(frameset_with_6_frames)
    frameset_name = frameset_obj.name
    for frame_obj in frameset_obj.child_frames:
        assert frame_obj.frameset_name == frameset_name
