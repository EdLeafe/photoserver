from __future__ import print_function

import copy
import dataclasses
from datetime import datetime
from decimal import Decimal
import random

import exceptions as exc
import utils


class Base:
    table_name = None
    non_db_fields = []

    @classmethod
    def get(cls, pkid_or_obj):
        """Returns an object matching the supplied ID. If the value is an
        instance of the object, verifies that the object's ID is valid.
        """
        if isinstance(pkid_or_obj, cls):
            pkid = pkid_or_obj.pkid
        else:
            pkid = pkid_or_obj
        crs = utils.get_cursor()
        sql = "select * from {} where pkid = %s;".format(cls.table_name)
        crs.execute(sql, (pkid,))
        rec = crs.fetchone()
        if not rec:
            raise exc.NotFound()
        # Allow subclasses to customize the response
        cls._after_get(rec)
        return cls(**rec)

    @classmethod
    def _after_get(cls, rec):
        pass

    @classmethod
    def list(cls, **kwargs):
        """Get all the records for this class.
        
        They can be optionally filtered by the key/value pairs in kwargs
        """
        crs = utils.get_cursor()
        sql = "select * from {}".format(cls.table_name)
        wheres = ["{} = %s".format(fld) for fld in kwargs.keys()]
        vals = kwargs.values()
        where_clause = " and ".join(wheres)
        if where_clause:
            sql = "{} where {}".format(sql, where_clause)
        crs.execute(sql, *vals)
        recs = crs.fetchall()
        # Allow subclasses to customize the results
        cls._after_list(recs)
        return [cls(**rec) for rec in recs]

    @classmethod
    def _after_list(cls, recs):
        pass

    @classmethod
    def delete(cls, pkid):
        crs = utils.get_cursor()
        sql = "delete from {} where pkid = %s".format(cls.table_name)
        crs.execute(sql, (pkid,))
        cls._after_delete(pkid)
        utils.commit()

    @classmethod
    def _after_delete(cls, pkid):
        pass

    def to_dict(self):
        return {fld: getattr(self, fld) for fld in self.field_names}

    def save(self):
        if self.pkid:
            self._update()
        else:
            self._save_new()
        utils.commit()
        self._after_save()

    def _after_save(self):
        pass

    def _update(self):
        # Get the changed fields
        crs = utils.get_cursor()
        sql = "select * from {} where pkid = %s".format(self.table_name)
        crs.execute(sql, (self.pkid,))
        rec = crs.fetchone()
        changes = []
        values = []
        for fld, val in rec.items():
            obj_val = getattr(self, fld)
            if obj_val != val:
                changes.append("{}=%s".format(fld))
                values.append(obj_val)
        if not changes:
            # Just return; nothing to do
            return
        set_clause = ", ".join(changes)
        sql = "update {} set {} where pkid=%s".format(self.table_name, set_clause)
        crs.execute(sql, (*values, self.pkid))

    def _save_new(self):
        crs = utils.get_cursor()
        self.pkid = utils.gen_uuid()
        field_names = ", ".join(self.db_field_names)
        values = tuple(
            [str(getattr(self, field, None)) for field in self.db_field_names]
        )
        value_placeholders = ", ".join(["%s"] * len(self.db_field_names))
        sql = "insert into {} ({}) values ({})".format(
            self.table_name, field_names, value_placeholders
        )
        crs.execute(sql, values)

    @property
    def field_names(self):
        return [field.name for field in dataclasses.fields(self)]

    @property
    def db_field_names(self):
        return [
            field.name
            for field in dataclasses.fields(self)
            if field.name not in self.non_db_fields
        ]


