import os
import pyrax

PHOTO_SRC_DIR = "/var/www/photoserver"

ctx = pyrax.create_context()
ctx.set_credential_file("/home/ed/.rackspace_cloud_credentials")
ctx.authenticate()
clt = ctx.get_client("swift", "DFW")
cont = clt.get("photoviewer")

clt.sync_folder_to_container(PHOTO_SRC_DIR, cont)
