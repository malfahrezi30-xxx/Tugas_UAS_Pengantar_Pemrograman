"""
database.py — Dual-mode database support
  - Local development : SQLite (default, no extra config)
  - Production (Vercel): PostgreSQL via DATABASE_URL environment variable
"""

import sqlite3
import hashlib
import os
import re

from flask import g

# ─── Detect environment ───────────────────────────────────────────────────────
DATABASE_URL = os.environ.get('DATABASE_URL')
IS_POSTGRES  = bool(DATABASE_URL)
DATABASE     = os.path.join(os.path.dirname(__file__), 'database.db')

if IS_POSTGRES:
    import psycopg2
    import psycopg2.extras


# ─── Row Wrappers ─────────────────────────────────────────────────────────────

class SmartRow(dict):
    """Dict that also supports integer-based indexing (like sqlite3.Row)."""
    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)


# ─── PostgreSQL Wrapper ───────────────────────────────────────────────────────

class _PostgresCursor:
    """Wraps a psycopg2 RealDictCursor to return SmartRow objects."""
    def __init__(self, cursor):
        self._cur = cursor

    def fetchone(self):
        row = self._cur.fetchone()
        return SmartRow(row) if row is not None else None

    def fetchall(self):
        return [SmartRow(r) for r in self._cur.fetchall()]


class PostgresDB:
    """Wraps a psycopg2 connection with a sqlite3-compatible API."""

    def __init__(self, conn):
        self.conn = conn

    # --- Query Translation ---
    @staticmethod
    def _translate(query):
        """Convert SQLite-flavored SQL to PostgreSQL."""
        # ? → %s positional params
        query = query.replace('?', '%s')
        # strftime('%Y-%m', col) → TO_CHAR(col, 'YYYY-MM')
        query = re.sub(
            r"strftime\('%Y-%m',\s*([^)]+?)\)",
            r"TO_CHAR(\1, 'YYYY-MM')",
            query
        )
        # date('now', '-N months') → (CURRENT_DATE - INTERVAL 'N months')
        query = re.sub(
            r"date\('now',\s*'-(\d+)\s*months?'\)",
            r"(CURRENT_DATE - INTERVAL '\1 months')",
            query
        )
        # INSERT OR IGNORE → INSERT (ON CONFLICT DO NOTHING added separately)
        query = re.sub(r'INSERT\s+OR\s+IGNORE\s+', 'INSERT ', query, flags=re.IGNORECASE)
        return query

    def execute(self, query, params=()):
        query = self._translate(query)
        cur = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(query, params if params else None)
        return _PostgresCursor(cur)

    def execute_ignore(self, query, params=()):
        """Execute an INSERT that should silently ignore conflicts."""
        query = self._translate(query)
        if 'ON CONFLICT' not in query.upper():
            query = query.rstrip().rstrip(';') + ' ON CONFLICT DO NOTHING'
        cur = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(query, params if params else None)
        return _PostgresCursor(cur)

    def commit(self):
        self.conn.commit()

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass


# ─── SQLite Wrapper ───────────────────────────────────────────────────────────

class SQLiteDB:
    """Thin wrapper around sqlite3 connection for API consistency."""
    def __init__(self, conn):
        self.conn = conn

    def execute(self, query, params=()):
        return self.conn.execute(query, params)

    def execute_ignore(self, query, params=()):
        return self.conn.execute(query, params)

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()


# ─── Connection Factory ───────────────────────────────────────────────────────

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        if IS_POSTGRES:
            conn = psycopg2.connect(DATABASE_URL, sslmode='require')
            db = g._database = PostgresDB(conn)
        else:
            conn = sqlite3.connect(DATABASE)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            db = g._database = SQLiteDB(conn)
    return db


# ─── DB Initialization ────────────────────────────────────────────────────────

_db_initialized = False   # per-process flag to avoid re-running DDL

def init_db():
    global _db_initialized
    if _db_initialized:
        return
    _db_initialized = True

    if IS_POSTGRES:
        _init_postgres()
    else:
        _init_sqlite()


