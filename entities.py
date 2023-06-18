from __future__ import print_function

import copy
import dataclasses
from datetime import datetime
from decimal import Decimal
import json
import random

from dateutil import parser as date_parser

import exceptions as exc
import utils


class Base:
    table_name = None
    non_db_fields = []
    custom_list = False

    @classmethod
    def get(cls, pkid_or_obj):
        """Returns an object matching the supplied ID. If the value is an
        instance of the object, verifies that the object's ID is valid.
        """
        if isinstance(pkid_or_obj, cls):
            pkid = pkid_or_obj.pkid
        else:
            pkid = pkid_or_obj
        sql = "select * from {} where pkid = %s;".format(cls.table_name)
        with utils.DbCursor() as crs:
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
        sql = "select * from {}".format(cls.table_name)
        if cls.custom_list:
            where_clause = cls._custom_where(**kwargs)
            vals = tuple()
        else:
            wheres = ["{} = %s".format(fld) for fld in kwargs.keys()]
            vals = kwargs.values()
            where_clause = " and ".join(wheres)
        if where_clause:
            sql = "{} where {}".format(sql, where_clause)
        print("SQL", sql)
        with utils.DbCursor() as crs:
            crs.execute(sql, *vals)
        recs = crs.fetchall()
        # Allow subclasses to customize the results
        cls._after_list(recs)
        return cls.from_recs(recs)

    @classmethod
    def _custom_where(cls, **kwargs):
        pass

    @classmethod
    def _after_list(cls, recs):
        pass

    @classmethod
    def delete(cls, pkid):
        sql = "delete from {} where pkid = %s".format(cls.table_name)
        with utils.DbCursor() as crs:
            crs.execute(sql, (pkid,))
        cls._after_delete(pkid)

    @classmethod
    def _after_delete(cls, pkid):
        pass

    def to_dict(self):
        return {fld: getattr(self, fld) for fld in self.field_names}

    @classmethod
    def from_rec(cls, rec):
        return cls(**rec)

    @classmethod
    def from_recs(cls, recs):
        return [cls(**rec) for rec in recs]

    def save(self, new=False):
        if self.pkid and not new:
            self._update()
        else:
            try:
                self._save_new()
            except utils.IntegrityError:
                # The record already exists
                self._update()
        self._after_save()

    def _after_save(self):
        pass

    def _update(self):
        # Get the changed fields
        sql = "select * from {} where pkid = %s".format(self.table_name)
        with utils.DbCursor() as crs:
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
        # New frames may specify their pkid, so if it's there, use that
        self.pkid = self.pkid or utils.gen_uuid()
        field_names = ", ".join(self.db_field_names)
        values = tuple([str(getattr(self, field, None)) for field in self.db_field_names])
        value_placeholders = ", ".join(["%s"] * len(self.db_field_names))
        sql = "insert into {} ({}) values ({})".format(
            self.table_name, field_names, value_placeholders
        )
        with utils.DbCursor() as crs:
            crs.execute(sql, values)

    @property
    def field_names(self):
        return [field.name for field in dataclasses.fields(self)]

    @property
    def db_field_names(self):
        return [
            field.name for field in dataclasses.fields(self) if field.name not in self.non_db_fields
        ]


# TODO: When modifying an album, need to update any sub-albums


