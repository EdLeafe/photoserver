from __future__ import absolute_import, print_function, unicode_literals

from dataclasses import dataclass
from datetime import datetime

from flask import Flask, abort, g, make_response, redirect, render_template, request, session, url_for

import albums
import entities
import frames
import utils


def GET_list():
    crs = utils.get_cursor()
    framesets = entities.Frameset.list()
    g.framesets = [fs.to_dict() for fs in framesets]
    albums = entities.Album.list()
    g.albums = [ab.to_dict() for ab in albums if not ab.parent_id]
    g.request_string = str(request.headers)
    return render_template("frameset_list.html")


def set_album(frameset_id, album_id):
    fs = entities.Frameset.get(frameset_id)
    fs.assign_album(album_id)
    return ""


def show(frameset_id):
    if frameset_id is None:
        g.frameset = {"name": "", "pkid": "", "orientation": ""}
    else:
        crs = utils.get_cursor()
        crs.execute("select * from frameset where pkid = %s", (frameset_id,))
        g.frameset = crs.fetchall()[0]
        sql = """select frame.pkid, frame.name, frame.description
                from frame join frameset_frame on frame.pkid = frameset_frame.frame_id
                where frameset_frame.frameset_id = %s;"""
        crs.execute(sql, (frameset_id,))
        g.frames = crs.fetchall()
    return render_template("frameset_detail.html")


def delete(pkid=None):
    if pkid is None:
        # Form
        pkid = request.form["pkid"]
    crs = utils.get_cursor()
    # Get the file name
    sql = "select name from frameset where pkid = %s"
    res = crs.execute(sql, (pkid, ))
    if not res:
        abort(404)
    fname = crs.fetchone()["name"]
    sql = "delete from frameset where pkid = %s"
    crs.execute(sql, (pkid, ))
    sql = "delete from frameset_frame where frameset_id = %s"
    crs.execute(sql, (pkid, ))
    utils.commit()
    return redirect(url_for("list_framesets"))


def update():
    rf = request.form
    if "delete" in rf:
        return delete()
    pkid = rf["pkid"]
    name = rf["name"]
    orientation = rf["orientation"]
    crs = utils.get_cursor()
    print("NAME:", name, "PKID", pkid)
    if not pkid:
        # New frameset
        pkid = utils.gen_uuid()
        sql = """insert into frameset (pkid, name, orientation)
                 values (%s, %s, %s); """
        vals = (pkid, name, orientation)
    else:
        sql = """update frameset set name = %s, orientation = %s
                 where pkid = %s; """
        vals = (name, orientation, pkid)
    crs.execute(sql, vals)
    print("SQL", sql, "VALS", vals)
    utils.commit()
    return redirect(url_for("list_framesets"))


def manage_frames(frameset_id):
    fs = entities.Frameset.get(frameset_id)
    g.frameset = fs.to_dict()
    g.frames = [frm.to_dict() for frm in entities.Frame.list()]
    for frm in g.frames:
        frm["selected"] = 1 if frm["frameset_id"] == frameset_id else 0
    return render_template("frameset_frames.html")


def manage_frames_POST(frameset_id):
    frame_ids = request.form.getlist("selected")
    fs = entities.Frameset.get(frameset_id)
    fs.set_frames(frame_ids)
    return redirect("/framesets")