@dataclasses.dataclass
class Album(Base):
    pkid: str = ""
    name: str = ""
    orientation: str = ""
    num_images: int = 0
    updated: datetime = datetime.utcnow()
    parent_id: str = ""

    table_name = "album"
    non_db_fields = ["num_images"]
    DEFAULT_ALBUM_NAME = "calibrate"

    @classmethod
    def _after_get(cls, rec):
        """We need to add the image count to the record."""
        crs = utils.get_cursor()
        sql = """select count(image.pkid) as num_images
                from image join album_image on image.pkid = album_image.image_id
                where album_image.album_id = %s;"""
        crs.execute(sql, (rec["pkid"],))
        rec["num_images"] = crs.fetchone()["num_images"]

    @classmethod
    def _after_list(cls, recs):
        sql = """select album.pkid, count(album_image.image_id) as num_images
                 from album
                    left join album_image
                        on album.pkid = album_image.album_id
                 group by album.pkid ;"""
        crs = utils.get_cursor()
        res = crs.execute(sql)
        image_count_recs = crs.fetchall()
        mapping = {rec["pkid"]: rec["num_images"] for rec in image_count_recs}
        for rec in recs:
            rec["num_images"] = mapping[rec["pkid"]]

    @classmethod
    def _after_delete(cls, pkid):
        # We need to delete the related records in album_image
        crs = utils.get_cursor()
        sql = "delete from album_image where album_image.album_id = %s"
        crs.execute(sql, (pkid))
        # We also need to null out any frames that were using this album
        sql = "update frame set album_id = '' where album_id = %s"
        crs.execute(sql, (pkid,))
        # Finally, we need to delete any sub-albums
        sql = "delete from album where parent_id = %s"
        crs.execute(sql, (pkid,))

    def generate_subalbum_name(self, pkid):
        return "{}-{}".format(self.name, pkid)

    @classmethod
    def get_by_name(cls, name):
        """Return any album whose name matches the supplied value."""
        crs = utils.get_cursor()
        sql = "select * from album where name = %s;"
        crs.execute(sql, (name,))
        recs = crs.fetchall()
        cls._after_list(recs)
        return [cls(**rec) for rec in recs]


    @staticmethod
    def delete_by_name(name):
        """Delete any album whose name matches the supplied value."""
        crs = utils.get_cursor()
        sql = "delete from album where name = %s;"
        crs.execute(sql, (name,))

    def split_for_frameset(self, frames):
        sub_albums = self.create_sub_albums(frames)
        num = len(sub_albums)
        image_count = len(self.images)
        per_album, extra = divmod(image_count, num) if num else (0, 0)
        image_pool = copy.deepcopy(self.images)
        for sub_album in sub_albums:
            sz = per_album + 1 if extra > 0 else per_album
            extra -= 1
            sample = random.sample(image_pool, sz)
            sub_album.add_images(sample)

    def create_sub_albums(self, frames):
        sub_albums = []
        for frame in frames:
            sub_album = Album(
                name=self.generate_subalbum_name(frame.pkid),
                orientation=self.orientation,
                parent_id=self.pkid,
            )
            sub_album.save()
            sub_albums.append(sub_album)
            # Do we need to call frame.set_album() here to set the etcd keys?
            frame.album_id = sub_album.pkid
            frame.save()
        return sub_albums

    def remove_sub_albums(self):
        crs = utils.get_cursor()
        sql = "delete from album where parent_id = %s;"
        crs.execute(sql, (self.pkid,))

    @property
    def images(self):
        crs = utils.get_cursor()
        sql = """select image.* from image join album_image on album_image.image_id = image.pkid
                where album_image.album_id = %s"""
        crs.execute(sql, self.pkid)
        return [Image(**rec) for rec in crs.fetchall()]

    @property
    def image_ids(self):
        crs = utils.get_cursor()
        sql = """select image.pkid from image
                join album_image on album_image.image_id = image.pkid
                where album_image.album_id = %s"""
        crs.execute(sql, self.pkid)
        return [rec["pkid"] for rec in crs.fetchall()]

    @property
    def image_names(self):
        crs = utils.get_cursor()
        sql = """select image.name from image
                join album_image on album_image.image_id = image.pkid
                where album_image.album_id = %s"""
        crs.execute(sql, self.pkid)
        return [rec["name"] for rec in crs.fetchall()]

    def add_images(self, img_list):
        [self.add_image(img) for img in img_list]

    def add_image(self, img):
        img_obj = Image.get(img)
        crs = utils.get_cursor()
        sql = "insert into album_image (album_id, image_id) values (%s, %s);"
        crs.execute(sql, (self.pkid, img_obj.pkid))
        self.num_images += 1

    def remove_images(self, img_list):
        [self.remove_image(img) for img in img_list]

    def remove_image(self, img):
        img_obj = Image.get(img)
        crs = utils.get_cursor()
        sql = "delete from album_image where album_id = %s and image_id = %s;"
        crs.execute(sql, (self.pkid, img_obj.pkid))
        self.num_images -= 1

    def update_frame_album(self, image_ids=None):
        """Updates the 'images' key for all frames that are linked to the album."""
        crs = utils.get_cursor()
        if image_ids is None:
            sql = "select image_id from album_image where album_id = %s;"
            crs.execute(sql, self.pkid)
            image_ids = [rec["image_id"] for rec in crs.fetchall()]
        sql = "select pkid from frame where album_id = %s;"
        crs.execute(sql, (self.pkid,))
        frame_ids = [rec["pkid"] for rec in crs.fetchall()]
        if frame_ids:
            sql = "select name from image where pkid in %s;"
            crs.execute(sql, (image_ids,))
            image_names = [rec["name"] for rec in crs.fetchall()]
            for frame_id in frame_ids:
                utils.write_key(frame_id, "images", image_names)

    @classmethod
    def default_album_id(cls):
        crs = utils.get_cursor()
        sql = "select pkid from album where name = %s"
        crs.execute(sql, (cls.DEFAULT_ALBUM_NAME, ))
        return crs.fetchone().get("pkid")