@dataclasses.dataclass
class Album(Base):
    pkid: str = ""
    name: str = ""
    orientation: str = ""
    updated: datetime = datetime.utcnow()
    parent_id: str = ""
    smart: bool = False
    rules: str = ""

    table_name = "album"
    DEFAULT_ALBUM_NAME = "calibrate"

    @classmethod
    def _after_delete(cls, pkid):
        # We need to delete the related records in album_image
        with utils.DbCursor() as crs:
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
        sql = "select * from album where name = %s;"
        with utils.DbCursor() as crs:
            crs.execute(sql, (name,))
        recs = crs.fetchall()
        cls._after_list(recs)
        return cls.from_recs(recs)

    @staticmethod
    def delete_by_name(name):
        """Delete any album whose name matches the supplied value."""
        sql = "delete from album where name = %s;"
        with utils.DbCursor() as crs:
            crs.execute(sql, (name,))

    def split_for_frameset(self, frames):
        sub_albums = self.create_sub_albums(frames)
        num = len(sub_albums)
        image_count = len(self.images)
        per_album, extra = divmod(image_count, num) if num else (0, 0)
        image_pool = copy.deepcopy(self.images)
        for sub_album in [sa[1] for sa in sub_albums]:
            sz = per_album + 1 if extra > 0 else per_album
            extra -= 1
            sample = random.sample(image_pool, sz)
            sub_album.add_images(sample)
            sub_album.save()
            [image_pool.remove(s) for s in sample]
        # Set the album for each of the frames
        for frame, album in sub_albums:
            frame.set_album(album.pkid)

    def create_sub_albums(self, frames):
        sub_albums = []
        for frame in frames:
            sub_album = Album(
                name=self.generate_subalbum_name(frame.pkid),
                orientation=self.orientation,
                parent_id=self.pkid,
            )
            sub_album.save()
            sub_albums.append((frame, sub_album))
        return sub_albums

    def remove_sub_albums(self):
        sql = "delete from album where parent_id = %s;"
        with utils.DbCursor() as crs:
            crs.execute(sql, (self.pkid,))

    @property
    def sub_albums(self):
        sql = "select * from album where parent_id = %s;"
        with utils.DbCursor() as crs:
            crs.execute(sql, (self.pkid))
        return self.from_recs(crs.fetchall())

    @property
    def images(self):
        if self.smart:
            return self.smart_album_images(self.pkid)
        sql = (
            "select image.* from image join album_image "
            "on album_image.image_id = image.pkid "
            "where album_image.album_id = %s"
        )
        with utils.DbCursor() as crs:
            crs.execute(sql, self.pkid)
        return Image.from_recs(crs.fetchall())

    @property
    def image_ids(self):
        if self.smart:
            recs = self.smart_album_images(self.pkid, return_objects=False)
        else:
            sql = """select image.pkid from image
                    join album_image on album_image.image_id = image.pkid
                    where album_image.album_id = %s"""
            with utils.DbCursor() as crs:
                crs.execute(sql, self.pkid)
            recs = crs.fetchall()
        return [rec["pkid"] for rec in recs]

    @property
    def image_names(self):
        if self.smart:
            recs = self.smart_album_images(self.pkid, return_objects=False)
        else:
            sql = """select image.name from image
                    join album_image on album_image.image_id = image.pkid
                    where album_image.album_id = %s"""
            with utils.DbCursor() as crs:
                crs.execute(sql, self.pkid)
            recs = crs.fetchall()
        return [rec["name"] for rec in recs]

    @property
    def image_count(self):
        return self._get_image_count(self.pkid)

    @classmethod
    def _get_image_count(cls, pkid, smart=False):
        if smart:
            return len(cls.smart_album_images(pkid))
        sql = """select count(*) as image_count from image
                join album_image on album_image.image_id = image.pkid
                where album_image.album_id = %s"""
        with utils.DbCursor() as crs:
            crs.execute(sql, pkid)
        return crs.fetchone()["image_count"]

    @classmethod
    def add_image_counts(cls, recs):
        """Add the image_count property as a key in each record."""
        for rec in recs:
            rec["image_count"] = cls._get_image_count(rec["pkid"], rec["smart"])

    @classmethod
    def smart_album_images(cls, pkid, return_objects=True):
        sql = "select rules from album where album.pkid = %s"
        with utils.DbCursor() as crs:
            crs.execute(sql, pkid)
        rules = json.loads(crs.fetchone()["rules"])
        filters = []
        joins = []
        mthds = {
            "keywords": cls._filter_keywords,
            "name": cls._filter_name,
            "orientation": cls._filter_orientation,
            "created": cls._filter_created,
            "year": cls._filter_year,
            "album": cls._filter_album,
        }
        for rule_dict in rules:
            field = next(iter(rule_dict))
            compval = rule_dict[field]
            comp = next(iter(compval))
            val = compval[comp]
            mthd = mthds[field]
            mthd(comp.lower(), val, filters, joins)
        where_clause = " AND ".join(filters)
        join_clause = " ".join(joins)
        sql = (
            f"select image.* from image {join_clause} "
            f"{'where' if where_clause else ''} {where_clause}"
        )
        with utils.DbCursor() as crs:
            crs.execute(sql)
        recs = crs.fetchall()
        if return_objects:
            return Image.from_recs(recs)
        return recs

    @classmethod
    def _filter_keywords(cls, comp, val, filters, joins):
        filters.append(
            rf"image.keywords {'not ' if 'does not contain' in comp.lower() else ''}regexp '\\b{val}\\b'"
        )

    @classmethod
    def _filter_name(cls, comp, val, filters, joins):
        if comp == "equals":
            clause = f"image.name = '{val}'"
        elif comp == "starts with":
            clause = f"image.name like '{val}%'"
        elif comp == "ends with":
            clause = f"image.name like '%{val}'"
        elif comp == "contains":
            clause = f"image.name like '%{val}%'"
        filters.append(clause)

    @classmethod
    def _filter_orientation(cls, comp, val, filters, joins):
        filters.append(f"image.orientation = '{comp[0].upper()}'")

    @classmethod
    def _filter_created(cls, comp, val, filters, joins):
        dateval = date_parser.parse(val)
        datestr = dateval.strftime("%Y-%m-%d %H:%M:%S")
        if comp == "equals":
            clause = f"image.created like '{datestr}%'"
        elif comp == "before":
            clause = f"image.created < '{datestr}'"
        elif comp == "after":
            clause = f"image.created > '{datestr}'"
        elif comp == "on or before":
            clause = f"image.created <= '{datestr}'"
        elif comp == "on or after":
            clause = f"image.created >= '{datestr}'"
        filters.append(clause)

    @classmethod
    def _filter_year(cls, comp, val, filters, joins):
        filters.append(f"year(image.created) = '{comp}'")

    @classmethod
    def _filter_album(cls, comp, val, filters, joins):
        joins.append("join album_image on image.pkid = album_image.image_id")
        filters.append(f"album_image.album_id {'!' if 'not a member' in comp else ''}= '{val}'")

    def update_images(self, image_ids):
        utils.debugout("UPD IMG CALLED")
        if self.smart:
            images = self.smart_album_images(self.pkid)
            image_ids = [img.pkid for img in images]
        else:
            current_ids = set(self.image_ids)
            selected_ids = set(image_ids)
            to_remove = current_ids.difference(selected_ids)
            to_add = selected_ids.difference(current_ids)
            utils.debugout("TOREMOVE", len(to_remove))
            utils.debugout("TOADD", len(to_add))
            self.remove_images(to_remove)
            self.add_images(to_add)
        utils.debugout("CALLING UPDATE_FRAME_ALBUM")
        self.update_frame_album(image_ids)

    def add_images(self, img_list):
        for img in img_list:
            self.add_image(img)

    def add_image(self, img):
        img_obj = Image.get(img)
        utils.debugout("Adding image to", self)
        sql = "insert into album_image (album_id, image_id) values (%s, %s);"
        with utils.DbCursor() as crs:
            crs.execute(sql, (self.pkid, img_obj.pkid))
        self._allocate_to_sub_albums(img_obj)

    def _allocate_to_sub_albums(self, img_obj):
        utils.debugout("ALLOC CALLED", len(self.sub_albums))
        if not self.sub_albums:
            return
        albums_by_image_count = sorted([ab for ab in self.sub_albums], key=lambda x: x.image_count)
        utils.debugout("ALBBYCOUNT", albums_by_image_count)
        # Add the new image to the first album in the list; it will have image_count <= the others
        utils.debugout("ADDING IMAGE TO", albums_by_image_count[0])
        albums_by_image_count[0].add_image(img_obj)

    def remove_images(self, img_list):
        for img in img_list:
            self.remove_image(img)

    def remove_image(self, img):
        img_obj = Image.get(img)
        sql = "delete from album_image where album_id = %s and image_id = %s;"
        with utils.DbCursor() as crs:
            crs.execute(sql, (self.pkid, img_obj.pkid))
        self._deallocate_from_sub_albums(img_obj)

    def _deallocate_from_sub_albums(self, img_obj):
        utils.debugout("DEALLOC CALLED", len(self.sub_albums))
        if not self.sub_albums:
            return
        try:
            sub_album_with_image = [ab for ab in self.sub_albums if img_obj.pkid in ab.image_ids][0]
        except IndexError:
            # No sub_album has that image
            return
        counts = [ab.image_count for ab in self.sub_albums]
        min_cnt, max_cnt = min(counts), max(counts)
        album_in_max_cnt_group = sub_album_with_image.image_count == max_cnt
        # First remove the image
        sub_album_with_image.remove_image(img_obj)
        if not album_in_max_cnt_group:
            # We need to  move an image from one of the albums with max_cnt.
            max_albums = [ab for ab in self.sub_albums if ab.image_count == max_cnt]
            max_album = random.choice(max_albums)
            image_to_move = random.choice(max_album.images)
            max_album.remove_image(image_to_move)
            sub_album_with_image.add_image(image_to_move)

    def set_frame_album(self, frame_id):
        utils.debugout("SET_FRAME_ALBUM called")
        image_names = []
        if self.image_ids:
            sql = "select name from image where pkid in %s;"
            with utils.DbCursor() as crs:
                crs.execute(sql, (self.image_ids,))
            image_names = [rec["name"] for rec in crs.fetchall()]
        utils.write_key(frame_id, "images", image_names)
        utils.debugout("Wrote images for frame_id =", frame_id)

    def update_frame_album(self, image_ids=None):
        """Updates the 'images' key for all frames that are linked to the album."""
        utils.debugout("UPDATE_FRAME_ALBUM called")
        image_ids = image_ids or self.image_ids
        sql = "select pkid from frame where album_id = %s;"
        with utils.DbCursor() as crs:
            count = crs.execute(sql, (self.pkid,))
            utils.debugout("FRAME COUNT", count)
            frame_ids = [rec["pkid"] for rec in crs.fetchall()]
            utils.debugout(
                "Album.update_frame_album; frame_ids=", frame_ids, "album_id =", self.pkid
            )
            if frame_ids:
                sql = "select name from image where pkid in %s;"
                crs.execute(sql, (image_ids,))
                image_names = [rec["name"] for rec in crs.fetchall()]
                for frame_id in frame_ids:
                    utils.write_key(frame_id, "images", image_names)
                    utils.debugout("Wrote images for frame_id =", frame_id)

    @classmethod
    def default_album_id(cls):
        sql = "select pkid from album where name = %s"
        with utils.DbCursor() as crs:
            crs.execute(sql, (cls.DEFAULT_ALBUM_NAME,))
        return crs.fetchone().get("pkid")


