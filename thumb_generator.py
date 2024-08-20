import os
from PIL import Image


IMAGE_FOLDER = "/var/www/photoserver/"

for fname in os.listdir(IMAGE_FOLDER):
    fpath = os.path.join(IMAGE_FOLDER, fname)
    tpath = os.path.join(IMAGE_FOLDER, "thumb", fname)
    if os.path.exists(tpath):
        print(fname, "exists")
        continue
    try:
        img_obj = Image.open(fpath)
    except IOError:
        print(fname, "is not a valid image")
        continue
    imgtype = img_obj.format

    # Make a thumbnail
    thumb_size = (120, 120)
    img_obj.thumbnail(thumb_size)
    img_obj.save(tpath, format=imgtype)
    print("Thumbnail for %s was created" % fname)
