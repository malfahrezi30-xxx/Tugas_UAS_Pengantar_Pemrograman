# 🏟️ SportReserve — Sistem Informasi Reservasi Lapangan Olahraga

Aplikasi web berbasis **Python + Flask** untuk mengelola reservasi lapangan olahraga secara online.

---

## 📋 Fitur Utama

### 👥 Sisi Pengguna (User)
- Beranda dengan info lapangan, jadwal 7 hari ke depan & statistik
- Kalender slot waktu interaktif (tersedia/terpesan)
- Form reservasi dengan **cek bentrok otomatis**
- **QR Code** + kode booking unik untuk setiap reservasi
- Cek status reservasi via kode booking
- Field catatan opsional saat reservasi

### 🔐 Sisi Admin
- Login dengan autentikasi session (SHA-256)
- Dashboard dengan statistik & grafik (Chart.js)
- **Edit** info lapangan (nama, jenis, lokasi, fasilitas, deskripsi)
- CRUD Reservasi: Tambah, Edit, Konfirmasi, Batalkan, Hapus
- Laporan per bulan: ringkasan + grafik reservasi per hari
- Detail reservasi + QR Code
- Filter & pencarian reservasi (status, tanggal, nama/kode)

---

## 🛠️ Teknologi

| Komponen     | Teknologi          |
|--------------|--------------------|
| Bahasa       | Python 3.x         |
| Framework    | Flask              |
| Database     | SQLite             |
| Frontend     | HTML, CSS, JS      |
| QR Code      | qrcode (Python)    |

---

## 🚀 Cara Instalasi & Menjalankan

### 1. Clone Repository
```bash
git clone https://github.com/malfahrezi30-xxx/Tugas_UAS_Pengantar_Pemrograman.git
cd Tugas_UAS_Pengantar_Pemrograman
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Jalankan Aplikasi
```bash
python app.py
```

### 4. Buka di Browser
```
http://localhost:5000
```

---

## 🔑 Login Admin Default

| Field    | Value      |
|----------|------------|
| Username | `admin`    |
| Password | `admin123` |

---

## 📁 Struktur Proyek

```
Tugas_UAS_Pengantar_Pemrograman/
│
├── app.py                  # File utama Flask (routes & logic)
├── database.py             # Koneksi & inisialisasi database SQLite
├── test_app.py             # Unit tests (24 test cases)
├── requirements.txt        # Dependensi Python
├── .gitignore
├── README.md
│
├── templates/
│   ├── base.html           # Layout dasar user
│   ├── index.html          # Beranda + kalender jadwal
│   ├── form_reservasi.html # Form buat reservasi
│   ├── cek_status.html     # Halaman cek kode booking
│   ├── status_reservasi.html # Detail + QR Code reservasi
│   └── admin/
│       ├── base_admin.html
│       ├── login.html
│       ├── dashboard.html  # Statistik & grafik
│       ├── lapangan.html   # Manajemen lapangan
│       ├── form_lapangan.html
│       ├── reservasi.html  # Daftar reservasi
│       ├── form_reservasi.html
│       ├── detail_reservasi.html
│       └── laporan.html    # Laporan bulanan
│
└── static/
    ├── css/
    │   ├── style.css       # Styling halaman user
    │   └── admin.css       # Styling panel admin
    └── js/
        └── main.js         # JavaScript interaktif
```

---

## 🗄️ Struktur Database

### Tabel `lapangan`
| Field | Tipe | Keterangan |
|-------|------|------------|
| id_lapangan | INTEGER PK | Auto increment |
| nama_lapangan | TEXT | Nama lapangan |
| jenis_olahraga | TEXT | Futsal/Badminton/dst |
| lokasi | TEXT | Lokasi lapangan |
| harga_per_jam | REAL | Harga sewa per jam |
| status | TEXT | aktif/nonaktif |
| deskripsi | TEXT | Deskripsi lapangan |
| fasilitas | TEXT | Fasilitas tersedia |

### Tabel `reservasi`
| Field | Tipe | Keterangan |
|-------|------|------------|
| id_reservasi | INTEGER PK | Auto increment |
| nama_pemesan | TEXT | Nama pemesan |
| no_hp | TEXT | Nomor HP |
| id_lapangan | INTEGER FK | Referensi lapangan |
| tanggal | TEXT | Tanggal reservasi (YYYY-MM-DD) |
| jam_mulai | TEXT | Jam mulai (HH:MM) |
| jam_selesai | TEXT | Jam selesai (HH:MM) |
| status | TEXT | menunggu/dikonfirmasi/dibatalkan/selesai |
| kode_booking | TEXT UNIQUE | Kode unik reservasi |
| total_harga | REAL | Total biaya (0 = gratis) |
| catatan | TEXT | Catatan opsional dari pemesan |

---

## 👨‍💻 Dibuat oleh

**Nama:** [Nama Mahasiswa]  
**NIM:** [NIM]  
**Mata Kuliah:** Pengantar Pemrograman  
**Dosen:** Pak Bayu  
**Tahun:** 2024
