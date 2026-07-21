import unittest
import json
from app import app
from database import get_db

class TestSportReserve(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_index(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'SportReserve', response.data)

    def test_daftar_lapangan(self):
        response = self.app.get('/lapangan')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Daftar Lapangan', response.data)

    def test_daftar_lapangan_filter(self):
        response = self.app.get('/lapangan?jenis=Futsal')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Futsal', response.data)

    def test_detail_lapangan(self):
        response = self.app.get('/lapangan/1')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Informasi Lapangan', response.data)

    def test_form_reservasi_get(self):
        response = self.app.get('/reservasi')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Buat Reservasi', response.data)

    def test_cek_status_get(self):
        response = self.app.get('/status')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Cek Status', response.data)

    def test_admin_login_get(self):
        response = self.app.get('/admin/login')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Admin Login', response.data)

    def test_admin_flow(self):
        # 1. Login
        response = self.app.post('/admin/login', data={
            'username': 'admin',
            'password': 'admin123'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Dashboard', response.data)

        # 2. View Dashboard
        response = self.app.get('/admin/dashboard')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Dashboard', response.data)

        # 3. View Lapangan CRUD
        response = self.app.get('/admin/lapangan')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Manajemen Lapangan', response.data)

        # 4. View Reservasi CRUD
        response = self.app.get('/admin/reservasi')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Manajemen Reservasi', response.data)

        # 5. View Laporan
        response = self.app.get('/admin/laporan')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Laporan Bulanan', response.data)

        # 6. CRUD Lapangan - Create
        response = self.app.post('/admin/lapangan/tambah', data={
            'nama_lapangan': 'Lapangan Test Baru',
            'jenis_olahraga': 'Futsal',
            'lokasi': 'Test Area',
            'harga_per_jam': '125000',
            'status': 'aktif',
            'deskripsi': 'Deskripsi test',
            'fasilitas': 'Fasilitas test'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Lapangan Test Baru', response.data)

        # Find the ID of the new Lapangan
        import sqlite3
        conn = sqlite3.connect('database.db')
        conn.row_factory = sqlite3.Row
        lap = conn.execute("SELECT id_lapangan FROM lapangan WHERE nama_lapangan='Lapangan Test Baru'").fetchone()
        self.assertIsNotNone(lap)
        lap_id = lap['id_lapangan']

        # 7. CRUD Lapangan - Update
        response = self.app.post(f'/admin/lapangan/edit/{lap_id}', data={
            'nama_lapangan': 'Lapangan Test Edited',
            'jenis_olahraga': 'Futsal',
            'lokasi': 'Test Area Modified',
            'harga_per_jam': '130000',
            'status': 'aktif',
            'deskripsi': 'Deskripsi test edited',
            'fasilitas': 'Fasilitas test edited'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Lapangan Test Edited', response.data)

        # 8. CRUD Reservasi - Create
        response = self.app.post('/admin/reservasi/tambah', data={
            'nama_pemesan': 'Pemesan Test',
            'no_hp': '081234567890',
            'id_lapangan': str(lap_id),
            'tanggal': '2026-12-25',
            'jam_mulai': '10:00',
            'jam_selesai': '12:00',
            'status': 'menunggu'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Pemesan Test', response.data)

        # Find the ID of the new Reservasi
        res = conn.execute("SELECT id_reservasi FROM reservasi WHERE nama_pemesan='Pemesan Test'").fetchone()
        self.assertIsNotNone(res)
        res_id = res['id_reservasi']

        # 9. CRUD Reservasi - Update (Edit status / details)
        response = self.app.post(f'/admin/reservasi/edit/{res_id}', data={
            'nama_pemesan': 'Pemesan Test Edited',
            'no_hp': '081234567899',
            'id_lapangan': str(lap_id),
            'tanggal': '2026-12-25',
            'jam_mulai': '10:00',
            'jam_selesai': '12:00',
            'status': 'dikonfirmasi'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Pemesan Test Edited', response.data)

        # 10. CRUD Reservasi - Delete
        response = self.app.post(f'/admin/reservasi/hapus/{res_id}', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b'Pemesan Test Edited', response.data)

        # 11. CRUD Lapangan - Delete
        response = self.app.post(f'/admin/lapangan/hapus/{lap_id}', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b'Lapangan Test Edited', response.data)
        conn.close()


if __name__ == '__main__':
    unittest.main()
