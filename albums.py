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
    recs = sorted([album.to_dict() for album in albums], key=lambda x: x["name"])
    entities.Album.add_image_counts(recs)
    g.albums = recs
    if "format" in request.args:
        if request.args.get("format").lower() == "json":
            return json.dumps(recs)
    return render_template("album_list.html")


def show(album_id):
    if album_id is None:
        g.album = {"name": "", "pkid": "", "orientation": ""}
    else:
        album = entities.Album.get(album_id)
        if album.smart:
            return show_smart(album_id)
        g.album = album.to_dict()
    return render_template("album_detail.html")


def show_smart(album_id):
    g.kw_data = utils.all_keywords()
    albums = entities.Album.list()
    name_pks = sorted([(album.name, album.pkid) for album in albums])
    g.album_names = [item[0] for item in name_pks]
    g.album_ids = [item[1] for item in name_pks]
    if album_id is None:
        g.album = {"name": "", "pkid": "", "orientation": "", "rules": ""}
        g.rules = []
    else:
        album = entities.Album.get(album_id)
        g.album = album.to_dict()
        g.rules = album.rules
    return render_template("album_smart_rules.html")


def delete(pkid=None):
    if pkid is None:
        # Form
        pkid = request.form["pkid"]
    entities.Album.delete(pkid)
    return redirect(url_for("list_albums"))


def update():
    rf = request.form
    rfc = dict(rf)
    if "delete" in rfc:
        pkid = rfc["pkid"]
        entities.Album.delete(pkid)
        return redirect(url_for("list_albums"))
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


def _parse_smart_form(rf):
    kk = list(rf.keys())
    fields = [k for k in kk if k.startswith("field")]
    comps = [k for k in kk if k.startswith("comp")]
    name = rf.get("name")
    out = []
    for field in fields:
        fld_name = rf.get(field)
        # The name is 'fieldN', where N is the sequence
        seq = field.split("field")[-1]
        comp = rf.get(f"comp{seq}")
        val = rf.get(f"value{seq}")
        out.append({fld_name: {comp: val}})
    return out


def smart_calculate():
    parsed = _parse_smart_form(request.form)
    recs = entities.Album.records_for_rules(parsed)
    return json.dumps({rec["pkid"]: rec["name"] for rec in recs})


def update_smart():
    parsed = _parse_smart_form(request.form)
    rf = request.form
    rfc = dict(rf)
    if "delete" in rfc:
        pkid = rfc["pkid"]
        entities.Album.delete(pkid)
        return redirect(url_for("list_albums"))
    rules = json.dumps(parsed)
    name = rf.get("name")
    pkid = rf.get("pkid")
    if not pkid:
        # New Album
        pkid = utils.gen_uuid()
        sql = """insert into album (pkid, name, smart, rules)
                 values (%s, %s, %s, %s); """
        vals = (pkid, name, True, rules)
    else:
        sql = """update album set name = %s, rules = %s
                 where pkid = %s; """
        vals = (name, rules, pkid)
    with utils.DbCursor() as crs:
        crs.execute(sql, vals)
    album_obj = entities.Album.get(pkid)
    album_obj.update_images(None)
    return redirect(url_for("list_albums"))


def manage_images(album_id, filter_term=None):
    album_obj = entities.Album.get(album_id)
    if album_obj.smart:
        return view_smart_images(album_obj)
    g.album = album_obj.to_dict()
    orientation = g.album["orientation"]
    all_images = entities.Image.list()
    imgs = [img.to_dict() for img in all_images if img.orientation in ("S", orientation)]
    for img in imgs:
        img["size"] = utils.human_fmt(img["size"])
        img["selected"] = img["pkid"] in album_obj.image_ids
    if filter_term:
        imgs = [img for img in imgs if img["selected"] or filter_term in img["keywords"]]
    crea = [(im["name"], im["created"], type(im["created"])) for im in imgs]
    imgs.sort(key=lambda x: (not x["selected"], x["created"]), reverse=False)
    g.images = imgs
    g.image_count = len(imgs)
    return render_template("album_images.html")


def view_smart_images(album_obj):
    g.album = album_obj.to_dict()
    g.images = entities.Album.smart_album_images(album_obj.pkid)
    g.image_count = len(g.images)
    return render_template("album_images.html")


def manage_images_POST(album_id):
    filter_term = request.form.get("filter")
    if filter_term:
        return manage_images(album_id, request.form.get("filter"))
    album_obj = entities.Album.get(album_id)
    imgs = request.form.getlist("selected")
    album_obj.update_images(imgs)
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
