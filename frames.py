from __future__ import print_function

from datetime import datetime
import json
import sys

from flask import Flask, abort, g, redirect, render_template, request, url_for

from images import DEFAULT_IMAGES
import utils
from utils import debugout


def GET_list():
    crs = utils.get_cursor()
    res = crs.execute("""select frame.*, album.name as album_name
                         from frame left join album
                         on frame.album_id = album.pkid;""")
    recs = crs.fetchall()
    for rec in recs:
        fs = rec["freespace"]
        rec["freespace"] = utils.human_fmt(fs)
    g.frames = recs
    res = crs.execute("select * from album;")
    g.albums = crs.fetchall()
    return render_template("frame_list.html")


def set_album(frame_id, album_id):
    crs = utils.get_cursor()
    sql = "update frame set album_id = %s where pkid = %s;"
    crs.execute(sql, (album_id, frame_id))
    utils.commit()
    return ""


def register_frame():
    pkid = None
    crs = utils.get_cursor()
    now = datetime.now()
    ip = request.remote_addr
    rf = request.form
    name = rf["name"]
    pkid = rf["pkid"]
    desc = rf["description"]
    # Cast to H, V, or S
    orientation = rf["orientation"][0].upper()
    if not orientation in ("HVS"):
        abort(400, "Invalid orientation '%s' submitted" % rf["orientation"])
    interval_time = rf["interval_time"]
    interval_units = rf["interval_units"]
    freespace = rf["freespace"]

    if not pkid:
        # Try finding it by name
        sql = """
                select pkid from frame
                where name = %s; """
        res = crs.execute(sql, (name, ))
        if res:
            pkid = crs.fetchall()[0]["pkid"]
    if pkid:
        sql = """
                update frame set name = %s, description = %s, orientation = %s,
                interval_time = %s, interval_units = %s, freespace = %s,
                ip = %s, updated = %s
                where pkid = %s; """
        vals = (name, desc, orientation, interval_time, interval_units,
                freespace, ip, now, pkid)
        res = crs.execute(sql, vals)
        if not res:
            # The pkid doesn't exist
            pkid = ""
    if not pkid:
        # New record
        pkid = utils.gen_uuid()
        sql = """
                insert into frame (pkid, name, description, orientation,
                        interval_time, interval_units, freespace, ip, updated)
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s); """
        vals = (pkid, name, desc, orientation, interval_time, interval_units,
                freespace, ip, now)
        res = crs.execute(sql, vals)
    utils.commit()

    # Get the associated images
    sql = """
            select image.name from image 
            join album_image on image.pkid = album_image.image_id
            join album on album_image.album_id = album.pkid
            join frame on frame.album_id = album.pkid
            where frame.pkid = %s ;
            """
    crs.execute(sql, (pkid,))
    image_names = [img["name"] for img in crs.fetchall()]
    if not image_names:
        # New frame, so add the default image
        def_img = (DEFAULT_IMAGES["H"] if orientation == "H"
                else DEFAULT_IMAGES["V"])
        image_names.append(def_img)
    agent = request.headers.get("User-agent")
    if agent == "photoviewer":
        # from the frame app; return the pkid
        return json.dumps([pkid, image_names])
    # From a web interface
    return render_template("registration.html")


def show_frame(frame_id):
    crs = utils.get_cursor()
    crs.execute("select * from frame where pkid = %s", (frame_id,))
    g.frame = crs.fetchall()[0]
    g.frame["freespace"] = utils.human_fmt(g.frame["freespace"])
    return render_template("frame_detail.html")


def update(pkid=None):
    rf = request.form
    pkid = pkid or rf["pkid"]
    description = rf["description"]
    interval_time = rf["interval_time"]
    interval_units = rf["interval_units"]
    sql = """
            update frame set description = %s, interval_time = %s,
                interval_units = %s
            where pkid = %s; """
    vals = (description, interval_time, interval_units, pkid)
    crs = utils.get_cursor()
    crs.execute(sql, vals)
    utils.commit()
    return redirect(url_for("index"))


def image_assign_POST(frame_id):
    crs = utils.get_cursor()
    sql = "delete from frame_image where frame_id = %s;"
    crs.execute(sql, (frame_id))
    image_ids = request.form.getlist("selected")
    sql = "insert into frame_image (frame_id, image_id) values (%s, %s) ;"
    for image_id in image_ids:
        crs.execute(sql, (frame_id, image_id))
    utils.commit()
    return image_assign(frame_id)


def image_assign(frame_id):
    crs = utils.get_cursor()
    sql = "select * from frame where pkid = %s;"
    crs.execute(sql, (frame_id, ))
    g.frame = crs.fetchall()[0]
    g.frame["freespace"] = utils.human_fmt(g.frame["freespace"])
    orientation = g.frame["orientation"]


    sql = "select * from frame_image where frame_id = %s;"
    crs.execute(sql, (frame_id, ))
    count_nojoin = crs.fetchall()

    sql = """
            select image.*, ifnull(frame_image.frame_id = %s, 0) as selected
            from image
                left join frame_image
                on image.pkid = frame_image.image_id
                and frame_image.frame_id = %s
            where image.orientation = %s
            group by image.pkid
            order by selected desc, image.name
            """
    res = crs.execute(sql, (frame_id, frame_id, orientation))
    imgs = crs.fetchall()
    for img in imgs:
        img["size"] = utils.human_fmt(img["size"])
    g.images = imgs
    return render_template("image_assign.html")


def status(pkid):
    crs = utils.get_cursor()
    sql = """
            select name, description, interval_time, interval_units, album_id
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
            "images": image_ids})
