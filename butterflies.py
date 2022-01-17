import json
import random

from flask import abort, Flask, g, render_template, request, session, url_for

import utils


def show_butterflies():
    return json.dumps("there were 100 of 'em")


def random_butterfly():
    crs = utils.get_cursor()
    sql = "select name from image where keywords like '%2020%' order by rand() limit 1;"
    crs.execute(sql)
    fname = crs.fetchone()["name"]
    return json.dumps(fname)