def _init_sqlite():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")

    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id_user   INTEGER PRIMARY KEY AUTOINCREMENT,
            nama      TEXT NOT NULL,
            username  TEXT UNIQUE NOT NULL,
            email     TEXT UNIQUE,
            password  TEXT NOT NULL,
            role      TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS lapangan (
            id_lapangan    INTEGER PRIMARY KEY AUTOINCREMENT,
            nama_lapangan  TEXT NOT NULL,
            jenis_olahraga TEXT NOT NULL,
            lokasi         TEXT NOT NULL,
            harga_per_jam  REAL NOT NULL DEFAULT 0,
            status         TEXT DEFAULT 'aktif',
            deskripsi      TEXT,
            fasilitas      TEXT,
            created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS reservasi (
            id_reservasi INTEGER PRIMARY KEY AUTOINCREMENT,
            nama_pemesan TEXT NOT NULL,
            no_hp        TEXT NOT NULL,
            id_lapangan  INTEGER NOT NULL,
            tanggal      TEXT NOT NULL,
            jam_mulai    TEXT NOT NULL,
            jam_selesai  TEXT NOT NULL,
            status       TEXT DEFAULT 'menunggu',
            kode_booking TEXT UNIQUE NOT NULL,
            total_harga  REAL DEFAULT 0,
            catatan      TEXT,
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (id_lapangan) REFERENCES lapangan(id_lapangan)
        );
    """)

    _seed_data_sqlite(db)
    db.commit()
    db.close()


def _init_postgres():
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    cur  = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id_user    SERIAL PRIMARY KEY,
            nama       TEXT NOT NULL,
            username   TEXT UNIQUE NOT NULL,
            email      TEXT UNIQUE,
            password   TEXT NOT NULL,
            role       TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS lapangan (
            id_lapangan    SERIAL PRIMARY KEY,
            nama_lapangan  TEXT NOT NULL,
            jenis_olahraga TEXT NOT NULL,
            lokasi         TEXT NOT NULL,
            harga_per_jam  REAL NOT NULL DEFAULT 0,
            status         TEXT DEFAULT 'aktif',
            deskripsi      TEXT,
            fasilitas      TEXT,
            created_at     TIMESTAMP DEFAULT NOW()
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS reservasi (
            id_reservasi INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            nama_pemesan TEXT NOT NULL,
            no_hp        TEXT NOT NULL,
            id_lapangan  INTEGER NOT NULL REFERENCES lapangan(id_lapangan),
            tanggal      TEXT NOT NULL,
            jam_mulai    TEXT NOT NULL,
            jam_selesai  TEXT NOT NULL,
            status       TEXT DEFAULT 'menunggu',
            kode_booking TEXT UNIQUE NOT NULL,
            total_harga  REAL DEFAULT 0,
            catatan      TEXT,
            created_at   TIMESTAMP DEFAULT NOW()
        )
    """)

    conn.commit()
    _seed_data_postgres(conn, cur)
    conn.commit()
    cur.close()
    conn.close()


# ─── Seed Data ────────────────────────────────────────────────────────────────

def _seed_data_sqlite(db):
    admin_pw = hashlib.sha256('admin123'.encode()).hexdigest()
    existing = db.execute("SELECT id_user FROM users WHERE username='admin'").fetchone()
    if not existing:
        db.execute(
            "INSERT INTO users (nama, username, email, password, role) VALUES (?,?,?,?,?)",
            ('Administrator', 'admin', 'admin@sportreserve.com', admin_pw, 'admin')
        )

    count = db.execute("SELECT COUNT(*) FROM lapangan").fetchone()[0]
    if count == 0:
        db.execute(
            """INSERT INTO lapangan (nama_lapangan, jenis_olahraga, lokasi, harga_per_jam,
               status, deskripsi, fasilitas) VALUES (?,?,?,?,?,?,?)""",
            ('Lapangan Multiguna Kampus', 'Multiguna', 'Area Olahraga Utama', 0, 'aktif',
             'Lapangan olahraga multiguna untuk seluruh civitas akademika kampus. '
             'Dapat digunakan untuk futsal, basket, voli, dan badminton.',
             'Toilet, Ruang Ganti, Tribun Penonton, Parkir, Penerangan LED Malam')
        )
        _seed_reservasi_sqlite(db)