@dataclasses.dataclass
class Frame(Base):
    pkid: str = ""
    name: str = ""
    frameset_id: str = ""
    frameset_name: str = ""
    album_id: str = ""
    description: str = ""
    orientation: str = ""
    interval_time: int = 0
    interval_units: str = ""
    variance_pct: int = 0
    shutdown: bool = 0
    brightness: Decimal = 0.0
    contrast: Decimal = 0.0
    saturation: Decimal = 0.0
    freespace: int = 0
    ip: str = ""
    updated: datetime = datetime.utcnow()
    log_level: str = ""

    table_name = "frame"
    non_db_fields = ["frameset_name"]

    @classmethod
    def _after_get(cls, rec):
        """We need to add the frameset name, if any, to the record."""
        crs = utils.get_cursor()
        sql = """select frameset.name
                from frameset
                where frameset.pkid = %s;"""
        crs.execute(sql, (rec["pkid"],))
        name_rec = crs.fetchone()
        rec["frameset_name"] = name_rec.get("name") if name_rec else ""
        fs = rec["freespace"]
        rec["freespace"] = utils.human_fmt(fs)

    @classmethod
    def _after_list(cls, recs):
        sql = """select frame.pkid, frameset.name, frameset.album_id
                from frame join frameset on frame.frameset_id = frameset.pkid;"""
        crs = utils.get_cursor()
        crs.execute(sql)
        frameset_name_recs = crs.fetchall()
        name_mapping = {rec["pkid"]: rec["name"] for rec in frameset_name_recs}
        album_mapping = {rec["pkid"]: rec["album_id"] for rec in frameset_name_recs}
        for rec in recs:
            rec["frameset_name"] = name_mapping.get(rec["pkid"], "-none-")
            rec["album_id"] = album_mapping.get(rec["pkid"], rec["album_id"])
            rec["freespace"] = utils.human_fmt(rec["freespace"])

    def _after_save(self):
        """Write the updated values to etcd"""
        def safe_json(att):
            """Convert Decimal to str"""
            val = getattr(self, att)
            if isinstance(val, Decimal):
                return(str(val))
            return val

        settings = (
            "description",
            "interval_time",
            "interval_units",
            "brightness",
            "contrast",
            "saturation",
        )
        settings_dict = {setting: safe_json(setting) for setting in settings}
        utils.write_key(self.pkid, "settings", settings_dict)

    def set_album(self, album_id):
        crs = utils.get_cursor()
        sql = "update frame set album_id = %s where pkid = %s;"
        crs.execute(sql, (album_id, self.pkid))
        utils.commit()
        # Update the etcd keys
        album = Album.get(album_id)
        album.update_frame_album()


