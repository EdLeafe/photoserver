from flask import Flask, abort, make_response, redirect, url_for
app = Flask(__name__)
app.secret_key = "exposure"
################
app.debug = True
################
app.config["TEMPLATES_AUTO_RELOAD"] = True

import werkzeug

import albums
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


### Frames ###
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

@app.route("/frames/<frame_id>/album/<album_id>", methods=["PUT"])
def set_frame_album(frame_id, album_id):
    return frames.set_album(frame_id, album_id)

@app.route("/frame/<pkid>/status")
def frame_status(pkid):
    status = frames.status(pkid)
    resp = make_response(status)
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


### Images ###
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

@app.route("/images/thumb", methods=["POST"])
def upload_image_thumb():
    return images.upload_thumb()

@app.route("/download/<img_name>", strict_slashes=False)
def download_file(img_name):
    return images.download(img_name)

@app.route("/images/album", methods=["POST", "GET"])
def image_album():
    return images.set_album()


### Albums ###
@app.route("/albums", strict_slashes=False)
@app.route("/albums/view/<orient>")
def list_albums(orient=None):
    return albums.GET_list(orient)

@app.route("/albums/new", strict_slashes=False)
def create_album():
    return albums.show(None)

@app.route("/albums/<pkid>")
def show_album(pkid):
    return albums.show(pkid)

@app.route("/albums/update", methods=["POST"])
def update_album():
    return albums.update()

@app.route("/albums/<pkid>/images", strict_slashes=False)
def album_images(pkid):
    return albums.manage_images(pkid)

@app.route("/albums/<pkid>/images", strict_slashes=False, methods=["POST"])
def album_images_POST(pkid):
    return albums.manage_images_POST(pkid)

@app.route("/albums/delete/<pkid>", methods=["DELETE", "POST", "GET"])
def delete_album(pkid=None):
    return albums.delete(pkid=pkid)

@app.route("/whaturl/")
def geturl():
    return url_for("index")

if __name__ == "__main__":
    app.run(debug=True)
