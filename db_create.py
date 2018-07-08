from __future__ import print_function

import utils

crs = utils.get_cursor()

sql = """
drop table if exists frame;
create table frame (
    pkid VARCHAR(36) NOT NULL PRIMARY KEY,
    name VARCHAR(256) NOT NULL,
    frameset_id VARCHAR(36) NOT NULL,
    album_id VARCHAR(36),
    description VARCHAR(256),
    orientation ENUM('H', 'V', 'S') NOT NULL,
    interval_time SMALLINT UNSIGNED NOT NULL,
    interval_units VARCHAR(16) NOT NULL,
    shutdown tinyint(1) DEFAULT 0,
    brightness DECIMAL (4,3) UNSIGNED DEFAULT 1.0,                              
    contrast DECIMAL (4,3) UNSIGNED DEFAULT 1.0,                                
    saturation DECIMAL (4,3) UNSIGNED DEFAULT 1.0,                              
    freespace INT,
    ip VARCHAR(16),
    updated TIMESTAMP
    );
"""
crs.execute(sql)
print("FRAME")

sql = """
drop table if exists frameset;
create table frameset (
    pkid VARCHAR(36) NOT NULL PRIMARY KEY,
    name VARCHAR(256) NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    updated TIMESTAMP
    );
"""
crs.execute(sql)
print("FRAMESET")

sql = """
drop table if exists frameset_frames;
create table frameset_frames (
    fs_id VARCHAR(36) NOT NULL,
    frame_id VARCHAR(36) NOT NULL
    );
"""
crs.execute(sql)
print("FRAMESET_FRAMES")

sql = """
drop table if exists image;
create table image (
    pkid VARCHAR(36) NOT NULL PRIMARY KEY,
    keywords VARCHAR(256),
    name VARCHAR(256) NOT NULL,
    width INT NOT NULL,
    height INT NOT NULL,
    orientation ENUM('H', 'V', 'S') NOT NULL,
    imgtype VARCHAR(6), 
    size INT,
    updated TIMESTAMP
    );
"""
crs.execute(sql)
utils.update_img_db()
print("IMAGE")

sql = """
drop table if exists frame_image;
create table frame_image (
    frame_id VARCHAR(36),
    image_id VARCHAR(36),
    PRIMARY KEY (frame_id, image_id)
    );
"""
crs.execute(sql)
print("FRAME_IMAGE")

sql = """
drop table if exists album;
create table album (
    pkid VARCHAR(36) NOT NULL PRIMARY KEY,
    name VARCHAR(256) NOT NULL,
    orientation ENUM('H', 'V', 'S') NOT NULL,
    updated TIMESTAMP
    );
"""
crs.execute(sql)
print("ALBUM")

sql = """
drop table if exists album_image;
create table album_image (
    album_id VARCHAR(36),
    image_id VARCHAR(36),
    PRIMARY KEY (album_id, image_id)
    );
"""
crs.execute(sql)
print("ALBUM_IMAGE")