@dataclasses.dataclass
class Frameset(Base):
    pkid: str = ""
    name: str = ""
    user_id: str = ""
    album_id: str = ""
    description: str = ""
    orientation: str = "H"
    interval_time: int = 0
    variance_pct: int = 0
    interval_units: str = ""
    num_frames: int = 0
    updated: datetime = datetime.utcnow()

    table_name = "frameset"
    non_db_fields = ["num_frames"]

    @classmethod
    def _after_get(self, rec):
        """Add the frame count."""
        crs = utils.get_cursor()
        sql = "select frame.pkid from frame where frame.frameset_id = %s;"
        rec["num_frames"] = crs.execute(sql, (self.pkid,))

    @classmethod
    def _after_list(self, recs):
        """Add the frame counts."""
        crs = utils.get_cursor()
        sql = "select count(pkid) as num_frames, frameset_id from frame group by frameset_id;"
        crs.execute(sql)
        frame_count_recs = crs.fetchall()
        mapping = {rec["frameset_id"]: rec["num_frames"] for rec in frame_count_recs}
        for rec in recs:
            rec["num_frames"] = mapping.get(rec["pkid"], 0)

    def set_frames(self, frame_ids):
        # Remove any existing relationships
        self.remove_sub_albums()
        for child in self.child_frames:
            self.remove_frame(child)
        for frame_id in frame_ids:
            self.add_frame(frame_id)
        self.assign_sub_albums()

    def remove_frame(self, child):
        child_obj = Frame.get(child)
        child_obj.frameset_id = None
        # We also need to blank their album_id
        child_obj.album_id = None
        child_obj.save()

    def add_frame(self, child):
        child_obj = Frame.get(child)
        if child_obj.frameset_id:
            if child_obj.frameset_id != self.pkid:
                # Frame belongs to a different frameset
                raise exc.DuplicateMembership()
        child_obj.frameset_id = self.pkid
        # We also need to blank their album_id
        child_obj.album_id = None
        child_obj.save()

    def assign_album(self, album):
        self.remove_sub_albums()
        if album is None:
            self.album_id = None
        else:
            album_obj = Album.get(album)
            self.album_id = album_obj.pkid
            # This will add the pkid if this is a new frameset
            self.save()
            self.assign_sub_albums()

    def assign_sub_albums(self):
        if not self.album_id:
            return
        album_obj = Album.get(self.album_id)
        album_obj.split_for_frameset(self.child_frames)

    def remove_sub_albums(self):
        if not self.album_id:
            return
        album_obj = Album.get(self.album_id)
        for frame in self.child_frames:
            subalbum_name = album_obj.generate_subalbum_name(frame.pkid)
            album_obj.delete_by_name(subalbum_name)

    @property
    def child_frames(self):
        crs = utils.get_cursor()
        sql = "select * from frame where frameset_id = %s"
        crs.execute(sql, (self.pkid,))
        return [Frame(**rec) for rec in crs.fetchall()]

    @property
    def child_frame_ids(self):
        crs = utils.get_cursor()
        sql = "select pkid from frame where frameset_id = %s"
        crs.execute(sql, (self.pkid,))
        return [rec["pkid"] for rec in crs.fetchall()]


@dataclasses.dataclass
class Image(Base):
    pkid: str = ""
    keywords: str = ""
    name: str = ""
    width: int = 0
    height: int = 0
    orientation: str = ""
    imgtype: str = "JPEG"
    size: int = 0
    created: datetime = datetime.utcnow()
    updated: datetime = datetime.utcnow()

    table_name = "image"