def _seed_reservasi_sqlite(db):
    import random
    from datetime import date, timedelta
    kode_set = set()
    for i in range(15):
        while True:
            kode = f"RSV202407{random.randint(10000, 99999)}"
            if kode not in kode_set:
                kode_set.add(kode)
                break
        tgl   = (date.today() + timedelta(days=random.randint(-5, 5))).isoformat()
        jam_m = random.choice(['08:00','09:00','10:00','13:00','14:00','15:00','16:00','17:00'])
        jam_s_map = {
            '08:00': '09:00', '09:00': '10:00', '10:00': '11:00',
            '13:00': '14:00', '14:00': '15:00', '15:00': '16:00',
            '16:00': '17:00', '17:00': '18:00'
        }
        jam_s  = jam_s_map[jam_m]
        status = random.choice(['menunggu','dikonfirmasi','dikonfirmasi','selesai'])
        db.execute(
            """INSERT OR IGNORE INTO reservasi
               (nama_pemesan, no_hp, id_lapangan, tanggal,
                jam_mulai, jam_selesai, status, kode_booking, total_harga)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (f'Pelanggan {i+1}', f'08{random.randint(100000000,999999999)}',
             1, tgl, jam_m, jam_s, status, kode, 0)
        )


def _seed_data_postgres(conn, cur):
    admin_pw = hashlib.sha256('admin123'.encode()).hexdigest()
    cur.execute("SELECT id_user FROM users WHERE username='admin'")
    if cur.fetchone() is None:
        cur.execute(
            "INSERT INTO users (nama, username, email, password, role) VALUES (%s,%s,%s,%s,%s)",
            ('Administrator', 'admin', 'admin@sportreserve.com', admin_pw, 'admin')
        )

    cur.execute("SELECT COUNT(*) FROM lapangan")
    if cur.fetchone()[0] == 0:
        cur.execute(
            """INSERT INTO lapangan
               (nama_lapangan, jenis_olahraga, lokasi, harga_per_jam, status, deskripsi, fasilitas)
               VALUES (%s,%s,%s,%s,%s,%s,%s)""",
            ('Lapangan Multiguna Kampus', 'Multiguna', 'Area Olahraga Utama', 0, 'aktif',
             'Lapangan olahraga multiguna untuk seluruh civitas akademika kampus. '
             'Dapat digunakan untuk futsal, basket, voli, dan badminton.',
             'Toilet, Ruang Ganti, Tribun Penonton, Parkir, Penerangan LED Malam')
        )
        conn.commit()
        _seed_reservasi_postgres(conn, cur)


def _seed_reservasi_postgres(conn, cur):
    import random
    from datetime import date, timedelta
    kode_set = set()
    for i in range(15):
        while True:
            kode = f"RSV202407{random.randint(10000, 99999)}"
            if kode not in kode_set:
                kode_set.add(kode)
                break
        tgl   = (date.today() + timedelta(days=random.randint(-5, 5))).isoformat()
        jam_m = random.choice(['08:00','09:00','10:00','13:00','14:00','15:00','16:00','17:00'])
        jam_s_map = {
            '08:00': '09:00', '09:00': '10:00', '10:00': '11:00',
            '13:00': '14:00', '14:00': '15:00', '15:00': '16:00',
            '16:00': '17:00', '17:00': '18:00'
        }
        jam_s  = jam_s_map[jam_m]
        status = random.choice(['menunggu','dikonfirmasi','dikonfirmasi','selesai'])
        cur.execute(
            """INSERT INTO reservasi
               (nama_pemesan, no_hp, id_lapangan, tanggal,
                jam_mulai, jam_selesai, status, kode_booking, total_harga)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT DO NOTHING""",
            (f'Pelanggan {i+1}', f'08{random.randint(100000000,999999999)}',
             1, tgl, jam_m, jam_s, status, kode, 0)
        )
