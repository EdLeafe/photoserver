from __future__ import absolute_import, print_function, unicode_literals

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
import json
import sys

from flask import Flask, abort, g, make_response, redirect, render_template
from flask import request, session, url_for

import albums
import entities
import exceptions as exc
from images import DEFAULT_IMAGES
import utils
from utils import debugout

LOG = utils.LOG
    

def GET_list():
    frames = entities.Frame.list()
    g.frames = [frm.to_dict() for frm in frames]
    albums = entities.Album.list()
    g.albums = [ab.to_dict() for ab in albums if not ab.parent_id]
    g.request_string = str(request.headers)
    return render_template("frame_list.html")


def set_album(frame_id, album_id):
    frame = entities.Frame.get(frame_id)
    frame.set_album(album_id)
    return ""


def register_frame():
    rf = request.form
    frame = entities.Frame(**rf)
    frame.ip = request.remote_addr
    debugout("REG", rf, frame.ip)
    # Cast orientation to H, V, or S
    orientation = rf["orientation"][0].upper()
    if orientation not in ("HVS"):
        abort(400, "Invalid orientation '%s' submitted" % rf["orientation"])
    # If no album is specified, set the default album
    if not frame.album_id:
        frame.album_id = entities.Album.default_album_id()
    debugout("FALB", frame.album_id)
    agent = request.headers.get("User-agent")
    if agent == "photoviewer":
        # from the frame app; return the pkid and images
        album = entities.Album.get(frame.album_id)
        debugout("ALBUM", album)
        debugout("IMG", album.image_names)
        return json.dumps([pkid, album.image_names])
    # From a web interface
    return render_template("registration.html")


def show_frame(frame_id):
    g.frame = entities.Frame.get(frame_id).to_dict()
    return render_template("frame_detail.html")


def delete(pkid):
    crs = utils.get_cursor()
    crs.execute("delete from frame where pkid = %s", (pkid,))
    utils.commit()
    return GET_list()


def navigate(pkid):
    qs = request.query_string.decode("utf-8")
    direction = qs.split("=")[-1]
    LOG.debug("navigate() called for pkid = '{}' and direction = {}".format(
            pkid, direction))
    utils.write_key(pkid, "change_photo", direction)
    return ""


def update(pkid=None):
    rf = request.form
    frame = entities.Frame.get(pkid=pkid, **rf)
    frame.save()
    return redirect(url_for("index"))


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super(DecimalEncoder, self).default(o)


def status(pkid):
    crs = utils.get_cursor()
    sql = """
            select name, description, interval_time, interval_units, album_id,
              brightness, contrast, saturation
            from frame where pkid = %s;
            """
    crs.execute(sql, (pkid, ))
    recs = crs.fetchall()
    if not recs:
        return ""
    rec = recs[0]
    name = rec["name"]
    description = rec["description"]
    interval_time = rec["interval_time"]
    interval_units = rec["interval_units"]
    album_id = rec["album_id"]
    brightness = rec["brightness"]
    contrast = rec["contrast"]
    saturation = rec["saturation"]
    # Get associated images
    sql = """
            select image.name from image 
            join album_image on image.pkid = album_image.image_id
            join album on album_image.album_id = album.pkid
            join frame on frame.album_id = album.pkid
            where frame.pkid = %s ;
            """
    crs.execute(sql, (pkid, ))
    image_ids = [rec["name"] for rec in crs.fetchall()]
    return json.dumps({"name": name, "description": description,
            "interval_time": interval_time, "interval_units": interval_units,
            "brightness": brightness, "contrast": contrast,
            "saturation": saturation, "images": image_ids},
            cls=DecimalEncoder)
