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
    g.frames = sorted([frm.to_dict() for frm in frames], key=lambda x: x["name"].upper())
    albums = entities.Album.list()
    g.albums = sorted(
        [ab.to_dict() for ab in albums if not ab.parent_id],
        key=lambda x: x["name"].upper(),
    )
    g.request_string = str(request.headers)
    return render_template("frame_list.html")


def set_album(frame_id, album_id):
    frame = entities.Frame.get(frame_id)
    frame.set_album(album_id)
    return ""


def register_frame():
    rf = request.form
    utils.debugout("FORM", rf)
    pkid = rf["pkid"]
    try:
        frame = entities.Frame.get(pkid)
    except exc.NotFound:
        # New frame
        frame = entities.Frame(pkid=pkid)
    frame.ip = request.remote_addr
    frame.freespace = rf["freespace"]
    frame.save(new=True)
    agent = request.headers.get("User-agent")
    debugout("Album:", frame.album_id)
    if agent == "photoviewer":
        # from the frame app; return the pkid and images
        if frame.album_id:
            album = entities.Album.get(frame.album_id)
            image_names = album.image_names
        else:
            image_names = []
        return json.dumps([frame.pkid, image_names])
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
    LOG.debug("navigate() called for pkid = '{}' and direction = {}".format(pkid, direction))
    utils.write_key(pkid, "change_photo", direction)
    return ""


def update(pkid=None):
    rf = request.form
    rfc = dict(rf)
    if "delete" in rfc:
        pkid = rfc["pkid"]
        entities.Frame.delete(pkid)
        return redirect(url_for("index"))
    # Get rid of the 'submit' field
    rfc.pop("submit", None)
    pkid = rfc["pkid"] = rfc["pkid"] or pkid
    frame_dict = entities.Frame.get(pkid).to_dict()
    frame_dict.update(rfc)
    frame = entities.Frame(**frame_dict)
    utils.debugout("FRAMEDICT", frame_dict)
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
    crs.execute(sql, (pkid,))
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
    crs.execute(sql, (pkid,))
    image_ids = [rec["name"] for rec in crs.fetchall()]
    return json.dumps(
        {
            "name": name,
            "description": description,
            "interval_time": interval_time,
            "interval_units": interval_units,
            "brightness": brightness,
            "contrast": contrast,
            "saturation": saturation,
            "images": image_ids,
        },
        cls=DecimalEncoder,
    )
