from flask import Flask, abort, redirect, url_for
app = Flask(__name__)
app.secret_key = "exposure"
################
app.debug = True
################
app.config["TEMPLATES_AUTO_RELOAD"] = True

import frames
import framesets
import images
import utils


@app.route('/')
@app.route('/frames/')
def index():
    return frames.GET_list()

@app.route("/register", methods=["POST"])
@utils.nocache
def register():
    return frames.register_frame()

@app.route("/frames/<frame_id>", strict_slashes=False)
def show_frame(frame_id):
    return frames.show_frame(frame_id)

@app.route("/frames/<frame_id>/update", methods=["POST"])
def update_frame(frame_id):
    return frames.update(frame_id)

@app.route("/frames/<frame_id>/images/", methods=["POST"])
def image_assign_POST(frame_id):
    return frames.image_assign_POST(frame_id)

@app.route("/frames/<frame_id>/images/")
def image_assign(frame_id):
    return frames.image_assign(frame_id)

@app.route("/images", strict_slashes=False, methods=["POST"])
def update_image_list():
    return images.update_list()

@app.route("/images", strict_slashes=False)
@app.route("/images/view/<orient>")
def list_images(orient=None):
    return images.GET_list(orient)

@app.route("/images/<pkid>")
def show_image(pkid):
    return images.show(pkid)

@app.route("/images/update", methods=["POST"])
def update_image():
    return images.update()

@app.route("/images/delete/<pkid>", methods=["DELETE", "POST", "GET"])
def delete_image(pkid=None):
    return images.delete(pkid=pkid)

@app.route("/images/upload/")
def upload_image_form():
    return images.upload_form()

@app.route("/images/upload_file", methods=["POST"])
def upload_file():
    return images.upload_file()

@app.route("/download/<img_name>", strict_slashes=False)
def download_file(img_name):
    return images.download(img_name)

@app.route("/frame/<pkid>/status")
def frame_status(pkid):
    return frames.status(pkid)


@app.route("/whaturl/")
def geturl():
    return url_for("index")