@dataclasses.dataclass
class Frame(Base):
    pkid: str = ""
    name: str = "-new frame-"
    frameset_id: str = ""
    frameset_name: str = ""
    album_id: str = ""
    description: str = ""
    orientation: str = "H"
    interval_time: int = 60
    interval_units: str = "M"
    variance_pct: int = 0
    halflife_interval: bool = 0
    shutdown: bool = 0
    brightness: Decimal = 1.0
    contrast: Decimal = 1.0
    saturation: Decimal = 1.0
    freespace: int = 0
    ip: str = ""
    updated: datetime = datetime.utcnow()
    log_level: str = "INFO"

    table_name = "frame"
    non_db_fields = ["frameset_name"]
    _write_keys = True

    @classmethod
    def _after_get(cls, rec):
        """We need to add the frameset name, if any, to the record."""
        sql = """select frameset.name
                from frameset
                where frameset.pkid = %s;"""
        with utils.DbCursor() as crs:
            crs.execute(sql, (rec["frameset_id"],))
        name_rec = crs.fetchone()
        rec["frameset_name"] = name_rec.get("name") if name_rec else ""

    @classmethod
    def _after_list(cls, recs):
        sql = """select frame.pkid, frameset.name, frameset.album_id
                from frame join frameset on frame.frameset_id = frameset.pkid;"""
        with utils.DbCursor() as crs:
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
        if not self._write_keys:
            return

        def safe_json(att):
            """Convert Decimal to str"""
            val = getattr(self, att)
            if isinstance(val, Decimal):
                return str(val)
            return val

        settings = (
            "name",
            "description",
            "orientation",
            "interval_time",
            "interval_units",
            "variance_pct",
            "brightness",
            "contrast",
            "saturation",
            "log_level",
        )
        settings_dict = {setting: safe_json(setting) for setting in settings}
        utils.write_key(self.pkid, "settings", settings_dict)

    def set_album(self, album_obj_or_id):
        if isinstance(album_obj_or_id, Album):
            self.album_id = album_obj_or_id.pkid
            album_obj = album_obj_or_id
        else:
            self.album_id = album_obj_or_id
            album_obj = Album.get(album_obj_or_id)
        save_keys = self._write_keys
        self._write_keys = False
        self.save()
        self._write_keys = save_keys
        # Update the etcd keys
        album_obj.set_frame_album(self.pkid)


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
        sql = "select frame.pkid from frame where frame.frameset_id = %s;"
        with utils.DbCursor() as crs:
            rec["num_frames"] = crs.execute(sql, (self.pkid,))

    @classmethod
    def _after_list(self, recs):
        """Add the frame counts."""
        sql = "select count(pkid) as num_frames, frameset_id from frame group by frameset_id;"
        with utils.DbCursor() as crs:
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
            # Already set
            return
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
        sql = "select pkid from frame where frameset_id = %s"
        with utils.DbCursor() as crs:
            crs.execute(sql, (self.pkid,))
        frame_ids = [rec["pkid"] for rec in crs.fetchall()]
        return [Frame.get(frame_id) for frame_id in frame_ids]

    @property
    def child_frame_ids(self):
        sql = "select pkid from frame where frameset_id = %s"
        with utils.DbCursor() as crs:
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
    custom_list = True

    @classmethod
    def _custom_where(cls, **kwargs):
        where = ""
        orient = kwargs.get("orientation")
        keywords = kwargs.get("keywords")
        if orient:
            where = f" image.orientation = '{orient}' "
        if keywords:
            words = [" keywords REGEXP '\\\\b%s\\\\b' " % word for word in keywords.split()]
            filt_clause = " and ".join(words)
            if where:
                where = f"{where} {filt_clause}"
            else:
                where = filt_clause
        return where
