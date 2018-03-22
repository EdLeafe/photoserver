from datetime import datetime
from functools import wraps, update_wrapper
import logging
from math import log
import os
from subprocess import Popen, PIPE
import uuid

from PIL import Image
import pymysql

from flask import make_response
import images


main_cursor = None
HOST = "dodb"
conn = None

LOG = logging.getLogger(__name__)


def runproc(cmd):
    proc = Popen([cmd], shell=True, stdin=PIPE, stdout=PIPE, stderr=PIPE,
            close_fds=True)
    stdout_text, stderr_text = proc.communicate()
    return stdout_text, stderr_text


def _parse_creds():
    with open("/home/ed/.dbcreds") as ff:
        lines = ff.read().splitlines()
    ret = {}
    for ln in lines:
        key, val = ln.split("=")
        ret[key] = val
    return ret


def connect():
    creds = _parse_creds()
    ret = pymysql.connect(host=HOST, user=creds["DB_USERNAME"],
            passwd=creds["DB_PWD"], db=creds["DB_NAME"], charset="utf8")
    return ret

def gen_uuid():
    return str(uuid.uuid4())

def get_cursor():
    global conn, main_cursor
    if not (conn and conn.open):
        LOG.debug("No DB connection")
        main_cursor = None
        conn = connect()
    if not main_cursor:
        LOG.debug("No cursor")
        main_cursor = conn.cursor(pymysql.cursors.DictCursor)
    return main_cursor

def commit():
    conn.commit()

def get_img_orientation(fpath):
    img = Image.open(fpath)
    width, height = img.size
    if width == height:
        orientation = "S"
    elif width > height:
        orientation = "H"
    else:
        orientation = "V"
    return orientation


def update_img_db(img_dir=None):
    """Great for restoring the image information after resetting the DB. It
    loses any custom keywords that may have been set, though.
    """
    img_dir = img_dir or images.IMAGE_FOLDER
    disk_images = os.listdir(img_dir)
    db_images = images.list_db_images()
    db_names = [db_img["name"] for db_img in db_images]
    for disk_img in disk_images:
        if disk_img in db_names:
            continue
        fpath = os.path.join(img_dir, disk_img)
        try:
            img = Image.open(fpath)
        except IOError:
            # Not a valid image file; delete maybe?
            continue
        # Add back to the database
        pkid = gen_uuid()
        name = disk_img
        keywords = ""
        width, height = img.size
        orientation = get_img_orientation(fpath)
        imgtype = img.format
        osstat = os.stat(fpath)
        size = osstat.st_size
        updated = datetime.fromtimestamp(osstat.st_ctime)
        sql = """
                insert into image (pkid, keywords, name, orientation, width,
                    height, imgtype, size, updated)
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s); """
        vals = (pkid, keywords, name, orientation, width, height, imgtype,
                size, updated)
        crs = get_cursor()
        crs.execute(sql, vals)
    # Save the db changes
    commit()


def update_image_thumbnails(img_dir=None):
    img_dir = img_dir or images.IMAGE_FOLDER
    thumb_dir = os.path.join(img_dir, "thumb")
    disk_images = os.listdir(img_dir)
    thumb_images = os.listdir(thumb_dir)
    print("DISK", len(disk_images))
    print("THMB", len(thumb_images))
    import pudb
    pudb.set_trace()
    thumb_size = (120, 120)
    for img in disk_images:
        print("Processing", img)
        img_path = os.path.join(images.IMAGE_FOLDER, img)
        if img in thumb_images or not os.path.isfile(img_path):
            print("   ...skipping")
            continue
        print("   ...converting")
        img_path = os.path.join(img_dir, img)
        thumb_path = os.path.join(thumb_dir, img)
        img_obj = Image.open(img_path)
        img_obj.thumbnail(thumb_size)
        img_obj.save(thumb_path)


def debugout(*args):
    with open("/tmp/debugout", "a") as ff:
        ff.write("YO!")
    argtxt = [str(arg) for arg in args]
    msg = "  ".join(argtxt) + "\n"
    with open("/tmp/debugout", "a") as ff:
        ff.write(msg)

def nocache(view):
    @wraps(view)
    def no_cache(*args, **kwargs):
        response = make_response(view(*args, **kwargs))
        response.headers["Last-Modified"] = datetime.now()
        response.headers["Cache-Control"] = "no-store, no-cache, " \
                "must-revalidate, post-check=0, pre-check=0, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "-1"
        return response
        
    return update_wrapper(no_cache, view)

def human_fmt(num):
    """Human friendly file size"""
    units = zip(["bytes", "K", "MB", "GB", "TB", "PB"], [0, 0, 1, 2, 2, 2])
    if num > 1:
        exponent = min(int(log(num, 1024)), len(units) - 1)
        quotient = float(num) / 1024**exponent
        unit, num_decimals = units[exponent]
        format_string = "{:.%sf} {}" % (num_decimals)
        return format_string.format(quotient, unit)
    if num == 0:
        return "0 bytes"
    if num == 1:
        return "1 byte"
