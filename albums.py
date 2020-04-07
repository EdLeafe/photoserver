from __future__ import print_function

import copy
from dataclasses import dataclass
from datetime import datetime
import json
import random
import sys

from flask import Flask, abort, g, redirect, render_template, request, url_for

import entities
from images import DEFAULT_IMAGES
import utils
from utils import debugout


def update_list():
    rf = request.form
    if rf["filter"]:
        return GET_list(filt=rf["filter"])


def GET_list(orient, filt=None):
    if filt:
        albums = entities.Album.list(orientation=filt)
    else:
        albums = entities.Album.list()
    recs = [album.to_dict() for album in albums]
    g.albums = recs
    if "format" in request.args:
        if request.args.get("format").lower() == "json":
            return json.dumps(recs)
    return render_template("album_list.html")


def show(album_id):
    if album_id is None:
        g.album = {"name": "", "pkid": "", "orientation": ""}
    else:
        g.album = entities.Album.get(album_id).to_dict()
    return render_template("album_detail.html")


def delete(pkid=None):
    if pkid is None:
        # Form
        pkid = request.form["pkid"]
    entities.Album.delete(pkid)
    return redirect(url_for("list_albums"))


def update():
    rf = request.form
    if "delete" in rf:
        return delete()
    pkid = rf["pkid"]
    name = rf["name"]
    orientation = rf["orientation"]
    crs = utils.get_cursor()
    if not pkid:
        # New Album
        pkid = utils.gen_uuid()
        sql = """insert into album (pkid, name, orientation)
                 values (%s, %s, %s); """
        vals = (pkid, name, orientation)
    else:
        sql = """update album set name = %s, orientation = %s
                 where pkid = %s; """
        vals = (name, orientation, pkid)
    crs.execute(sql, vals)
    utils.commit()
    return redirect(url_for("list_albums"))


def manage_images(album_id, filter_term=None):
    crs = utils.get_cursor()
    sql = "select * from album where pkid = %s;"
    crs.execute(sql, (album_id, ))
    g.album = crs.fetchall()[0]
    orientation = g.album["orientation"]

    sql = "select * from album_image where album_id = %s;"
    crs.execute(sql, (album_id, ))
    count_nojoin = crs.fetchall()

    sql = """
            select image.*, ifnull(album_image.album_id = %s, 0) as selected
            from image
                left join album_image
                on image.pkid = album_image.image_id
                and album_image.album_id = %s
            where image.orientation = %s
            or image.orientation = "S"
            group by image.pkid
            order by selected desc, image.created
            """
    res = crs.execute(sql, (album_id, album_id, orientation))
    imgs = crs.fetchall()
    for img in imgs:
        img["size"] = utils.human_fmt(img["size"])
    if filter_term:
        imgs = [img for img in imgs
                if img["selected"] or filter_term in img["keywords"]]
    g.images = imgs
    g.image_count = len(imgs)
    return render_template("album_images.html")


def manage_images_POST(album_id):
    filter_term = request.form.get("filter")
    if filter_term:
        return manage_images(album_id, request.form.get("filter"))
    crs = utils.get_cursor()
    sql = "delete from album_image where album_id = %s;"
    crs.execute(sql, (album_id, ))
    image_ids = request.form.getlist("selected")
    sql = "insert into album_image (album_id, image_id) values (%s, %s) ;"
    for image_id in image_ids:
        crs.execute(sql, (album_id, image_id))
    utils.commit()
    # Update the image listings for all frames using that album
    update_frame_album(album_id, image_ids=image_ids)
    return redirect("/albums")


def update_frame_album(album_id, image_ids=None):
    """Updates the 'images' key for all frames that are linked to the album."""
    album = entities.Album.get(album_id)
    album.update_frame_album(image_ids)


def update_frameset_album(album_id, image_ids=None):
    """Updates the 'images' key for all framesets that are linked to the album."""
    crs = utils.get_cursor()
    if image_ids is None:
        sql = "select image_id from album_image where album_id = %s;"
        crs.execute(sql, album_id)
        image_ids = [rec["image_id"] for rec in crs.fetchall()]
    sql = "select pkid from frameset where album_id = %s;"
    crs.execute(sql, (album_id,))
    frameset_ids = [rec["pkid"] for rec in crs.fetchall()]
    if frameset_ids:
        sql = "select name from image where pkid in %s;"
        crs.execute(sql, (image_ids,))
        image_names = [rec["name"] for rec in crs.fetchall()]
        for frameset_id in frameset_ids:
            utils.write_key(frameset_id, "images", image_names)
