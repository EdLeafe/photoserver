import datetime as dt
from functools import wraps
import hashlib
import os

from flask import abort, flash, g, redirect, render_template, request
from flask import Response, session
import utils

TOKEN_DURATION = dt.timedelta(hours=48)
LOG = utils.LOG

def _hash_pw(val):
    try:
        val = val.encode("utf-8")
    except AttributeError:
        # Already encoded
        pass
    return hashlib.md5(val).hexdigest()


def _get_user_token(user_id):
    token = hashlib.md5(os.urandom(8)).hexdigest()
    expires = dt.datetime.utcnow() + TOKEN_DURATION
    crs = utils.get_cursor()
    crs.execute("""
            INSERT INTO login (token, user_id, expires)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE token=%s, expires=%s""",
            (token, user_id, expires, token, expires))
    utils.commit()
    return token


def login_required(fnc):
    @wraps(fnc)
    def wrapped(*args, **kwargs):
        ok = False
        token = session.get("token")
        LOG.debug("TOKEN: %s" % token)
        if token:
            crs = utils.get_cursor()
            crs.execute("SELECT expires FROM login WHERE token = %s;",
                    token)
            rec = crs.fetchone()
            if rec:
                LOG.debug("EXPIRES: %s" % rec["expires"])
                LOG.debug("NOW: %s" % dt.datetime.utcnow())
                ok = rec["expires"] > dt.datetime.utcnow()
                LOG.debug("OK: %s" % ok)
        if not ok:
            session["original_url"] = request.url
            return redirect("/login_form")
        LOG.debug("Credentials OK")
        return fnc(*args, **kwargs)
    return wrapped


def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
	    "Could not verify your access level for that URL.\n"
	    "You have to login with proper credentials", 401,
	    {"WWW-Authenticate": "Basic realm='Login Required'"})


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth():
            session["original_url"] = request.url
            return authenticate()
        return f(*args, **kwargs)
    return decorated


def POST_login():
    form = request.form
    username = form.get("username")
    pw = form.get("pw")
    hashed = _hash_pw(pw)
    crs = utils.get_cursor()
    crs.execute("""
            SELECT pkid, superuser FROM user
            WHERE name = %s and pw = %s""",
            (username, hashed))
    rec = crs.fetchone()
    if not rec:
        flash("Login failed.")
        return redirect("/login_form")
    user_id = rec["pkid"]
    superuser = rec["superuser"]
    token = _get_user_token(user_id)
    flash("Login successful.")
    target = session.get("original_url") or "/"
    session["token"] = token
    session["superuser"] = superuser
    return redirect(target)


def logout():
    token = session.get("token")
    if token:
        crs = utils.get_cursor()
        crs.execute("DELETE FROM login WHERE token = %s;", token)
        utils.commit()
    del session["token"]
    del session["superuser"]
    flash("You have been logged out.")
    return redirect("/")


def register_user_form():
    return render_template("user_reg_form.html")


def create_user():
    form = request.form
    username = form.get("username")
    pw = form.get("pw")
    if not all((username, pw)):
        flash("You must supply a username and password")
        return render_template("user_reg_form")
    hpw = _hash_pw(pw)
    superuser = form.get("user_type") == "super"
    pkid = utils.gen_uuid()
    crs = utils.get_cursor()
    try:
        crs.execute("""
            INSERT INTO user (pkid, name, pw, superuser)
            VALUES (%s, %s, %s, %s)""", (pkid, username, hpw, superuser))
        utils.commit()
    except utils.IntegrityError as ee:
        flash("Oops! %s" % str(ee.args[1]), "error")
        return render_template("user_reg_form.html")
    flash("Successfully registered user '%s'" % username)
    return redirect("/")
