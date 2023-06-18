from __future__ import absolute_import, print_function, unicode_literals

import builtins
from mock import patch
import uuid
import warnings

import pymysql
import pytest

import db_create
import entities
import utils


@pytest.fixture(scope="function")
def test_db_cursor():
    """A db cursor for use in testing that cleans up after it's done."""
    db_name = "test_{}".format(uuid.uuid4().hex)
    cls = pymysql.cursors.DictCursor
    creds = utils.parse_creds()
    creds.pop("dbname", "")
    conn = pymysql.connect(
        host=creds.get("host"),
        user=creds["username"],
        passwd=creds["password"],
        charset="utf8",
        cursorclass=cls,
    )
    test_crs = conn.cursor()
    test_crs.execute("create database {};".format(db_name))
    conn.select_db(db_name)
    conn.db = db_name
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        db_create.main(test_crs)
    builtins.TEST_CURSOR = test_crs
    yield test_crs
    test_crs.execute("drop database if exists {};".format(db_name))
    delattr(builtins, "TEST_CURSOR")


def ensure_table(crs, name):
    sql = "select table_name from information_schema.tables where table_schema = %s and table_name = %s"
    res = crs.execute(sql, (crs.connection.db, name))
    if not res:
        create_name = "create_{}".format(name)
        mthd = getattr(db_create, create_name)
        mthd(crs)


@pytest.fixture
def mock_etcd():
    with patch("utils._get_etcd_client") as mock_client:
        yield mock_client


@pytest.fixture  # (scope="function")
def frame_factory(test_db_cursor):
    """Given a frame name, creates that frame record and returns its ID"""
    ensure_table(test_db_cursor, "frame")

    def make_frame(name, **kwargs):
        frame = entities.Frame(name=name, **kwargs)
        frame.save()
        return frame.pkid

    return make_frame


@pytest.fixture
def frame(frame_factory):
    pkid = frame_factory("test_frame")
    yield pkid


@pytest.fixture
def frame_obj(frame):
    yield entities.Frame.get(frame)


@pytest.fixture  # (scope="function")
def frameset_factory(test_db_cursor):
    """Given a frameset name, creates that frameset record and returns its ID"""
    ensure_table(test_db_cursor, "frameset")

    def make_frameset(name, **kwargs):
        frameset = entities.Frameset(name=name, **kwargs)
        frameset.save()
        return frameset.pkid

    return make_frameset


@pytest.fixture
def frameset(frameset_factory):
    pkid = frameset_factory("test_frameset")
    yield pkid


@pytest.fixture
def frameset_obj(frameset):
    yield entities.Frameset.get(frameset)


@pytest.fixture
def frameset_with_6_frames(frameset_obj, frame_factory, album, mock_etcd):
    frame_ids = [frame_factory(name="Frame {}".format(num)) for num in range(6)]
    frameset_obj.set_frames(frame_ids)
    yield frameset_obj.pkid


@pytest.fixture  # (scope="function")
def album_factory(test_db_cursor):
    """Given a album name, creates that album record and returns its ID"""
    ensure_table(test_db_cursor, "album")

    def make_album(name, **kwargs):
        album = entities.Album(name=name, **kwargs)
        album.save()
        return album.pkid

    return make_album


@pytest.fixture
def album(album_factory):
    pkid = album_factory("test_album")
    yield pkid


@pytest.fixture
def album_obj(album):
    yield entities.Album.get(album)


@pytest.fixture  # (scope="function")
def image_factory(test_db_cursor):
    """Given a image name, creates that image record and returns its ID"""
    ensure_table(test_db_cursor, "image")

    def make_image(name, **kwargs):
        img = entities.Image(name=name, **kwargs)
        img.save()
        return img.pkid

    return make_image


@pytest.fixture
def image(image_factory):
    pkid = image_factory("test_image")
    yield pkid


@pytest.fixture
def image_obj(image):
    yield entities.Image.get(image)
