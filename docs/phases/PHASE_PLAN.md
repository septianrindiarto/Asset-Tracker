# Gold Tracker — Rencana Fase (v1.2)

Satu fase = satu paket kerja yang bisa diuji. Fase berikutnya dimulai **setelah gate fase sebelumnya lulus**, supaya kesalahan fondasi tidak terbawa ke fitur.

| Fase | Nama | Status | Gate (syarat lanjut) |
|---|---|---|---|
| 0 | Desain | ✅ Selesai | Master doc + mockup v2 disetujui |
| 1 | PoC Rp0 | 🟡 Kode siap, menunggu langkah manual | T-01, 02, 03, 05, 06, 11, 14, 15 lulus + probe Antam |
| 1.1 | Penyesuaian parser | ⏳ Bila diperlukan | Harga Antam jual & buyback masuk otomatis |
| 2 | Core MVP (aplikasi utama) | ⏳ | T-04, 07, 08, 13 + UAT singkat |
| 3 | Analisis & rekomendasi | ⏳ | T-09, 10 + backtest dibandingkan DCA |
| 4 | Berita & notifikasi | ⏳ | T-12 + digest/alert per user berjalan 3 hari |
| 5 | Hardening & rilis | ⏳ | Semua tes PASS + recovery drill + UAT 3–5 user |

Pola tiap sesi kerja: **Claude membuat kode + tes + panduan → disimpan ke `D:\Project\Gold Tracker` → Anda menjalankan langkah manual & checklist → lapor yang gagal saja.**

---

## Fase 1 — PoC Rp0 *(kode siap)*

**Sudah dibuat:**
- `supabase/migrations/0001_init.sql`: tabel inti, `has_access()`/`is_admin()`, RLS, profil otomatis saat diundang, data awal. Diuji pada Postgres 16 dengan tiruan Supabase: user aktif/expired/anon/admin berperilaku benar, dan upsert tidak menghasilkan duplikat.
- `jobs/`: job harga (XAU/USD, USD/IDR, spot/gram, Antam), cek kualitas, idempotent, laporan Telegram, mode `--dry-run` & `--simulate-fail`. **18 tes otomatis lulus.**
- `worker/`: pemicu cron → GitHub, watchdog jadwal terlewat, endpoint uji manual. Tes logika lulus.
- `web/`: PoC login magic-link undangan, status akses, harga, log job admin.
- `.github/workflows/`: `prices` (+ jadwal cadangan), `ci` (tes tiap push), `probe` (cek situs sumber).

**Langkah manual Anda:** `PHASE1_GUIDE.md` (A–K).

---

## Fase 2 — Core MVP: aplikasi utama dari mockup

**Yang saya buat:**
1. **Web app React + Vite** sesuai mockup v2: semua halaman, mode bahasa sederhana, mode privasi, responsif.
2. **Migration 0002**:
   - `transactions` (ledger per user), `goals`, `user_prefs`
   - `metric_explanations`: template penjelasan sederhana yang diisi nilai terkini, sehingga teksnya dinamis dan bisa diedit admin tanpa mengubah kode
   - view `holdings_v` & fungsi valuasi semua jenis emas (`pricing_method`: scrape/manual/formula)
   - harga manual oleh admin, dan RLS `owner_id = auth.uid()` untuk data pribadi (admin tidak bisa membaca portofolio orang lain)
3. **Halaman Pengaturan** tersambung ke `app_config` & `user_prefs`.
4. **Admin Akses**: undang/ubah role/masa akses/suspend dari UI, lewat endpoint Worker `/admin/*` yang memverifikasi token admin. Secret key tetap di server.
5. Job `portfolio` harian: snapshot nilai per user untuk grafik pertumbuhan.
6. Ekspor CSV + backup mingguan otomatis (GitHub Actions → artifact).

**Langkah manual Anda (perkiraan):** jalankan SQL 0002 · ubah Build settings Cloudflare Pages (build command `npm run build`, output `web/dist`) · tambah 2 secret Worker · uji UAT dengan 1 akun user & 1 viewer.

**Tes:** T-04 (user A ≠ user B), T-07 (valuasi 3 kasus termasuk perhiasan), T-08 (konversi), T-13 (ekspor & restore).

---

## Fase 3 — Analisis & rekomendasi

**Yang saya buat:**
1. Backfill riwayat harga 10 tahun (yfinance) → tabel `price_daily`.
2. Job `analysis` (pandas): MA, RSI, volatilitas, DXY, spread → skor faktor → sinyal fisik & spot, beserta alasan, *invalidation*, dan `rule_version`. Semua parameter dibaca dari `app_config` (bobot, ambang, batas skor), sesuai yang diatur di halaman Pengaturan.
3. Backtest tanpa look-ahead, dibandingkan dengan DCA & buy-and-hold, termasuk spread. Hasilnya disimpan & ditampilkan; label *Eksperimental* otomatis bila tidak lebih baik dari DCA.
4. Proyeksi Monte Carlo (P10/P50/P90) dari volatilitas historis.
5. Penjelasan sederhana dinamis untuk setiap faktor (template + angka terkini).

**Langkah manual Anda:** hampir tidak ada (jalankan workflow backfill sekali).
**Tes:** T-09 (sinyal bisa dihitung ulang), T-10 (tanpa look-ahead).

---

## Fase 4 — Berita & notifikasi

**Yang saya buat:**
1. Job `news` (06:30 & 18:30 WIB): RSS Google News (ID/EN), media ekonomi, World Gold Council, keterbukaan IDX → dedupe → klasifikasi kata kunci → ringkasan & dampak.
2. **AI opsional** (Gemini/Groq free tier) dengan timeout. Jika gagal atau kuota habis, otomatis kembali ke aturan kata kunci.
3. Data perusahaan emas (ANTM, MDKA, BRMS, HRTA, NEM, B) mingguan.
4. Bot Telegram dua arah: `/start KODE` untuk menghubungkan akun (webhook di Worker), digest per user sesuai jam pilihan, alert harga ±X%, alert perubahan sinyal, dengan dedupe & retry.

**Langkah manual Anda:** buat API key AI gratis (opsional, panduan disediakan) · daftarkan webhook bot (1 perintah) · 1 secret baru.
**Tes:** T-12 (dedupe/retry), digest 3 hari berturut-turut.

---

## Fase 5 — Hardening & rilis

**Yang saya buat:** uji keamanan (akses langsung API, privilege escalation), recovery drill (restore dari backup), audit log, halaman status job, SMTP gratis untuk email login (opsional), dokumentasi pemakaian untuk user.

**Langkah manual Anda:** UAT bersama 3–5 calon user (checklist disediakan), keputusan domain (tetap `pages.dev` atau domain sendiri).

---

## Keputusan default (open questions yang belum dijawab)

Dipakai sampai Anda mengubahnya.

| Pertanyaan | Default yang saya pakai |
|---|---|
| Merek prioritas sumber otomatis | Antam (scrape). UBS, Galeri24, Pegadaian manual dulu, otomatis menyusul bila sumbernya stabil |
| Acuan perhiasan | Buyback Antam (bisa diubah per user) |
| Ambang stale | Spot 8 jam, merek 24 jam |
| Repo | Privat |
| Domain | `*.pages.dev` |
| Masa akses default user baru | 30 hari (`app_config.default_access_days`, 0 = unlimited) |
