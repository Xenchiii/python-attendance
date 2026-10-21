import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

import pymysql
import pymysql.cursors

BACKEND = os.environ.get("DB_BACKEND", "sqlite").lower()
SQLITE_PATH = os.environ.get("SQLITE_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "qr_attendance.db"))
STAMP = "%Y-%m-%d %H:%M:%S"

IntegrityError = (sqlite3.IntegrityError, pymysql.err.IntegrityError)


def configure(backend=None, sqlite_path=None):
    global BACKEND, SQLITE_PATH
    if backend:
        BACKEND = backend.lower()
    if sqlite_path:
        SQLITE_PATH = sqlite_path


def now():
    return datetime.now(timezone.utc).strftime(STAMP)


def stamp(value):
    return value.strftime(STAMP)


def iso(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%dT%H:%M:%S") + "Z"
    return str(value).replace(" ", "T")[:19] + "Z"


def concat(*parts):
    if BACKEND == "mysql":
        return "CONCAT(" + ", ".join(parts) + ")"
    return "(" + " || ".join(parts) + ")"


def connect():
    if BACKEND == "mysql":
        return pymysql.connect(
            host=os.environ.get("DB_HOST", "localhost"),
            port=int(os.environ.get("DB_PORT", "3306")),
            user=os.environ.get("DB_USER", "root"),
            password=os.environ.get("DB_PASS", ""),
            database=os.environ.get("DB_NAME", "qr_attendance"),
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False,
        )
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def adapt(sql):
    return sql.replace("?", "%s") if BACKEND == "mysql" else sql


class Tx:
    def __init__(self, conn):
        self.conn = conn

    def run(self, sql, *args):
        cursor = self.conn.cursor()
        cursor.execute(adapt(sql), args)
        return cursor

    def query(self, sql, *args):
        cursor = self.run(sql, *args)
        return [dict(row) for row in cursor.fetchall()]

    def one(self, sql, *args):
        rows = self.query(sql, *args)
        return rows[0] if rows else None


@contextmanager
def tx():
    conn = connect()
    try:
        yield Tx(conn)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def query(sql, *args):
    with tx() as t:
        return t.query(sql, *args)


def one(sql, *args):
    with tx() as t:
        return t.one(sql, *args)


def execute(sql, *args):
    with tx() as t:
        return t.run(sql, *args).lastrowid


def init_schema(path):
    with open(path, "r", encoding="utf-8") as handle:
        script = handle.read()
    conn = connect()
    try:
        if BACKEND == "mysql":
            cursor = conn.cursor()
            for statement in [s.strip() for s in script.split(";\n") if s.strip()]:
                cursor.execute(statement)
        else:
            conn.executescript(script)
        conn.commit()
    finally:
        conn.close()
