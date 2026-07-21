import sqlite3
import hashlib
import os
from flask import g, current_app

DATABASE = os.path.join(os.path.dirname(__file__), 'database.db')

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
    return db

def init_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")

    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id_user INTEGER PRIMARY KEY AUTOINCREMENT,
            nama TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS lapangan (
            id_lapangan INTEGER PRIMARY KEY AUTOINCREMENT,
            nama_lapangan TEXT NOT NULL,
            jenis_olahraga TEXT NOT NULL,
            lokasi TEXT NOT NULL,
            harga_per_jam REAL NOT NULL DEFAULT 0,
            status TEXT DEFAULT 'aktif',
            deskripsi TEXT,
            fasilitas TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS reservasi (
            id_reservasi INTEGER PRIMARY KEY AUTOINCREMENT,
            nama_pemesan TEXT NOT NULL,
            no_hp TEXT NOT NULL,
            id_lapangan INTEGER NOT NULL,
            tanggal TEXT NOT NULL,
            jam_mulai TEXT NOT NULL,
            jam_selesai TEXT NOT NULL,
            status TEXT DEFAULT 'menunggu',
            kode_booking TEXT UNIQUE NOT NULL,
            total_harga REAL DEFAULT 0,
            catatan TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (id_lapangan) REFERENCES lapangan(id_lapangan)
        );
    """)

    # Seed admin default
    admin_pw = hashlib.sha256('admin123'.encode()).hexdigest()
    existing = db.execute("SELECT id_user FROM users WHERE username='admin'").fetchone()
    if not existing:
        db.execute(
            "INSERT INTO users (nama, username, email, password, role) VALUES (?,?,?,?,?)",
            ('Administrator', 'admin', 'admin@sportreserve.com', admin_pw, 'admin')
        )

    # Seed data lapangan contoh
    count = db.execute("SELECT COUNT(*) FROM lapangan").fetchone()[0]
    if count == 0:
        lapangan_data = [
            ('Lapangan Multiguna Kampus', 'Multiguna', 'Area Olahraga Utama', 0, 'aktif',
             'Lapangan olahraga multiguna untuk seluruh civitas akademika kampus. Dapat digunakan untuk futsal, basket, voli, dan badminton.',
             'Toilet, Ruang Ganti, Tribun Penonton, Parkir, Penerangan LED Malam'),
        ]
        for d in lapangan_data:
            db.execute(
                """INSERT INTO lapangan (nama_lapangan, jenis_olahraga, lokasi, harga_per_jam,
                   status, deskripsi, fasilitas) VALUES (?,?,?,?,?,?,?)""", d
            )

        # Seed beberapa reservasi contoh
        import random
        from datetime import date, timedelta
        kode_set = set()
        for i in range(15):
            while True:
                kode = f"RSV202407{random.randint(10000, 99999)}"
                if kode not in kode_set:
                    kode_set.add(kode)
                    break
            tgl = (date.today() + timedelta(days=random.randint(-5, 5))).isoformat()
            jam_m = random.choice(['08:00', '09:00', '10:00', '13:00', '14:00', '15:00', '16:00', '17:00'])
            jam_s_map = {'08:00': '09:00', '09:00': '10:00', '10:00': '11:00',
                         '13:00': '14:00', '14:00': '15:00', '15:00': '16:00',
                         '16:00': '17:00', '17:00': '18:00'}
            jam_s = jam_s_map[jam_m]
            id_lap = 1
            lap_harga = 0
            status = random.choice(['menunggu', 'dikonfirmasi', 'dikonfirmasi', 'selesai'])
            db.execute(
                """INSERT OR IGNORE INTO reservasi (nama_pemesan, no_hp, id_lapangan, tanggal,
                   jam_mulai, jam_selesai, status, kode_booking, total_harga)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (f'Pelanggan {i+1}', f'08{random.randint(100000000, 999999999)}',
                 id_lap, tgl, jam_m, jam_s, status, kode, lap_harga)
            )

    db.commit()
    db.close()
