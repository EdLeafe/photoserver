from datetime import datetime
import os
import shutil

from flask import Flask, abort, flash, g
from flask import redirect, render_template, request, send_from_directory
from flask import url_for
from PIL import Image
from werkzeug.utils import secure_filename

import utils

IMAGE_FOLDER = "/var/www/photoserver/"
DEFAULT_IMAGES = {"H": "default_h.jpg", "V": "default_v.jpg"}
CREATE_DATE_KEY = 36867


def list_db_images(orient=None, filt=None):
    crs = utils.get_cursor()
    where = ""
    if orient and not orient == "A":
        # 'A' stands for 'ALL'
        where = " where image.orientation = '%s' " % orient
    if filt:
        words = [" keywords REGEXP '\\\\b%s\\\\b' " % word for word in filt.split()]
        filt_clause = " and ".join(words)
        if where:
            where += filt_clause
        else:
            where = " where %s " % filt_clause
    sql = "select * from image %s order by created;" % where
    crs.execute(sql)
    imgs = crs.fetchall()
    for img in imgs:
        img["size"] = utils.human_fmt(img["size"])
    return imgs


def GET_list(orient=None, filt=None):
    g.orient = orient or "A"
    orient_order = "HVSAH"
    orient_pos = orient_order.index(g.orient)
    g.next_orient = orient_order[orient_pos + 1]
    g.images = list_db_images(orient=g.orient, filt=filt)
    g.thumb_path = os.path.join(IMAGE_FOLDER, "thumbs")
    return render_template("image_list.html")


def show(pkid):
    crs = utils.get_cursor()
    sql = "select * from image where pkid = %s"
    res = crs.execute(sql, (pkid, ))
    if not res:
        abort(404)
    g.image = crs.fetchone()
    g.image["size"] = utils.human_fmt(g.image["size"])
    return render_template("image_detail.html")


def update_list():
    rf = request.form
    if rf["filter"]:
        return GET_list(filt=rf["filter"])
    crs = utils.get_cursor()
    sql = "update image set keywords = %s where pkid = %s;"
    keys = rf.keys()
    new_fields = [key for key in keys if key.startswith("key_")]
    for new_field in new_fields:
        pkid = new_field.split("_")[-1]
        orig_field = "orig_%s" % pkid
        new_val = rf.get(new_field)
        orig_val = rf.get(orig_field)
        if new_val == orig_val:
            continue
        crs.execute(sql, (new_val, pkid))
    utils.commit()
    return GET_list()


def update():
    rf = request.form
    if "delete" in rf:
        return delete()
    pkid = rf["pkid"]
    name = rf["name"]
    orig_name = rf["orig_name"]
    keywords = rf["keywords"]
    crs = utils.get_cursor()
    sql = """
            update image set name = %s, keywords = %s
            where pkid = %s; """
    crs.execute(sql, (name, keywords, pkid))
    utils.commit()
    if name != orig_name:
        _rename_image(orig_name, name)
    return redirect(url_for("list_images"))


def _rename_image(orig_name, new_name):
    fpath_orig = os.path.join(IMAGE_FOLDER, orig_name)
    fpath_new = os.path.join(IMAGE_FOLDER, new_name)
    shutil.move(fpath_orig, fpath_new)
    # Move the thumbnail file, too
    tpath_orig = os.path.join(IMAGE_FOLDER, "thumbs", orig_name)
    tpath_new = os.path.join(IMAGE_FOLDER, "thumbs", new_name)
    shutil.move(tpath_orig, tpath_new)


def delete(pkid=None):
    if pkid is None:
        # Form
        pkid = request.form["pkid"]
    crs = utils.get_cursor()
    # Get the file name
    sql = "select name from image where pkid = %s"
    res = crs.execute(sql, (pkid, ))
    if not res:
        abort(404)
    fname = crs.fetchone()["name"]
    sql = "delete from image where pkid = %s"
    crs.execute(sql, (pkid, ))
    sql = "delete from album_image where image_id = %s"
    crs.execute(sql, (pkid, ))
    utils.commit()
    # Now delete the file, if it is present
    fpath = os.path.join(IMAGE_FOLDER, fname)
    try:
        os.unlink(fpath)
    except OSError:
        pass
    return redirect(url_for("list_images"))


