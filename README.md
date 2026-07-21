# 🏟️ SportReserve — Sistem Informasi Reservasi Lapangan Olahraga

Aplikasi web berbasis **Python + Flask** untuk mengelola reservasi lapangan olahraga secara online.

---

## 📋 Fitur Utama

### 👥 Sisi Pengguna (User)
- Beranda dengan info lapangan & statistik
- Daftar lapangan dengan filter jenis olahraga
- Detail lapangan + kalender ketersediaan 7 hari
- Form reservasi dengan cek bentrok otomatis
- QR Code / kode booking untuk setiap reservasi
- Cek status reservasi via kode booking

### 🔐 Sisi Admin
- Login dengan autentikasi session
- Dashboard dengan statistik & grafik
- CRUD Lapangan (Tambah, Edit, Hapus)
- CRUD Reservasi (Tambah, Edit, Konfirmasi, Batalkan, Hapus)
- Laporan per bulan dengan ringkasan pendapatan
- Detail reservasi + QR Code

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
├── app.py                  # File utama Flask
├── database.py             # Koneksi & inisialisasi database
├── requirements.txt        # Dependensi Python
├── .gitignore
├── README.md
│
├── templates/
│   ├── base.html           # Layout dasar user
│   ├── index.html          # Beranda
│   ├── daftar_lapangan.html
│   ├── detail_lapangan.html
│   ├── form_reservasi.html
│   ├── cek_status.html
│   ├── status_reservasi.html
│   └── admin/
│       ├── base_admin.html
│       ├── login.html
│       ├── dashboard.html
│       ├── lapangan.html
│       ├── form_lapangan.html
│       ├── reservasi.html
│       ├── form_reservasi.html
│       ├── detail_reservasi.html
│       └── laporan.html
│
└── static/
    ├── css/
    │   └── style.css
    └── js/
        └── main.js
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
| tanggal | TEXT | Tanggal reservasi |
| jam_mulai | TEXT | Jam mulai |
| jam_selesai | TEXT | Jam selesai |
| status | TEXT | menunggu/dikonfirmasi/dibatalkan/selesai |
| kode_booking | TEXT UNIQUE | Kode unik reservasi |
| total_harga | REAL | Total biaya |

---

## 👨‍💻 Dibuat oleh

**Nama:** [Nama Mahasiswa]  
**NIM:** [NIM]  
**Mata Kuliah:** Pengantar Pemrograman  
**Dosen:** Pak Bayu  
**Tahun:** 2024
