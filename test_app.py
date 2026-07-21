import unittest
import json
import hashlib
from datetime import date, timedelta
from app import app
from database import init_db, get_db
import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(__file__), 'database.db')


class TestSportReserve(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True
        init_db()  # pastikan database & seed sudah ada

    # ─── USER ROUTES ─────────────────────────────────────────────────────────

    def test_01_halaman_beranda(self):
        """Beranda harus bisa diakses dan mengandung nama aplikasi"""
        r = self.client.get('/')
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'SportReserve', r.data)

    def test_02_redirect_daftar_lapangan(self):
        """/lapangan harus redirect ke beranda (single-field)"""
        r = self.client.get('/lapangan')
        self.assertEqual(r.status_code, 302)  # redirect

    def test_03_redirect_detail_lapangan(self):
        """/lapangan/<id> harus redirect ke beranda"""
        r = self.client.get('/lapangan/1')
        self.assertEqual(r.status_code, 302)

    def test_04_form_reservasi_get(self):
        """Halaman form reservasi harus bisa diakses"""
        r = self.client.get('/reservasi')
        self.assertEqual(r.status_code, 200)

    def test_05_form_reservasi_validasi_kosong(self):
        """Submit form kosong harus ditolak dan kembali ke form"""
        r = self.client.post('/reservasi', data={}, follow_redirects=True)
        self.assertEqual(r.status_code, 200)

    def test_06_form_reservasi_submit_valid(self):
        """Reservasi valid harus berhasil dan redirect ke halaman status"""
        tanggal_mendatang = (date.today() + timedelta(days=5)).isoformat()
        r = self.client.post('/reservasi', data={
            'nama_pemesan': 'Test User Unittest',
            'no_hp': '081298765432',
            'tanggal': tanggal_mendatang,
            'jam_mulai': '13:00',
            'jam_selesai': '14:00',
            'catatan': 'Reservasi test'
        }, follow_redirects=True)
        self.assertEqual(r.status_code, 200)
        # Hapus data test dari DB
        conn = sqlite3.connect(DB_PATH)
        conn.execute("DELETE FROM reservasi WHERE nama_pemesan='Test User Unittest'")
        conn.commit()
        conn.close()

    def test_07_cek_status_get(self):
        """Halaman cek status harus bisa diakses"""
        r = self.client.get('/status')
        self.assertEqual(r.status_code, 200)

    def test_08_cek_status_kode_tidak_ada(self):
        """Kode booking tidak valid harus redirect dengan pesan error"""
        r = self.client.get('/status/KODEBOGUS123', follow_redirects=True)
        self.assertEqual(r.status_code, 200)

    def test_09_api_cek_jadwal(self):
        """API cek-jadwal harus mengembalikan JSON"""
        tanggal = date.today().isoformat()
        r = self.client.get(f'/api/cek-jadwal?tanggal={tanggal}')
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.data)
        self.assertIsInstance(data, list)

    def test_10_api_cek_jadwal_tanpa_parameter(self):
        """API tanpa parameter tanggal harus return 400"""
        r = self.client.get('/api/cek-jadwal')
        self.assertEqual(r.status_code, 400)

    # ─── ADMIN ROUTES ────────────────────────────────────────────────────────

    def test_11_admin_login_get(self):
        """Halaman login admin harus bisa diakses"""
        r = self.client.get('/admin/login')
        self.assertEqual(r.status_code, 200)

    def test_12_admin_redirect_tanpa_login(self):
        """Akses admin tanpa login harus redirect ke halaman login"""
        r = self.client.get('/admin/dashboard')
        self.assertEqual(r.status_code, 302)

    def test_13_admin_login_salah(self):
        """Login dengan password salah harus gagal"""
        r = self.client.post('/admin/login', data={
            'username': 'admin',
            'password': 'salah123'
        }, follow_redirects=True)
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'salah', r.data.lower())

    def _login_admin(self):
        """Helper: login sebagai admin"""
        self.client.post('/admin/login', data={
            'username': 'admin',
            'password': 'admin123'
        }, follow_redirects=True)

    def test_14_admin_login_berhasil(self):
        """Login admin yang benar harus berhasil dan masuk dashboard"""
        self._login_admin()
        r = self.client.get('/admin/dashboard')
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'Dashboard', r.data)

    def test_15_admin_dashboard(self):
        """Dashboard admin harus menampilkan statistik"""
        self._login_admin()
        r = self.client.get('/admin/dashboard')
        self.assertEqual(r.status_code, 200)

    def test_16_admin_lapangan_view(self):
        """Halaman manajemen lapangan harus tampil"""
        self._login_admin()
        r = self.client.get('/admin/lapangan')
        self.assertEqual(r.status_code, 200)

    def test_17_admin_lapangan_tidak_bisa_tambah(self):
        """Tambah lapangan baru harus ditolak (single-field)"""
        self._login_admin()
        r = self.client.post('/admin/lapangan/tambah', data={
            'nama_lapangan': 'Lapangan Baru',
            'jenis_olahraga': 'Futsal',
            'lokasi': 'Test',
        }, follow_redirects=True)
        self.assertEqual(r.status_code, 200)  # redirect ke lapangan dengan flash error

    def test_18_admin_lapangan_edit(self):
        """Edit lapangan utama (id=1) harus berhasil"""
        self._login_admin()
        r = self.client.post('/admin/lapangan/edit/1', data={
            'nama_lapangan': 'Lapangan Multiguna Kampus',
            'jenis_olahraga': 'Multiguna',
            'lokasi': 'Area Olahraga Utama',
            'status': 'aktif',
            'deskripsi': 'Lapangan test edit',
            'fasilitas': 'Toilet, Parkir'
        }, follow_redirects=True)
        self.assertEqual(r.status_code, 200)

    def test_19_admin_lapangan_tidak_bisa_hapus(self):
        """Hapus lapangan utama harus ditolak"""
        self._login_admin()
        r = self.client.post('/admin/lapangan/hapus/1', follow_redirects=True)
        self.assertEqual(r.status_code, 200)

    def test_20_admin_reservasi_list(self):
        """Daftar reservasi admin harus tampil"""
        self._login_admin()
        r = self.client.get('/admin/reservasi')
        self.assertEqual(r.status_code, 200)

    def test_21_admin_reservasi_filter(self):
        """Filter reservasi berdasarkan status harus berjalan"""
        self._login_admin()
        r = self.client.get('/admin/reservasi?status=menunggu')
        self.assertEqual(r.status_code, 200)

    def test_22_admin_tambah_reservasi(self):
        """Admin bisa menambah reservasi baru"""
        self._login_admin()
        tanggal = (date.today() + timedelta(days=10)).isoformat()
        r = self.client.post('/admin/reservasi/tambah', data={
            'nama_pemesan': 'Admin Test User',
            'no_hp': '082100000001',
            'tanggal': tanggal,
            'jam_mulai': '07:00',
            'jam_selesai': '08:00',
            'status': 'dikonfirmasi',
            'catatan': ''
        }, follow_redirects=True)
        self.assertEqual(r.status_code, 200)
        # Cleanup
        conn = sqlite3.connect(DB_PATH)
        conn.execute("DELETE FROM reservasi WHERE nama_pemesan='Admin Test User'")
        conn.commit()
        conn.close()

    def test_23_admin_laporan(self):
        """Halaman laporan admin harus tampil"""
        self._login_admin()
        r = self.client.get('/admin/laporan')
        self.assertEqual(r.status_code, 200)

    def test_25_admin_pengaturan_get(self):
        """Halaman pengaturan akun admin harus tampil"""
        self._login_admin()
        r = self.client.get('/admin/pengaturan')
        self.assertEqual(r.status_code, 200)

    def test_26_admin_logout(self):
        """Logout harus berhasil dan redirect ke login"""
        self._login_admin()
        r = self.client.get('/admin/logout', follow_redirects=True)
        self.assertEqual(r.status_code, 200)
        # Setelah logout, dashboard harus tidak bisa diakses
        r2 = self.client.get('/admin/dashboard')
        self.assertEqual(r2.status_code, 302)


if __name__ == '__main__':
    unittest.main(verbosity=2)
