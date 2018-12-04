import os
import pickle
import sqlite3

DB = os.path.join(os.getcwd(), "db", "session_data.db")
conn = None

def create_tables():
    crs = get_cursor()
    cmd = "CREATE TABLE sessions (user text, data blob)"
    crs.execute(cmd)
    conn.commit()


def store_data(user, data):
    crs = get_cursor()
    pdata = pickle.dumps(data)
    cmd = "INSERT INTO sessions (user, data) VALUES (?, ?)"
    crs.execute(cmd, (user, pdata))
    conn.commit()


def get_user_data(user):
    crs = get_cursor()
    cmd = "SELECT data FROM sessions where user = ?"
    crs.execute(cmd, (user,))
    rec = crs.fetchone()
    if rec:
        return pickle.loads(rec[0])


def get_cursor():
    global conn
    conn = sqlite3.connect(DB)
    return conn.cursor()
