import sqlite3

from flask import Flask, make_response, render_template, url_for
import werkzeug

import albums
import butterflies
import frames
import framesets
import images
import secrets
import security
import test
import utils

from dBug import loggit, logPoint

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

################
app.debug = False
################
app.config["TEMPLATES_AUTO_RELOAD"] = True
# To make uwsgi happy
application = app

# for shorter decorators
login_required = security.login_required


@app.route("/")
@app.route("/frames/")
@login_required
def index():
    ret = frames.GET_list()
    return ret


@app.route("/register", methods=["POST"])
@utils.nocache
def register():
    return frames.register_frame()


### Frames ###
@app.route("/frames/<frame_id>", strict_slashes=False)
@login_required
def show_frame(frame_id):
    return frames.show_frame(frame_id)


@app.route("/frames/<frame_id>/navigate", methods=["PUT"])
@login_required
def navigate_frame(frame_id):
    return frames.navigate(frame_id)


@app.route("/frames/<frame_id>/update", methods=["POST"])
@login_required
def update_frame(frame_id):
    return frames.update(frame_id)


@app.route("/frames/<frame_id>/reboot", methods=["POST"])
@login_required
def reboot_frame(frame_id):
    return frames.reboot(frame_id)


@app.route("/frames/<frame_id>/screen", methods=["POST"])
@login_required
def restart_screen(frame_id):
    return frames.restart_screen(frame_id)


@app.route("/frames/<frame_id>/current", methods=["GET"])
@login_required
def get_current_frame_image(frame_id):
    return frames.get_current_frame_image(frame_id)


@app.route("/frames/<frame_id>/album/", methods=["PUT"])
@app.route("/frames/<frame_id>/album/<album_id>", methods=["PUT"])
@login_required
def set_frame_album(frame_id, album_id=None):
    return frames.set_album(frame_id, album_id)


@app.route("/frames/<pkid>/status")
def frame_status(pkid):
    status = frames.status(pkid)
    resp = make_response(status)
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


### Framesests ###
@app.route("/framesets", strict_slashes=False)
@login_required
def list_framesets(orient=None):
    return framesets.GET_list()


@app.route("/framesets/<frameset_id>", strict_slashes=False)
@login_required
def show_frameset(frameset_id):
    return framesets.show(frameset_id)


@app.route("/framesets/new", strict_slashes=False)
@login_required
def create_frameset():
    return framesets.show(None)


@app.route("/framesets/update", methods=["POST"])
@login_required
def update_frameset():
    return framesets.update()


@app.route("/framesets/<frameset_id>/album/", methods=["PUT"])
@app.route("/framesets/<frameset_id>/album/<album_id>", methods=["PUT"])
@login_required
def set_frameset_album(frameset_id, album_id=None):
    return framesets.set_album(frameset_id, album_id)


@app.route("/framesets/<pkid>/frames", strict_slashes=False)
@login_required
def frameset_frames(pkid):
    return framesets.manage_frames(pkid)


@app.route("/framesets/<pkid>/frames", strict_slashes=False, methods=["POST"])
@login_required
def frameset_frames_POST(pkid):
    return framesets.manage_frames_POST(pkid)


### Images ###
@app.route("/images", strict_slashes=False, methods=["POST"])
@login_required
def update_image_list():
    return images.update_list()


@app.route("/images", strict_slashes=False)
@app.route("/images/view/<orient>", methods=["GET", "POST"])
@login_required
def list_images(orient=None):
    return images.GET_list(orient)


@app.route("/images/<pkid>")
@login_required
def show_image(pkid):
    return images.show(pkid)


@app.route("/images/update", methods=["POST"])
@login_required
def update_image():
    return images.update()


@app.route("/images/delete/<pkid>", methods=["DELETE", "POST", "GET"])
@login_required
def delete_image(pkid=None):
    return images.delete(pkid=pkid)


@app.route("/images/upload/")
@login_required
def upload_image_form():
    return images.upload_form()


@app.route("/images/upload_file", methods=["POST"])
@login_required
def upload_file():
    return images.upload_file()


@app.route("/images/thumb", methods=["POST"])
def upload_image_thumb():
    return images.upload_thumb()


@app.route("/download/<img_name>", strict_slashes=False)
def download_file(img_name):
    return images.download(img_name)


@app.route("/images/album", methods=["POST", "GET"])
@login_required
def image_album():
    return images.set_album()


### Albums ###
@app.route("/albums", strict_slashes=False)
@app.route("/albums/view/<orient>")
@login_required
def list_albums(orient=None):
    return albums.GET_list(orient)


@app.route("/albums/new", strict_slashes=False)
@login_required
def create_album():
    return albums.show(None)


@app.route("/albums/new_smart", strict_slashes=False)
@login_required
def create_smart_album():
    return albums.show_smart(None)


@app.route("/albums/<pkid>")
@login_required
def show_album(pkid):
    return albums.show(pkid)


@app.route("/albums/update", methods=["POST"])
@login_required
def update_album():
    return albums.update()


@app.route("/albums/update_rules", methods=["POST"])
@login_required
def update_rules():
    return albums.update_smart()


@app.route("/albums/smart_calculate", methods=["POST"])
@login_required
def smart_calculate():
    return albums.smart_calculate()


@app.route("/albums/<pkid>/images", strict_slashes=False)
@login_required
def album_images(pkid):
    return albums.manage_images(pkid)


@app.route("/albums/<pkid>/images", strict_slashes=False, methods=["POST"])
@login_required
def album_images_POST(pkid):
    return albums.manage_images_POST(pkid)


@app.route("/albums/delete/<pkid>", methods=["DELETE", "POST", "GET"])
@login_required
def delete_album(pkid=None):
    return albums.delete(pkid=pkid)


### 2020 Butterflies ###
@app.route("/butterflies", methods=["GET"])
def show_butterflies():
    return butterflies.show()


@app.route("/butterflies/random", methods=["GET"])
def random_butterfly():
    selection = butterflies.random_butterfly()
    resp = make_response(selection)
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp


@app.route("/whaturl/")
@login_required
def geturl():
    return url_for("index")


@app.route("/login_form")
def login_form():
    return render_template("login_form.html")


@app.route("/login", methods=["POST"])
def login():
    return security.POST_login()


@app.route("/user_registration")
@login_required
def register_user():
    return security.register_user_form()


@app.route("/create_user", methods=["POST"])
@login_required
def create_user():
    return security.create_user()


@app.route("/logout")
def logout():
    return security.logout()


## Test ##
@app.route("/test")
def GET_test():
    return test.test()


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
