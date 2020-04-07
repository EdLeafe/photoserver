from __future__ import print_function

import utils


def create_frame(crs):
    sql = "drop table if exists frame;"
    crs.execute(sql)
    sql = """
    create table frame (
        pkid VARCHAR(36) NOT NULL PRIMARY KEY,
        name VARCHAR(256) NOT NULL,
        frameset_id VARCHAR(36) NOT NULL,
        album_id VARCHAR(36),
        description VARCHAR(256),
        orientation ENUM('H', 'V', 'S') NOT NULL,
        interval_time SMALLINT UNSIGNED NOT NULL,
        interval_units VARCHAR(16) NOT NULL,
        variance_pct INT,
        shutdown tinyint(1) DEFAULT 0,
        brightness DECIMAL (4,3) UNSIGNED DEFAULT 1.0,
        contrast DECIMAL (4,3) UNSIGNED DEFAULT 1.0,
        saturation DECIMAL (4,3) UNSIGNED DEFAULT 1.0,
        freespace INT,
        ip VARCHAR(16),
        updated TIMESTAMP,
	log_level VARCHAR(4) NOT NULL DEFAULT 'INFO'
        );
    """
    crs.execute(sql)

def create_frameset(crs):
    sql = "drop table if exists frameset;"
    crs.execute(sql)
    sql = """
    create table frameset (
        pkid VARCHAR(36) NOT NULL PRIMARY KEY,
        name VARCHAR(256) NOT NULL,
        user_id VARCHAR(36),
        album_id VARCHAR(36),
        description VARCHAR(256),
        orientation ENUM('H', 'V', 'S') NOT NULL,
        interval_time SMALLINT UNSIGNED NOT NULL,
        interval_units VARCHAR(16) NOT NULL,
        variance_pct INT,
        updated TIMESTAMP
        );
    """
    crs.execute(sql)

def create_image(crs):
    sql = "drop table if exists image;"
    crs.execute(sql)
    sql = """
    create table image (
        pkid VARCHAR(36) NOT NULL PRIMARY KEY,
        keywords VARCHAR(256),
        name VARCHAR(256) NOT NULL,
        width INT NOT NULL,
        height INT NOT NULL,
        orientation ENUM('H', 'V', 'S') NOT NULL,
        imgtype VARCHAR(6),
        size INT,
        created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated TIMESTAMP
        );
    """
    crs.execute(sql)
    utils.update_img_db()

def create_album(crs):
    sql = "drop table if exists album;"
    crs.execute(sql)
    sql = """
    create table album (
        pkid VARCHAR(36) NOT NULL PRIMARY KEY,
        name VARCHAR(256) NOT NULL,
        orientation ENUM('H', 'V', 'S') NOT NULL,
        parent_id VARCHAR(36),
        updated TIMESTAMP
        );
    """
    crs.execute(sql)

def create_album_image(crs):
    sql = "drop table if exists album_image;"
    crs.execute(sql)
    sql = """
    create table album_image (
        album_id VARCHAR(36),
        image_id VARCHAR(36),
        PRIMARY KEY (album_id, image_id)
        );
    """
    crs.execute(sql)


def main(crs):
    create_frame(crs)
    create_frameset(crs)
    create_image(crs)
    create_album(crs)
    create_album_image(crs)


if __name__ == "__main__":
    crs = utils.get_cursor()
    main(crs)