def upload_form():
    return render_template("upload.html")


def isduplicate(name):
    """See if another file of the same name exists."""
    crs = utils.get_cursor()
    sql = "select pkid from image where name = %s;"
    res = crs.execute(sql, (name, ))
    return bool(res)


def upload_thumb():
    """ Used when another app has uploaded the main file to the cloud, and is
    sending the thumb for local display.
    """
    image = request.files["thumb_file"]
    fname = request.form["filename"]
    tpath = os.path.join(IMAGE_FOLDER, "thumbs", fname)
    image.save(tpath)
    return "OK"


def upload_file():
    image = request.files["image_file"]
    fname = secure_filename(image.filename)
    # Make sure that there isn't another file by that name
    if isduplicate(fname):
        flash("Image already exists!!", "error")
        return redirect(url_for("upload_image_form"))
    fpath = os.path.join(IMAGE_FOLDER, fname)
    image.save(fpath)
    try:
        img_obj = Image.open(fpath)
    except IOError:
        flash("Not a valid image", "err")
        os.unlink(fpath)
        return redirect(url_for("upload_image_form"))
    imgtype = img_obj.format

    orientation = utils.get_img_orientation(fpath)
    width, height = img_obj.size
    rf = request.form
    keywords = rf["file_keywords"] or fname
    size = os.stat(fpath).st_size
    created = img_obj._getexif().get(CREATE_DATE_KEY)
    updated = datetime.fromtimestamp(os.stat(fpath).st_ctime)

    # Make a thumbnail
    thumb_size = (120, 120)
    img_obj.thumbnail(thumb_size)
    thumb_path_parts = list(os.path.split(fpath))
    thumb_path_parts.insert(-1, "thumbs")
    thumb_path = os.path.join(*thumb_path_parts)
    try:
        img_obj.save(thumb_path, format=imgtype)
    except Exception as e:
        print("EXCEPTION", e)
    
    # Save the info in the database
    pkid = utils.gen_uuid()
    crs = utils.get_cursor()
    sql = """
            insert into image (pkid, keywords, name, orientation, width,
                height, imgtype, size, created, updated)
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s); """
    vals = (pkid, keywords, fname, orientation, width, height, imgtype, size,
            created, updated)
    crs.execute(sql, vals)
    utils.commit()

    return redirect(url_for("list_images"))


def download(img_name):
    if img_name in DEFAULT_IMAGES.values():
        directory = "."
    else:
        directory = IMAGE_FOLDER
    return send_from_directory(directory, img_name)


def set_album():
    album_name = request.form.get("album_name")
    if not album_name:
        abort(400, "No value for 'album_name' received")
    image_name = request.form.get("image_name")
    if not image_name:
        abort(400, "No value for 'image_name' received")
    crs = utils.get_cursor()
    # Get the image
    sql = "select pkid, orientation from image where name = %s"
    crs.execute(sql, (image_name, ))
    image = crs.fetchone()
    if not image:
        abort(404, "Image %s not found" % image_name)
    image_id = image["pkid"]
    orientation = image["orientation"]
    # Get the album (if it exists)
    sql = "select pkid from album where name = %s"
    crs.execute(sql, (album_name, ))
    album = crs.fetchone()
    if album:
        album_id = album["pkid"]
    else:
        # Create it
        album_id = utils.gen_uuid()
        sql = """insert into album (pkid, name, orientation)
                 values (%s, %s, %s); """
        vals = (album_id, album_name, orientation)
        crs.execute(sql, vals)
    # Now add the image to the album
    sql = "insert into album_image (album_id, image_id) values (%s, %s) ;"
    crs.execute(sql, (album_id, image_id))
    utils.commit()
    return "Success!"
