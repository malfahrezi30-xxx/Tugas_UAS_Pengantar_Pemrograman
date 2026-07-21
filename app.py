from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from database import init_db, get_db
import hashlib
import os
from datetime import datetime, date
import qrcode
import io
import base64
import json

app = Flask(__name__)
app.secret_key = 'sportreserve_secret_key_2024'

# ─── INIT DATABASE ───────────────────────────────────────────────────────────
@app.before_request
def setup():
    init_db()

# ─── HELPER ──────────────────────────────────────────────────────────────────
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'admin_logged_in' not in session:
            flash('Silakan login terlebih dahulu.', 'warning')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated

def generate_qr(data):
    qr = qrcode.QRCode(version=1, box_size=6, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return base64.b64encode(buf.getvalue()).decode('utf-8')

# ═══════════════════════════════════════════════════════════════════════════════
#  USER ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/')
def index():
    db = get_db()
    lapangan = db.execute(
        "SELECT * FROM lapangan WHERE status='aktif' ORDER BY jenis_olahraga"
    ).fetchall()
    stats = {
        'total_lapangan': db.execute("SELECT COUNT(*) FROM lapangan").fetchone()[0],
        'total_reservasi': db.execute("SELECT COUNT(*) FROM reservasi").fetchone()[0],
        'reservasi_hari_ini': db.execute(
            "SELECT COUNT(*) FROM reservasi WHERE tanggal=?", (date.today().isoformat(),)
        ).fetchone()[0],
    }
    return render_template('index.html', lapangan=lapangan, stats=stats)


@app.route('/lapangan')
def daftar_lapangan():
    db = get_db()
    jenis_filter = request.args.get('jenis', '')
    if jenis_filter:
        lapangan = db.execute(
            "SELECT * FROM lapangan WHERE status='aktif' AND jenis_olahraga=? ORDER BY nama_lapangan",
            (jenis_filter,)
        ).fetchall()
    else:
        lapangan = db.execute(
            "SELECT * FROM lapangan WHERE status='aktif' ORDER BY jenis_olahraga, nama_lapangan"
        ).fetchall()
    jenis_list = ['Futsal', 'Badminton', 'Basket', 'Voli', 'Tenis', 'Renang']
    return render_template('daftar_lapangan.html', lapangan=lapangan,
                           jenis_list=jenis_list, jenis_filter=jenis_filter)


@app.route('/lapangan/<int:id>')
def detail_lapangan(id):
    db = get_db()
    lapangan = db.execute("SELECT * FROM lapangan WHERE id_lapangan=?", (id,)).fetchone()
    if not lapangan:
        flash('Lapangan tidak ditemukan.', 'danger')
        return redirect(url_for('daftar_lapangan'))

    # Jadwal reservasi 7 hari ke depan
    from datetime import timedelta
    jadwal = {}
    for i in range(7):
        tgl = (date.today() + timedelta(days=i)).isoformat()
        reservasi_tgl = db.execute(
            "SELECT jam_mulai, jam_selesai, status FROM reservasi "
            "WHERE id_lapangan=? AND tanggal=? AND status IN ('menunggu','dikonfirmasi')",
            (id, tgl)
        ).fetchall()
        jadwal[tgl] = [dict(r) for r in reservasi_tgl]

    return render_template('detail_lapangan.html', lapangan=lapangan, jadwal=json.dumps(jadwal))


@app.route('/reservasi', methods=['GET', 'POST'])
def form_reservasi():
    db = get_db()
    lapangan_list = db.execute("SELECT * FROM lapangan WHERE status='aktif'").fetchall()
    lapangan_id = request.args.get('lapangan_id', '')

    if request.method == 'POST':
        nama = request.form.get('nama_pemesan', '').strip()
        no_hp = request.form.get('no_hp', '').strip()
        id_lapangan = request.form.get('id_lapangan', '')
        tanggal = request.form.get('tanggal', '')
        jam_mulai = request.form.get('jam_mulai', '')
        jam_selesai = request.form.get('jam_selesai', '')

        # Validasi input
        errors = []
        if not nama:
            errors.append('Nama pemesan wajib diisi.')
        if not no_hp or len(no_hp) < 10:
            errors.append('Nomor HP tidak valid.')
        if not id_lapangan:
            errors.append('Lapangan wajib dipilih.')
        if not tanggal:
            errors.append('Tanggal wajib diisi.')
        if tanggal < date.today().isoformat():
            errors.append('Tanggal tidak boleh di masa lalu.')
        if not jam_mulai or not jam_selesai:
            errors.append('Jam mulai dan selesai wajib diisi.')
        if jam_mulai >= jam_selesai:
            errors.append('Jam selesai harus lebih dari jam mulai.')

        if not errors:
            # Cek bentrok jadwal
            bentrok = db.execute(
                """SELECT id_reservasi FROM reservasi
                   WHERE id_lapangan=? AND tanggal=? AND status IN ('menunggu','dikonfirmasi')
                   AND NOT (jam_selesai <= ? OR jam_mulai >= ?)""",
                (id_lapangan, tanggal, jam_mulai, jam_selesai)
            ).fetchone()

            if bentrok:
                flash('❌ Jadwal bentrok! Lapangan sudah dipesan pada waktu tersebut.', 'danger')
            else:
                # Hitung durasi dan harga
                lapangan = db.execute(
                    "SELECT * FROM lapangan WHERE id_lapangan=?", (id_lapangan,)
                ).fetchone()
                h_mulai = int(jam_mulai.replace(':', ''))
                h_selesai = int(jam_selesai.replace(':', ''))
                durasi = (h_selesai - h_mulai) / 100
                total_harga = durasi * lapangan['harga_per_jam']

                # Buat kode booking unik
                kode_booking = f"RSV{datetime.now().strftime('%Y%m%d%H%M%S')}"

                db.execute(
                    """INSERT INTO reservasi
                       (nama_pemesan, no_hp, id_lapangan, tanggal, jam_mulai, jam_selesai,
                        status, kode_booking, total_harga)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    (nama, no_hp, id_lapangan, tanggal, jam_mulai, jam_selesai,
                     'menunggu', kode_booking, total_harga)
                )
                db.commit()
                flash(f'✅ Reservasi berhasil! Kode booking Anda: {kode_booking}', 'success')
                return redirect(url_for('status_reservasi', kode=kode_booking))

        for err in errors:
            flash(err, 'danger')

    return render_template('form_reservasi.html', lapangan_list=lapangan_list,
                           lapangan_id=lapangan_id, today=date.today().isoformat())


@app.route('/status')
def cek_status():
    return render_template('cek_status.html')


@app.route('/status/<kode>')
def status_reservasi(kode):
    db = get_db()
    reservasi = db.execute(
        """SELECT r.*, l.nama_lapangan, l.jenis_olahraga, l.lokasi, l.harga_per_jam
           FROM reservasi r JOIN lapangan l ON r.id_lapangan=l.id_lapangan
           WHERE r.kode_booking=?""",
        (kode,)
    ).fetchone()
    if not reservasi:
        flash('Kode booking tidak ditemukan.', 'danger')
        return redirect(url_for('cek_status'))

    qr_data = generate_qr(f"Kode: {kode}\nNama: {reservasi['nama_pemesan']}\n"
                          f"Lapangan: {reservasi['nama_lapangan']}\n"
                          f"Tanggal: {reservasi['tanggal']}\n"
                          f"Jam: {reservasi['jam_mulai']}-{reservasi['jam_selesai']}")
    return render_template('status_reservasi.html', reservasi=reservasi, qr_data=qr_data)


@app.route('/cek-status', methods=['POST'])
def cek_status_post():
    kode = request.form.get('kode_booking', '').strip()
    if not kode:
        flash('Kode booking wajib diisi.', 'danger')
        return redirect(url_for('cek_status'))
    return redirect(url_for('status_reservasi', kode=kode))


# ═══════════════════════════════════════════════════════════════════════════════
#  ADMIN ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if 'admin_logged_in' in session:
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username=? AND role='admin'", (username,)
        ).fetchone()

        if user and user['password'] == hash_password(password):
            session['admin_logged_in'] = True
            session['admin_name'] = user['nama']
            session['admin_username'] = username
            flash(f'Selamat datang, {user["nama"]}!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Username atau password salah.', 'danger')

    return render_template('admin/login.html')


@app.route('/admin/logout')
def admin_logout():
    session.clear()
    flash('Berhasil logout.', 'info')
    return redirect(url_for('admin_login'))


@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    db = get_db()
    today = date.today().isoformat()

    stats = {
        'total_lapangan': db.execute("SELECT COUNT(*) FROM lapangan").fetchone()[0],
        'total_reservasi': db.execute("SELECT COUNT(*) FROM reservasi").fetchone()[0],
        'reservasi_hari_ini': db.execute(
            "SELECT COUNT(*) FROM reservasi WHERE tanggal=?", (today,)
        ).fetchone()[0],
        'reservasi_menunggu': db.execute(
            "SELECT COUNT(*) FROM reservasi WHERE status='menunggu'"
        ).fetchone()[0],
        'reservasi_dikonfirmasi': db.execute(
            "SELECT COUNT(*) FROM reservasi WHERE status='dikonfirmasi'"
        ).fetchone()[0],
        'reservasi_dibatalkan': db.execute(
            "SELECT COUNT(*) FROM reservasi WHERE status='dibatalkan'"
        ).fetchone()[0],
        'pendapatan_bulan_ini': db.execute(
            """SELECT COALESCE(SUM(total_harga),0) FROM reservasi
               WHERE status='dikonfirmasi'
               AND strftime('%Y-%m', tanggal)=strftime('%Y-%m','now')"""
        ).fetchone()[0],
    }

    # Lapangan paling sering digunakan
    top_lapangan = db.execute(
        """SELECT l.nama_lapangan, l.jenis_olahraga, COUNT(r.id_reservasi) as total
           FROM lapangan l LEFT JOIN reservasi r ON l.id_lapangan=r.id_lapangan
           GROUP BY l.id_lapangan ORDER BY total DESC LIMIT 5"""
    ).fetchall()

    # Reservasi 6 bulan terakhir (untuk grafik)
    monthly_data = db.execute(
        """SELECT strftime('%Y-%m', tanggal) as bulan, COUNT(*) as total
           FROM reservasi
           WHERE tanggal >= date('now', '-6 months')
           GROUP BY bulan ORDER BY bulan"""
    ).fetchall()

    # Reservasi terbaru
    recent_reservasi = db.execute(
        """SELECT r.*, l.nama_lapangan FROM reservasi r
           JOIN lapangan l ON r.id_lapangan=l.id_lapangan
           ORDER BY r.id_reservasi DESC LIMIT 8"""
    ).fetchall()

    # Distribusi per jenis olahraga
    jenis_data = db.execute(
        """SELECT l.jenis_olahraga, COUNT(r.id_reservasi) as total
           FROM lapangan l LEFT JOIN reservasi r ON l.id_lapangan=r.id_lapangan
           WHERE r.status IN ('menunggu','dikonfirmasi')
           GROUP BY l.jenis_olahraga ORDER BY total DESC"""
    ).fetchall()

    return render_template('admin/dashboard.html',
                           stats=stats,
                           top_lapangan=top_lapangan,
                           monthly_data=json.dumps([dict(r) for r in monthly_data]),
                           recent_reservasi=recent_reservasi,
                           jenis_data=json.dumps([dict(r) for r in jenis_data]))


# ─── LAPANGAN CRUD ───────────────────────────────────────────────────────────

@app.route('/admin/lapangan')
@login_required
def admin_lapangan():
    db = get_db()
    search = request.args.get('search', '')
    jenis = request.args.get('jenis', '')
    query = "SELECT * FROM lapangan WHERE 1=1"
    params = []
    if search:
        query += " AND (nama_lapangan LIKE ? OR lokasi LIKE ?)"
        params += [f'%{search}%', f'%{search}%']
    if jenis:
        query += " AND jenis_olahraga=?"
        params.append(jenis)
    query += " ORDER BY jenis_olahraga, nama_lapangan"
    lapangan = db.execute(query, params).fetchall()
    jenis_list = ['Futsal', 'Badminton', 'Basket', 'Voli', 'Tenis', 'Renang']
    return render_template('admin/lapangan.html', lapangan=lapangan,
                           jenis_list=jenis_list, search=search, jenis_filter=jenis)


@app.route('/admin/lapangan/tambah', methods=['GET', 'POST'])
@login_required
def admin_tambah_lapangan():
    jenis_list = ['Futsal', 'Badminton', 'Basket', 'Voli', 'Tenis', 'Renang']
    if request.method == 'POST':
        nama = request.form.get('nama_lapangan', '').strip()
        jenis = request.form.get('jenis_olahraga', '')
        lokasi = request.form.get('lokasi', '').strip()
        harga = request.form.get('harga_per_jam', '0')
        status = request.form.get('status', 'aktif')
        deskripsi = request.form.get('deskripsi', '').strip()
        fasilitas = request.form.get('fasilitas', '').strip()

        errors = []
        if not nama:
            errors.append('Nama lapangan wajib diisi.')
        if not jenis:
            errors.append('Jenis olahraga wajib dipilih.')
        if not lokasi:
            errors.append('Lokasi wajib diisi.')
        try:
            harga = float(harga)
            if harga <= 0:
                errors.append('Harga harus lebih dari 0.')
        except:
            errors.append('Harga tidak valid.')

        if not errors:
            db = get_db()
            db.execute(
                """INSERT INTO lapangan (nama_lapangan, jenis_olahraga, lokasi, harga_per_jam,
                   status, deskripsi, fasilitas) VALUES (?,?,?,?,?,?,?)""",
                (nama, jenis, lokasi, harga, status, deskripsi, fasilitas)
            )
            db.commit()
            flash('✅ Lapangan berhasil ditambahkan!', 'success')
            return redirect(url_for('admin_lapangan'))

        for err in errors:
            flash(err, 'danger')

    return render_template('admin/form_lapangan.html', lapangan=None, jenis_list=jenis_list, mode='tambah')


@app.route('/admin/lapangan/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def admin_edit_lapangan(id):
    db = get_db()
    lapangan = db.execute("SELECT * FROM lapangan WHERE id_lapangan=?", (id,)).fetchone()
    if not lapangan:
        flash('Lapangan tidak ditemukan.', 'danger')
        return redirect(url_for('admin_lapangan'))

    jenis_list = ['Futsal', 'Badminton', 'Basket', 'Voli', 'Tenis', 'Renang']
    if request.method == 'POST':
        nama = request.form.get('nama_lapangan', '').strip()
        jenis = request.form.get('jenis_olahraga', '')
        lokasi = request.form.get('lokasi', '').strip()
        harga = request.form.get('harga_per_jam', '0')
        status = request.form.get('status', 'aktif')
        deskripsi = request.form.get('deskripsi', '').strip()
        fasilitas = request.form.get('fasilitas', '').strip()

        errors = []
        if not nama: errors.append('Nama lapangan wajib diisi.')
        if not jenis: errors.append('Jenis olahraga wajib dipilih.')
        if not lokasi: errors.append('Lokasi wajib diisi.')
        try:
            harga = float(harga)
            if harga <= 0: errors.append('Harga harus lebih dari 0.')
        except:
            errors.append('Harga tidak valid.')

        if not errors:
            db.execute(
                """UPDATE lapangan SET nama_lapangan=?, jenis_olahraga=?, lokasi=?,
                   harga_per_jam=?, status=?, deskripsi=?, fasilitas=?
                   WHERE id_lapangan=?""",
                (nama, jenis, lokasi, harga, status, deskripsi, fasilitas, id)
            )
            db.commit()
            flash('✅ Lapangan berhasil diperbarui!', 'success')
            return redirect(url_for('admin_lapangan'))

        for err in errors:
            flash(err, 'danger')

    return render_template('admin/form_lapangan.html', lapangan=lapangan,
                           jenis_list=jenis_list, mode='edit')


@app.route('/admin/lapangan/hapus/<int:id>', methods=['POST'])
@login_required
def admin_hapus_lapangan(id):
    db = get_db()
    # Cek apakah ada reservasi aktif
    aktif = db.execute(
        "SELECT COUNT(*) FROM reservasi WHERE id_lapangan=? AND status IN ('menunggu','dikonfirmasi')",
        (id,)
    ).fetchone()[0]
    if aktif > 0:
        flash('❌ Lapangan tidak dapat dihapus karena masih ada reservasi aktif.', 'danger')
    else:
        db.execute("DELETE FROM lapangan WHERE id_lapangan=?", (id,))
        db.commit()
        flash('✅ Lapangan berhasil dihapus.', 'success')
    return redirect(url_for('admin_lapangan'))


# ─── RESERVASI CRUD ──────────────────────────────────────────────────────────

@app.route('/admin/reservasi')
@login_required
def admin_reservasi():
    db = get_db()
    status_filter = request.args.get('status', '')
    tanggal_filter = request.args.get('tanggal', '')
    search = request.args.get('search', '')

    query = """SELECT r.*, l.nama_lapangan, l.jenis_olahraga
               FROM reservasi r JOIN lapangan l ON r.id_lapangan=l.id_lapangan
               WHERE 1=1"""
    params = []

    if status_filter:
        query += " AND r.status=?"
        params.append(status_filter)
    if tanggal_filter:
        query += " AND r.tanggal=?"
        params.append(tanggal_filter)
    if search:
        query += " AND (r.nama_pemesan LIKE ? OR r.kode_booking LIKE ? OR r.no_hp LIKE ?)"
        params += [f'%{search}%', f'%{search}%', f'%{search}%']

    query += " ORDER BY r.tanggal DESC, r.jam_mulai DESC"
    reservasi = db.execute(query, params).fetchall()
    lapangan_list = db.execute("SELECT * FROM lapangan WHERE status='aktif'").fetchall()

    return render_template('admin/reservasi.html', reservasi=reservasi,
                           lapangan_list=lapangan_list,
                           status_filter=status_filter,
                           tanggal_filter=tanggal_filter, search=search)


@app.route('/admin/reservasi/tambah', methods=['GET', 'POST'])
@login_required
def admin_tambah_reservasi():
    db = get_db()
    lapangan_list = db.execute("SELECT * FROM lapangan WHERE status='aktif'").fetchall()

    if request.method == 'POST':
        nama = request.form.get('nama_pemesan', '').strip()
        no_hp = request.form.get('no_hp', '').strip()
        id_lapangan = request.form.get('id_lapangan', '')
        tanggal = request.form.get('tanggal', '')
        jam_mulai = request.form.get('jam_mulai', '')
        jam_selesai = request.form.get('jam_selesai', '')
        status = request.form.get('status', 'menunggu')

        errors = []
        if not nama: errors.append('Nama pemesan wajib diisi.')
        if not no_hp or len(no_hp) < 10: errors.append('Nomor HP tidak valid.')
        if not id_lapangan: errors.append('Lapangan wajib dipilih.')
        if not tanggal: errors.append('Tanggal wajib diisi.')
        if not jam_mulai or not jam_selesai: errors.append('Jam mulai dan selesai wajib diisi.')
        if jam_mulai >= jam_selesai: errors.append('Jam selesai harus lebih dari jam mulai.')

        if not errors:
            bentrok = db.execute(
                """SELECT id_reservasi FROM reservasi
                   WHERE id_lapangan=? AND tanggal=? AND status IN ('menunggu','dikonfirmasi')
                   AND NOT (jam_selesai <= ? OR jam_mulai >= ?)""",
                (id_lapangan, tanggal, jam_mulai, jam_selesai)
            ).fetchone()
            if bentrok:
                flash('❌ Jadwal bentrok dengan reservasi yang sudah ada!', 'danger')
            else:
                lapangan = db.execute("SELECT * FROM lapangan WHERE id_lapangan=?", (id_lapangan,)).fetchone()
                h_mulai = int(jam_mulai.replace(':', ''))
                h_selesai = int(jam_selesai.replace(':', ''))
                durasi = (h_selesai - h_mulai) / 100
                total_harga = durasi * lapangan['harga_per_jam']
                kode_booking = f"RSV{datetime.now().strftime('%Y%m%d%H%M%S')}"
                db.execute(
                    """INSERT INTO reservasi (nama_pemesan, no_hp, id_lapangan, tanggal,
                       jam_mulai, jam_selesai, status, kode_booking, total_harga)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    (nama, no_hp, id_lapangan, tanggal, jam_mulai, jam_selesai,
                     status, kode_booking, total_harga)
                )
                db.commit()
                flash('✅ Reservasi berhasil ditambahkan!', 'success')
                return redirect(url_for('admin_reservasi'))

        for err in errors:
            flash(err, 'danger')

    return render_template('admin/form_reservasi.html', reservasi=None,
                           lapangan_list=lapangan_list, mode='tambah',
                           today=date.today().isoformat())


@app.route('/admin/reservasi/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def admin_edit_reservasi(id):
    db = get_db()
    reservasi = db.execute("SELECT * FROM reservasi WHERE id_reservasi=?", (id,)).fetchone()
    if not reservasi:
        flash('Reservasi tidak ditemukan.', 'danger')
        return redirect(url_for('admin_reservasi'))

    lapangan_list = db.execute("SELECT * FROM lapangan WHERE status='aktif'").fetchall()

    if request.method == 'POST':
        nama = request.form.get('nama_pemesan', '').strip()
        no_hp = request.form.get('no_hp', '').strip()
        id_lapangan = request.form.get('id_lapangan', '')
        tanggal = request.form.get('tanggal', '')
        jam_mulai = request.form.get('jam_mulai', '')
        jam_selesai = request.form.get('jam_selesai', '')
        status = request.form.get('status', 'menunggu')

        if not all([nama, no_hp, id_lapangan, tanggal, jam_mulai, jam_selesai]):
            flash('Semua field wajib diisi.', 'danger')
        elif jam_mulai >= jam_selesai:
            flash('Jam selesai harus lebih dari jam mulai.', 'danger')
        else:
            bentrok = db.execute(
                """SELECT id_reservasi FROM reservasi
                   WHERE id_lapangan=? AND tanggal=? AND status IN ('menunggu','dikonfirmasi')
                   AND id_reservasi != ?
                   AND NOT (jam_selesai <= ? OR jam_mulai >= ?)""",
                (id_lapangan, tanggal, id, jam_mulai, jam_selesai)
            ).fetchone()
            if bentrok:
                flash('❌ Jadwal bentrok dengan reservasi lain!', 'danger')
            else:
                lapangan = db.execute("SELECT * FROM lapangan WHERE id_lapangan=?", (id_lapangan,)).fetchone()
                h_mulai = int(jam_mulai.replace(':', ''))
                h_selesai = int(jam_selesai.replace(':', ''))
                durasi = (h_selesai - h_mulai) / 100
                total_harga = durasi * lapangan['harga_per_jam']
                db.execute(
                    """UPDATE reservasi SET nama_pemesan=?, no_hp=?, id_lapangan=?, tanggal=?,
                       jam_mulai=?, jam_selesai=?, status=?, total_harga=? WHERE id_reservasi=?""",
                    (nama, no_hp, id_lapangan, tanggal, jam_mulai, jam_selesai, status, total_harga, id)
                )
                db.commit()
                flash('✅ Reservasi berhasil diperbarui!', 'success')
                return redirect(url_for('admin_reservasi'))

    return render_template('admin/form_reservasi.html', reservasi=reservasi,
                           lapangan_list=lapangan_list, mode='edit',
                           today=date.today().isoformat())


@app.route('/admin/reservasi/status/<int:id>/<action>', methods=['POST'])
@login_required
def admin_update_status(id, action):
    db = get_db()
    status_map = {
        'konfirmasi': 'dikonfirmasi',
        'batalkan': 'dibatalkan',
        'selesai': 'selesai'
    }
    if action not in status_map:
        flash('Aksi tidak valid.', 'danger')
        return redirect(url_for('admin_reservasi'))

    db.execute("UPDATE reservasi SET status=? WHERE id_reservasi=?", (status_map[action], id))
    db.commit()
    label = {'konfirmasi': 'dikonfirmasi', 'batalkan': 'dibatalkan', 'selesai': 'diselesaikan'}
    flash(f'✅ Reservasi berhasil {label[action]}.', 'success')
    return redirect(url_for('admin_reservasi'))


@app.route('/admin/reservasi/hapus/<int:id>', methods=['POST'])
@login_required
def admin_hapus_reservasi(id):
    db = get_db()
    db.execute("DELETE FROM reservasi WHERE id_reservasi=?", (id,))
    db.commit()
    flash('✅ Reservasi berhasil dihapus.', 'success')
    return redirect(url_for('admin_reservasi'))


@app.route('/admin/reservasi/detail/<int:id>')
@login_required
def admin_detail_reservasi(id):
    db = get_db()
    reservasi = db.execute(
        """SELECT r.*, l.nama_lapangan, l.jenis_olahraga, l.lokasi
           FROM reservasi r JOIN lapangan l ON r.id_lapangan=l.id_lapangan
           WHERE r.id_reservasi=?""", (id,)
    ).fetchone()
    if not reservasi:
        flash('Reservasi tidak ditemukan.', 'danger')
        return redirect(url_for('admin_reservasi'))
    qr_data = generate_qr(
        f"Kode: {reservasi['kode_booking']}\nNama: {reservasi['nama_pemesan']}\n"
        f"Lapangan: {reservasi['nama_lapangan']}\nTanggal: {reservasi['tanggal']}\n"
        f"Jam: {reservasi['jam_mulai']}-{reservasi['jam_selesai']}"
    )
    return render_template('admin/detail_reservasi.html', reservasi=reservasi, qr_data=qr_data)


# ─── LAPORAN ─────────────────────────────────────────────────────────────────

@app.route('/admin/laporan')
@login_required
def admin_laporan():
    db = get_db()
    bulan = request.args.get('bulan', datetime.now().strftime('%Y-%m'))

    laporan_bulan = db.execute(
        """SELECT r.*, l.nama_lapangan, l.jenis_olahraga
           FROM reservasi r JOIN lapangan l ON r.id_lapangan=l.id_lapangan
           WHERE strftime('%Y-%m', r.tanggal)=?
           ORDER BY r.tanggal, r.jam_mulai""",
        (bulan,)
    ).fetchall()

    ringkasan = {
        'total': len(laporan_bulan),
        'dikonfirmasi': sum(1 for r in laporan_bulan if r['status'] == 'dikonfirmasi'),
        'menunggu': sum(1 for r in laporan_bulan if r['status'] == 'menunggu'),
        'dibatalkan': sum(1 for r in laporan_bulan if r['status'] == 'dibatalkan'),
        'selesai': sum(1 for r in laporan_bulan if r['status'] == 'selesai'),
        'pendapatan': sum(r['total_harga'] for r in laporan_bulan if r['status'] in ('dikonfirmasi', 'selesai')),
    }

    per_lapangan = db.execute(
        """SELECT l.nama_lapangan, l.jenis_olahraga, COUNT(r.id_reservasi) as total,
           COALESCE(SUM(CASE WHEN r.status IN ('dikonfirmasi','selesai') THEN r.total_harga ELSE 0 END),0) as pendapatan
           FROM lapangan l LEFT JOIN reservasi r ON l.id_lapangan=r.id_lapangan
           AND strftime('%Y-%m', r.tanggal)=?
           GROUP BY l.id_lapangan ORDER BY total DESC""",
        (bulan,)
    ).fetchall()

    per_hari = db.execute(
        """SELECT tanggal, COUNT(*) as total,
           SUM(CASE WHEN status IN ('dikonfirmasi','selesai') THEN total_harga ELSE 0 END) as pendapatan
           FROM reservasi WHERE strftime('%Y-%m', tanggal)=?
           GROUP BY tanggal ORDER BY tanggal""",
        (bulan,)
    ).fetchall()

    return render_template('admin/laporan.html',
                           laporan_bulan=laporan_bulan,
                           ringkasan=ringkasan,
                           per_lapangan=per_lapangan,
                           per_hari=json.dumps([dict(r) for r in per_hari]),
                           bulan=bulan)


# ─── API ──────────────────────────────────────────────────────────────────────

@app.route('/api/cek-jadwal')
def api_cek_jadwal():
    """API untuk cek ketersediaan jadwal"""
    id_lapangan = request.args.get('id_lapangan')
    tanggal = request.args.get('tanggal')
    if not id_lapangan or not tanggal:
        return jsonify({'error': 'Parameter tidak lengkap'}), 400

    db = get_db()
    reservasi = db.execute(
        """SELECT jam_mulai, jam_selesai, status FROM reservasi
           WHERE id_lapangan=? AND tanggal=? AND status IN ('menunggu','dikonfirmasi')
           ORDER BY jam_mulai""",
        (id_lapangan, tanggal)
    ).fetchall()
    return jsonify([dict(r) for r in reservasi])


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
