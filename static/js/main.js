// ═══════════════════════════════════════════════════════════
//  SPORTRESERVE — Main JavaScript
// ═══════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', function () {

  // ─── NAVBAR MOBILE TOGGLE ────────────────────────────────
  const navToggle = document.getElementById('navToggle');
  const navMenu   = document.getElementById('navMenu');
  if (navToggle && navMenu) {
    navToggle.addEventListener('click', () => {
      navMenu.classList.toggle('open');
    });
  }

  // ─── AUTO-DISMISS FLASH MESSAGES ─────────────────────────
  const alerts = document.querySelectorAll('.alert');
  alerts.forEach(alert => {
    setTimeout(() => {
      alert.style.transition = 'opacity .4s, transform .4s';
      alert.style.opacity = '0';
      alert.style.transform = 'translateX(120%)';
      setTimeout(() => alert.remove(), 400);
    }, 5000);
  });

  // ─── MODAL CONFIRM ───────────────────────────────────────
  // Attach to any [data-confirm] buttons
  document.querySelectorAll('[data-confirm]').forEach(btn => {
    btn.addEventListener('click', function (e) {
      const msg = this.dataset.confirm || 'Apakah Anda yakin?';
      if (!confirm(msg)) e.preventDefault();
    });
  });

  // ─── JAM FORM VALIDATION ─────────────────────────────────
  const jamMulai   = document.getElementById('jam_mulai');
  const jamSelesai = document.getElementById('jam_selesai');
  if (jamMulai && jamSelesai) {
    jamSelesai.addEventListener('change', validateJam);
    jamMulai.addEventListener('change', validateJam);
  }

  function validateJam() {
    if (!jamMulai.value || !jamSelesai.value) return;
    if (jamMulai.value >= jamSelesai.value) {
      jamSelesai.classList.add('is-invalid');
      showInlineError(jamSelesai, 'Jam selesai harus lebih besar dari jam mulai.');
    } else {
      jamSelesai.classList.remove('is-invalid');
      removeInlineError(jamSelesai);
      checkJadwal();
    }
  }

  // ─── REAL-TIME CONFLICT CHECK ─────────────────────────────
  const idLapangan = document.getElementById('id_lapangan');
  const tanggal    = document.getElementById('tanggal');
  const conflictEl = document.getElementById('conflict-info');

  function checkJadwal() {
    if (!idLapangan || !tanggal || !conflictEl) return;
    if (!idLapangan.value || !tanggal.value) return;

    fetch(`/api/cek-jadwal?id_lapangan=${idLapangan.value}&tanggal=${tanggal.value}`)
      .then(r => r.json())
      .then(data => {
        if (data.length === 0) {
          conflictEl.innerHTML = '<i class="fas fa-check-circle" style="color:var(--success)"></i> Semua jam tersedia pada tanggal ini';
          conflictEl.className = 'form-hint text-success';
        } else {
          const jadwalList = data.map(r =>
            `<span class="badge badge-danger" style="margin:2px">${r.jam_mulai}–${r.jam_selesai}</span>`
          ).join(' ');
          conflictEl.innerHTML = `<i class="fas fa-exclamation-triangle"></i> Sudah dipesan: ${jadwalList}`;
          conflictEl.className = 'form-hint text-danger';
        }
      })
      .catch(() => {
        conflictEl.innerHTML = '';
      });
  }

  if (idLapangan) idLapangan.addEventListener('change', checkJadwal);
  if (tanggal)    tanggal.addEventListener('change', checkJadwal);
  if (jamMulai)   jamMulai.addEventListener('change', checkJadwal);

  // Trigger on load if values exist
  if (idLapangan?.value && tanggal?.value) checkJadwal();

  // ─── HARGA ESTIMASI ───────────────────────────────────────
  updateEstimasi();
  [idLapangan, jamMulai, jamSelesai].forEach(el => {
    if (el) el.addEventListener('change', updateEstimasi);
  });

  function updateEstimasi() {
    const estimasiEl = document.getElementById('estimasi-harga');
    if (!estimasiEl) return;

    const hargaPerJam = parseFloat(idLapangan?.options[idLapangan?.selectedIndex]?.dataset.harga || 0);
    const jm = jamMulai?.value;
    const js = jamSelesai?.value;

    if (!hargaPerJam || !jm || !js || jm >= js) {
      estimasiEl.textContent = '-';
      return;
    }

    const [h1, m1] = jm.split(':').map(Number);
    const [h2, m2] = js.split(':').map(Number);
    const durasi = (h2 * 60 + m2 - h1 * 60 - m1) / 60;
    const total  = durasi * hargaPerJam;
    estimasiEl.textContent = `Rp ${total.toLocaleString('id-ID')} (${durasi} jam)`;
  }

  // ─── INLINE ERROR HELPER ─────────────────────────────────
  function showInlineError(el, msg) {
    removeInlineError(el);
    const err = document.createElement('div');
    err.className = 'form-hint text-danger';
    err.id = el.id + '-err';
    err.innerHTML = `<i class="fas fa-times-circle"></i> ${msg}`;
    el.parentNode.appendChild(err);
  }

  function removeInlineError(el) {
    const existing = document.getElementById(el.id + '-err');
    if (existing) existing.remove();
  }

  // ─── TANGGAL MIN ─────────────────────────────────────────
  if (tanggal) {
    const today = new Date().toISOString().split('T')[0];
    tanggal.min = today;
  }

  // ─── SMOOTH SCROLL ───────────────────────────────────────
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
      const target = document.querySelector(this.getAttribute('href'));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });

  // ─── COUNTER ANIMATION ───────────────────────────────────
  const counters = document.querySelectorAll('[data-count]');
  if (counters.length > 0) {
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          animateCounter(entry.target);
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.5 });
    counters.forEach(c => observer.observe(c));
  }

  function animateCounter(el) {
    const target = parseInt(el.dataset.count);
    const duration = 1500;
    const start = performance.now();
    function update(time) {
      const elapsed = time - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      el.textContent = Math.round(eased * target).toLocaleString('id-ID');
      if (progress < 1) requestAnimationFrame(update);
    }
    requestAnimationFrame(update);
  }

  // ─── SIDEBAR ADMIN TOGGLE ─────────────────────────────── 
  const sidebarToggle = document.getElementById('sidebarToggle');
  const sidebar       = document.querySelector('.sidebar');
  if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener('click', () => {
      sidebar.classList.toggle('open');
    });
    // Close on outside click
    document.addEventListener('click', (e) => {
      if (!sidebar.contains(e.target) && !sidebarToggle.contains(e.target)) {
        sidebar.classList.remove('open');
      }
    });
  }

  // ─── COPY TO CLIPBOARD ───────────────────────────────────
  document.querySelectorAll('[data-copy]').forEach(btn => {
    btn.addEventListener('click', function () {
      const text = this.dataset.copy;
      navigator.clipboard.writeText(text).then(() => {
        const original = this.innerHTML;
        this.innerHTML = '<i class="fas fa-check"></i> Tersalin!';
        this.classList.add('btn-success');
        setTimeout(() => {
          this.innerHTML = original;
          this.classList.remove('btn-success');
        }, 2000);
      });
    });
  });

  // ─── TOOLTIPS (simple title-based) ───────────────────────
  document.querySelectorAll('[title]').forEach(el => {
    el.setAttribute('data-title', el.getAttribute('title'));
  });

});

// ─── FORMAT CURRENCY (global) ────────────────────────────
function formatRupiah(amount) {
  return 'Rp ' + parseInt(amount).toLocaleString('id-ID');
}

// ─── GET SPORT ICON ──────────────────────────────────────
function getSportIcon(jenis) {
  const icons = {
    'Futsal':    '⚽',
    'Badminton': '🏸',
    'Basket':    '🏀',
    'Voli':      '🏐',
    'Tenis':     '🎾',
    'Renang':    '🏊',
  };
  return icons[jenis] || '🏟️';
}
