# GOLD TRACKER — MASTER DOCUMENT v1.1

| Item | Nilai |
|---|---|
| Document ID | GT-DOC-001 |
| Versi | 1.1 — Consolidated Assessment & Solution Design |
| Tanggal | 30 Oktober 2026 |
| Status | DRAFT — siap review, belum ada implementasi |
| Owner | Arhent |
| Lingkup pengguna | Internal (pribadi, keluarga, rekan) — non-komersial |
| Target biaya | Rp0 (dalam batas free tier, diverifikasi per fase) |

**Changelog**

| Versi | Perubahan |
|---|---|
| 1.0 | Assessment awal (AI lain): baseline Cloudflare Workers + D1 + Access |
| 1.2 (31 Okt) | Mockup v2 (layout penuh, penjelasan sederhana dinamis per metrik, semua parameter via halaman Pengaturan, data per user, semua tombol/link berfungsi). Kode Fase 1 dibuat & diuji. Rencana fase: `docs/phases/PHASE_PLAN.md`; panduan manual: `docs/phases/PHASE1_GUIDE.md`. Keputusan baru: D-13 penjelasan metrik = template + nilai terkini (AI opsional); D-14 semua parameter di `app_config`/`user_prefs`, diubah lewat UI; D-15 admin kelola user lewat endpoint Worker (secret key tidak pernah di browser). |
| 1.1 | Konsolidasi. Arsitektur diganti ke **Cloudflare Pages + Supabase + GitHub Actions (Python) + Cloudflare Worker sebagai pemicu/watchdog**. Ditambah: taksonomi semua jenis emas, detail 3 engine, scheduling 3 lapis tanpa ketergantungan AI, design system (palet plum–peach–gold), checklist UX, struktur repo. Prinsip kualitas data, kontrak sinyal, test matrix & risk register dari v1.0 **dipertahankan**. |

---

## 1. Ringkasan Eksekutif

Gold Tracker adalah aplikasi web privat (responsif, mobile-first) untuk:

1. Memantau harga emas dunia & Indonesia (spot, retail, buyback) secara terjadwal.
2. Mengelola aset **semua jenis emas**, konversi, valuasi, dan proyeksi periodik.
3. Memberi rekomendasi beli/tahan/jual yang **transparan, berbasis aturan, dan teruji backtest**.
4. Mengumpulkan berita emas, makro, geopolitik, dan status perusahaan emas global/nasional.
5. Membatasi akses hanya untuk akun undangan dengan masa berlaku (tanggal tertentu s/d unlimited).
6. Mengirim notifikasi Telegram (WhatsApp ditunda — tidak gratis untuk pesan proaktif).

**Prinsip operasional:** semua proses terjadwal berjalan otomatis di infrastruktur cloud gratis. **Claude/AI asisten tidak berada di jalur produksi** — hanya membantu membangun kode. AI generatif di pipeline bersifat opsional dan selalu punya fallback.

---

## 2. Scope

### 2.1 Fitur (dari requirement owner)

| # | Fitur | Prioritas |
|---|---|---|
| F1 | Monitor harga (XAU/USD, USD/IDR, spot IDR/gram, harga jual & buyback per merek) | P0 |
| F2 | Portofolio semua jenis emas: ledger transaksi, valuasi, konversi, P/L, snapshot | P0 |
| F3 | Proyeksi periodik (skenario + simulasi DCA/target) | P0 |
| F4 | Rekomendasi beli/jual dengan justifikasi & backtest | P1 |
| F5 | Berita & company intelligence (global + Indonesia) | P1 |
| F6 | Akses undangan + role + expiry/unlimited | P0 |
| F7 | Scheduler otomatis + watchdog | P0 |
| F8 | Notifikasi Telegram (digest, alert harga, perubahan sinyal, kegagalan job) | P1 |
| F9 | Dashboard interaktif (desain hangat-elegan, audience utama wanita) | P0 |
| F10 | Ekspor CSV & backup | P2 |

### 2.2 Di luar scope awal
- Real-time tick data, trading/eksekusi order otomatis.
- WhatsApp otomatis (dievaluasi setelah MVP).
- Layanan berbayar atau billing aktif dalam bentuk apa pun.
- Jaminan profit / nasihat keuangan definitif.

---

## 3. Keputusan Arsitektur

### 3.1 Stack terpilih

| Layer | Pilihan | Alasan |
|---|---|---|
| Frontend | React + Vite + TypeScript + Tailwind, di **Cloudflare Pages** | Static hosting gratis, cepat, boleh komersial bila kelak dibutuhkan |
| Database + Auth | **Supabase Free** (Postgres + Auth + RLS) | Login, expiry, isolasi data per user dalam satu vendor |
| Pekerja batch | **GitHub Actions + Python** (pandas, requests, bs4) | Kekuatan owner; tidak ada batas CPU 10 ms; mudah di-debug |
| Pemicu & watchdog | **Cloudflare Worker Cron** | Tepat waktu; memicu GitHub `workflow_dispatch`; cek job macet |
| Notifikasi | **Telegram Bot API** | Gratis untuk pesan proaktif |
| AI (opsional) | Gemini / Groq free tier | Ringkasan & sentimen berita; selalu ada fallback rule-based |
| Repo | GitHub (private) | Source of truth kode & docs |

### 3.2 Opsi yang ditolak / ditunda

| Opsi | Status | Alasan |
|---|---|---|
| Semua di Cloudflare Workers + D1 (v1.0) | Ditolak sebagai inti | Free plan: **10 ms CPU per invocation/cron** — tidak cukup untuk indikator, backtest, parsing HTML, Monte Carlo. Stack JS, bukan Python. Dua lapis auth (Access + D1) terlalu rumit. |
| Neon Postgres | Cadangan | Tidak pause, tapi tanpa auth bawaan; kuota 100 CU-jam/bulan. Migrasi mudah (sama-sama Postgres). |
| n8n | Tidak dipakai | Butuh server menyala 24/7; free hosting (Oracle/Render) tidak andal. |
| WhatsApp Cloud API | Ditunda (P2) | Utility template (notifikasi proaktif) selalu berbayar. Library tidak resmi berisiko banned. |
| Streamlit | Hanya untuk prototipe analisis | Kontrol akses & UI terbatas, aplikasi tidur. |

### 3.3 Diagram

```text
                 ┌──────────────────────────┐
  User (HP/PC) ─▶│ Cloudflare Pages (React) │
                 └────────────┬─────────────┘
                              │ supabase-js (JWT user)
                              ▼
                 ┌──────────────────────────┐
                 │ Supabase                 │
                 │  Auth (invite-only)      │
                 │  Postgres + RLS          │◀──── tulis (service key)
                 └──────────────────────────┘           ▲
                                                         │
  ┌───────────────────────┐  workflow_dispatch  ┌────────┴─────────────┐
  │ Cloudflare Worker Cron│────────────────────▶│ GitHub Actions       │
  │  - pemicu jadwal      │                     │  Python jobs:        │
  │  - watchdog job_runs  │                     │  prices, news,       │
  └──────────┬────────────┘                     │  analysis, portfolio,│
             │ alert bila job macet             │  notify              │
             ▼                                  └────────┬─────────────┘
       Telegram Bot ◀───────────────────────────────────┘ digest/alert
                                                  ▲
                         Sumber data: API harga/kurs, halaman harga
                         merek (scraping), RSS berita, yfinance
```

---

## 4. Scheduling 3 Lapis (tanpa ketergantungan AI)

| Lapis | Komponen | Peran |
|---|---|---|
| 1. Pemicu | Cloudflare Worker Cron (UTC) | Memanggil GitHub API `workflow_dispatch`. CPU kecil (hanya fetch), aman di limit 10 ms. Tidak kena delay jadwal GitHub & tidak terdampak auto-disable 60 hari. |
| 2. Pekerja | GitHub Actions (Python) | Menjalankan job. `schedule:` bawaan GitHub tetap dipasang sebagai **cadangan**. |
| 3. Penjaga | Tabel `job_runs` + Worker watchdog | Bila sukses terakhir > ambang → alert Telegram ke admin. |

**Aturan wajib job:**
- **Idempotent** — aman dipicu dua kali (upsert by key + tanggal).
- **Timeout & retry terbatas** per sumber; satu sumber gagal tidak menggagalkan job lain.
- **Langkah AI opsional** — timeout pendek; gagal → hasil rule-based tetap disimpan.
- Setiap run menulis `job_runs` (start, end, status, rows, error).

### 4.1 Jadwal awal (WIB; cron disimpan dalam UTC)

| Job | Jadwal WIB | Isi |
|---|---|---|
| `prices` | 09:15, 13:15, 17:15, 21:15 | Spot, kurs, harga merek (jual/buyback) |
| `analysis` | setelah `prices` 17:15 | Indikator, sinyal, snapshot portofolio |
| `news` | 06:30, 18:30 | RSS → dedupe → klasifikasi → ringkasan |
| `digest` | 07:00 | Telegram: harga, sinyal, 3 berita teratas |
| `alerts` | setelah setiap `prices` | Cek threshold harga per user |
| `weekly` | Minggu 19:00 | Ringkasan mingguan portofolio |
| `watchdog` | tiap jam (Worker) | Cek freshness `job_runs` |

Batas Cloudflare free: 5 cron trigger per akun → pakai **3 trigger** (prices / news+digest / watchdog), job lain di-chain dari dalam workflow.

Estimasi pemakaian GitHub Actions: ±15–20 menit/hari (±600 menit/bulan) — di bawah kuota gratis repo privat (verifikasi kuota saat PoC). Alternatif: repo publik (menit tidak terbatas; secret tetap aman di GitHub Secrets).

---

## 5. Sumber Data & Kebijakan Kualitas

### 5.1 API vs scraping

| Cara | Untuk | Catatan |
|---|---|---|
| **API** (JSON resmi) | XAU/USD, USD/IDR, riwayat (yfinance: `GC=F`, `IDR=X`), saham emas | Stabil, kuota kecil → beberapa kali per hari cukup |
| **Scraping** (Python membaca HTML) | Harga jual/buyback Antam, UBS, Galeri24, dll. | Struktur halaman bisa berubah / IP bisa diblok → **wajib fallback input manual admin** |
| **RSS** | Berita | Simpan metadata + link + ringkasan pendek saja |
| **Manual (admin)** | Produk tanpa sumber otomatis | Diberi label sumber `manual` + timestamp |

Rumus spot: `spot_idr_per_gram = xau_usd × usd_idr / 31.1034768`. Ini **bukan** harga retail maupun buyback.

### 5.2 Standar kualitas (dari v1.0, dipertahankan)
1. Setiap record harga: `source`, `observed_at`, `fetched_at`, `currency`, `unit`, `price_type`, `quality_status`.
2. Nilai nol/negatif/lonjakan ekstrem (> X% dari kemarin) → `needs_review`, tidak dipakai sinyal.
3. Data gagal **tidak menimpa** data valid terakhir.
4. UI menampilkan badge: `Fresh` / `Terlambat` / `Stale` / `Tidak tersedia`.
5. DB simpan UTC, UI tampil WIB.

### 5.3 Etika & ToS
Penggunaan internal non-komersial. Scraping secukupnya (≤ 4×/hari per sumber, User-Agent jelas), tidak menyalin isi berita penuh, tidak menjual ulang data.

---

## 6. Taksonomi Emas & Metode Harga

Setiap produk punya `pricing_method`: `scrape | api | manual | formula`.

| Kategori | Contoh | Valuasi |
|---|---|---|
| Batangan bersertifikat | Antam, UBS, Galeri24, Lotus Archi, King Halim | Buyback merek × gram |
| Emas digital / tabungan | Tabungan Emas Pegadaian, Pluang, Tring, Treasury, IndoGold, emas bank syariah | Harga jual-kembali platform × gram |
| Perhiasan | 24K/22K/18K/17K/16K/9K | `kadar/24 × harga acuan × gram × (1 − potongan%)` |
| Koin / dinar | Dinar 22K 4,25 g, koin Antam | Formula kadar atau harga produk |
| Aset terkait emas (opsional) | ETF emas, reksa dana emas, saham tambang | Harga pasar — dipisah dari emas fisik |

`harga acuan` default = buyback Antam per gram (dapat diubah per user).

---

## 7. Desain Engine

### 7.1 Portfolio Engine
```
Ledger transaksi → Lot/kepemilikan → Valuasi → P/L → Snapshot → Proyeksi
```
- **Ledger** = source of truth (beli/jual, produk, gram, kadar, harga, biaya, sumber, catatan).
- **Dua nilai:** *nilai pasar* (harga jual hari ini) dan **nilai likuidasi** (buyback − potongan) — nilai likuidasi jadi angka utama di dashboard.
- **P/L:** unrealized & realized, metode average cost (FIFO opsional).
- **Snapshot harian** per user untuk grafik pertumbuhan.
- **Proyeksi:** Monte Carlo (volatilitas historis 10 tahun) → P10/P50/P90; simulator DCA & target ("100 g dalam 36 bulan").
- **Tujuan (goals):** user membuat target (mis. dana pendidikan) → progress gram/rupiah.

### 7.2 Analysis Engine
```
Data → Indikator → Skor faktor (−2..+2) → Skor gabungan → Guardrail → Sinyal + justifikasi → Backtest
```

| Faktor | Contoh aturan | Bobot draft |
|---|---|---|
| Tren | Harga vs MA50/MA200 | 25% |
| Momentum | RSI(14), jarak dari ATH | 20% |
| Makro | DXY, tren USD/IDR, real yield (bila tersedia) | 20% |
| Biaya fisik | Spread jual–buyback merek; break-even % | 20% |
| Sentimen berita | Rata-rata skor 7 hari (dibatasi) | 10% |
| Volatilitas | ATR/σ 30 hari vs median | 5% |

- Mapping skor → `AKUMULASI` / `BELI_BERTAHAP` / `TAHAN` / `TUNGGU` / `PERTIMBANGKAN_JUAL` / `INSUFFICIENT_DATA`.
- **Dua konteks:** sinyal *spot* (arah pasar) & sinyal *emas fisik* (memasukkan spread; horizon menengah, DCA-friendly).
- **Justifikasi dibangun dari angka** (template). AI hanya merapikan bahasa (opsional).
- **Kontrak sinyal (v1.0):** id, konteks, tipe, skor, faktor+nilai+bobot, alasan, risiko, *invalidation condition*, timestamp input, `rule_version`, `valid_until`, `quality_status`.
- **Validasi:** backtest 5–10 tahun, tanpa look-ahead, termasuk spread; bandingkan vs DCA & buy-and-hold. Kalah dari DCA → label *Eksperimental*.

### 7.3 News Intelligence
```
Kumpulkan (RSS) → Normalisasi & dedupe → Klasifikasi rule → [AI opsional] → Skor relevansi → Simpan → Digest & faktor sentimen
```
- Sumber kandidat: Google News RSS (kata kunci ID & EN), media ekonomi nasional, Kitco, World Gold Council, keterbukaan informasi IDX.
- Perusahaan dipantau: global (Newmont, Barrick, Agnico Eagle) & nasional (ANTM, MDKA, BRMS, PSAB, ARCI, HRTA) — harga saham mingguan via yfinance.
- Kategori: Kebijakan moneter, Inflasi, Geopolitik, Bank sentral, Indonesia, Perusahaan, Ritel emas.
- AI: ringkasan 2 kalimat + dampak (bullish/bearish/netral) + confidence. Fallback: kamus kata kunci.
- UI memisahkan **fakta berita** dan **inferensi dampak**.

---

## 8. Akses & Keamanan

- Supabase Auth **signup dinonaktifkan**; user hanya lewat undangan admin (email/magic link).
- Tabel `profiles`: `role (admin|user|viewer)`, `status (active|suspended|revoked)`, `access_start`, `access_end` (**NULL = unlimited**).
- Fungsi SQL `has_access()` → `status='active' AND now() >= access_start AND (access_end IS NULL OR now() < access_end)`.
- **Semua RLS policy** = `has_access() AND owner_id = auth.uid()` untuk data pribadi; data pasar = `has_access()` saja.
- Admin mengelola akses tetapi **tidak otomatis** dapat membaca portofolio user lain.
- Service key hanya di GitHub Secrets / Worker secrets — tidak pernah ke browser.
- Telegram linking: user klik "Hubungkan Telegram" → kode sekali pakai → `/start <kode>` ke bot → `chat_id` tersimpan.

---

## 9. Model Data (awal)

| Tabel | Kolom utama |
|---|---|
| `profiles` | user_id, display_name, role, status, access_start, access_end, tg_chat_id |
| `products` | id, category, brand, name, unit_gram, karat, pricing_method, source_ref |
| `price_snapshots` | product_id/instrument, price_type (spot/sell/buyback), price, currency, unit, source, observed_at, fetched_at, quality_status |
| `transactions` | id, owner_id, product_id, side, gram, karat, unit_price, fees, trx_date, venue, note |
| `portfolio_snapshots` | owner_id, date, gram_total, market_value, liquidation_value, cost_basis |
| `goals` | id, owner_id, name, target_gram/target_idr, deadline, dca_amount |
| `signals` | id, context, signal_type, score, factors (jsonb), rationale, risks, invalidation, rule_version, created_at, valid_until, quality_status |
| `signal_outcomes` | signal_id, horizon, return_pct, vs_dca_pct |
| `news_items` | id, url_hash, title, source, url, published_at, category, region, companies[], summary, impact, confidence |
| `companies` | ticker, name, region, last_price, change_1w |
| `alert_rules` | id, owner_id, type, threshold, active |
| `notifications` | id, owner_id, channel, type, payload_hash, status, retries, sent_at |
| `job_runs` | id, job, started_at, finished_at, status, rows, error |
| `audit_logs` | actor_id, action, object, at |

---

## 10. Design System & UX

### 10.1 Palet (dari referensi owner)

| Token | Hex | Peran |
|---|---|---|
| `plum-900` | `#522D60` | Primary gelap: header, hero card, teks judul, nav aktif |
| `mauve-600` | `#80426E` | Secondary: tombol sekunder, aksen grafik, chip aktif |
| `peach-400` | `#F2A67B` | Aksen hangat: CTA, highlight, garis grafik |
| `gold-200` | `#FFD38B` | Aksen emas: angka penting, progress, badge |
| `cream-50` | `#FFF8F0` | Background halaman (turunan) |
| `ink-900` | `#2B1A33` | Teks utama (turunan) |
| `up` / `down` | `#2F8F6B` / `#C4505E` | Naik/turun — selalu disertai ikon ▲▼ (tidak mengandalkan warna saja) |

Font: *Plus Jakarta Sans* (UI) + angka tabular. Radius 16–24px, bayangan lembut.

### 10.2 Checklist UX
1. Palet hangat-elegan; hindari kesan terminal trading.
2. Angka besar, kontras ≥ WCAG AA.
3. Satu grafik utama + kartu ringkas; indikator teknis di halaman detail.
4. Ikon per jenis emas untuk input cepat.
5. Bahasa awam + tooltip "Apa ini?".
6. **Berbasis tujuan** (goals + progress).
7. Rekomendasi bernada tenang: sinyal + 1 kalimat + "Lihat alasan". Tanpa FOMO.
8. Disclaimer singkat & ramah.
9. Mobile-first; input transaksi ≤ 30 detik.
10. **Mode privasi** (sembunyikan nominal) satu tap.
11. Notifikasi dapat diatur; default 1 digest + alert penting.
12. Konfirmasi + undo untuk aksi penting.
13. Onboarding 3 langkah: emas pertama → tujuan → Telegram.
14. Uji wireframe ke 3–5 calon user sebelum coding UI.

Mockup: `docs/mockup/dashboard.html` (data contoh, interaktif).

---

## 11. Struktur Repo

```text
gold-tracker/
├─ docs/                  # master doc, mockup, ADR, test reports
├─ web/                   # React + Vite (Cloudflare Pages)
├─ jobs/                  # Python batch
│  ├─ common/             # db, logging, quality, telegram
│  ├─ prices.py  news.py  analysis.py  portfolio.py  notify.py
│  └─ tests/
├─ worker/                # Cloudflare Worker: dispatcher + watchdog
├─ supabase/migrations/   # schema, RLS, seed produk
└─ .github/workflows/     # prices.yml, news.yml, analysis.yml, ci.yml
```

---

## 12. Roadmap

| Fase | Objektif | Output | Gate |
|---|---|---|---|
| 0. Design | Kunci desain | Master v1.1 ✔, mockup ✔, ERD, wireframe disetujui | Review owner |
| 1. PoC Rp0 | Buktikan fondasi | Login undangan + expiry + RLS, job `prices` (1 API + 1 scraping), Worker pemicu+watchdog, 1 pesan Telegram | T-01…T-06, T-11, T-14 PASS |
| 2. Core MVP | Dashboard & portofolio | Semua jenis emas, ledger, valuasi, konversi, goals, grafik, ekspor | T-07, T-08, T-13 PASS |
| 3. Intelligence | Sinyal teraudit | Analysis engine, backtest, halaman rekomendasi | T-09, T-10 PASS |
| 4. News & notif | Berita + Telegram penuh | News pipeline, digest, alert, preferensi | T-12, T-15 PASS |
| 5. Hardening | Stabil & aman | Uji keamanan, recovery drill, UAT 3–5 user | Semua PASS |

---

## 13. Test Matrix

| ID | Test | Status |
|---|---|---|
| T-01 | Web HTTPS dapat diakses user aktif | NOT TESTED |
| T-02 | Email tidak diundang tidak bisa login | NOT TESTED |
| T-03 | User expired/suspended ditolak di semua query (uji langsung ke API) | NOT TESTED |
| T-04 | User A tidak bisa baca/ubah data User B | NOT TESTED |
| T-05 | Harga tersimpan dengan source & timestamp benar | NOT TESTED |
| T-06 | Sumber gagal tidak menimpa data valid; badge stale tampil | NOT TESTED |
| T-07 | Valuasi & P/L cocok dengan hitungan manual (3 kasus, termasuk perhiasan) | NOT TESTED |
| T-08 | Konversi XAU/USD → IDR/gram & kadar akurat | NOT TESTED |
| T-09 | Sinyal dapat dihitung ulang dari input + rule_version | NOT TESTED |
| T-10 | Backtest bebas look-ahead | NOT TESTED |
| T-11 | Job idempotent (dipicu 2× → tidak ada duplikat) | NOT TESTED |
| T-12 | Telegram dedupe & retry | NOT TESTED |
| T-13 | Ekspor & restore berhasil | NOT TESTED |
| T-14 | Pemakaian di bawah free tier (Supabase, Actions, Workers) | NOT TESTED |
| T-15 | Watchdog mengirim alert saat job dimatikan sengaja | NOT TESTED |

---

## 14. Risk Register

| ID | Risiko | Sev | Mitigasi |
|---|---|---|---|
| R-01 | API harga berhenti/limit | High | 2 provider, cache, badge stale |
| R-02 | Scraping merek diblok/berubah | High | Fallback manual admin; test parser harian |
| R-03 | Sinyal tidak akurat | High | Backtest, label eksperimental, disclaimer |
| R-04 | Free tier berubah | High | Cek per fase; Neon sebagai cadangan DB |
| R-05 | Akses expired masih jalan | Critical | RLS `has_access()` + negative test |
| R-06 | Kebocoran data antar user | Critical | RLS owner + test T-04 |
| R-07 | Kehilangan data | Critical | Ekspor mingguan ke repo privat/Drive + restore drill |
| R-08 | GitHub cron telat/nonaktif | Medium | Pemicu Cloudflare + watchdog |
| R-09 | Kuota AI gratis habis | Low | AI opsional, fallback rule-based |
| R-10 | Spam notifikasi | Medium | Dedupe hash + preferensi user |

---

## 15. Protokol Kerja Hemat Kuota

1. Dokumen ini = **single source of truth**; perubahan dicatat di Decision Log.
2. **Satu sesi = satu task ID** dengan scope jelas.
3. Claude mengirim file lengkap sekaligus ke folder kerja `D:\Project\Gold Tracker`, lalu owner push ke GitHub.
4. Testing: Claude memberi checklist singkat; owner menjalankan & melaporkan **hanya yang gagal**.
5. Format laporan:

```text
Task ID   : GT-xxx
Objective : ...
Changes   : file yang dibuat/diubah
Test      : PASS / FAIL / NOT TESTED (+ bukti singkat)
Review    : risiko / temuan
Status    : DONE / PENDING / BLOCKED
Next      : ...
```

---

## 16. Decision Log

| ID | Keputusan | Status |
|---|---|---|
| D-01 | Web app privat responsif (bukan native) | ACCEPTED |
| D-02 | Supabase (DB + Auth + RLS) | PROPOSED |
| D-03 | Batch Python di GitHub Actions | PROPOSED |
| D-04 | Cloudflare Worker hanya pemicu + watchdog | PROPOSED |
| D-05 | Cloudflare Pages untuk frontend | PROPOSED |
| D-06 | Data terjadwal, bukan real-time | ACCEPTED |
| D-07 | Telegram dulu, WA ditunda | PROPOSED |
| D-08 | Rule-based engine; AI opsional | PROPOSED |
| D-09 | Tanpa n8n | ACCEPTED (owner) |
| D-10 | Cover semua jenis emas via `pricing_method` | ACCEPTED (owner) |
| D-11 | Akses internal, non-komersial | ACCEPTED (owner) |
| D-12 | Palet plum–mauve–peach–gold | ACCEPTED (owner) |
| D-13 | Penjelasan sederhana per metrik: template + nilai terkini, AI opsional | ACCEPTED (owner) |
| D-14 | Semua parameter dapat dikonfigurasi lewat UI (`app_config`, `user_prefs`) | ACCEPTED (owner) |
| D-15 | Manajemen user dari UI via endpoint Worker terverifikasi admin | PROPOSED |

---

## 17. Open Questions

1. Jumlah user awal & maksimal?
2. Merek/platform prioritas untuk sumber harga otomatis (3 teratas)?
3. Harga acuan default perhiasan: buyback Antam atau harga toko yang diinput user?
4. Ambang stale: spot 8 jam, harga merek 1 hari — setuju?
5. Repo privat atau publik (tanpa data pribadi)?
6. Domain: subdomain gratis `*.pages.dev` cukup?

---

## 18. Free-Tier Register (dicek 30 Okt 2026 — verifikasi ulang tiap fase)

| Layanan | Batas relevan | Dampak |
|---|---|---|
| Supabase Free | 2 project aktif, 500 MB DB, 1 GB file, 5 GB egress, 50k MAU; pause setelah 7 hari idle | Job harian mencegah pause |
| Cloudflare Workers Free | 100k request/hari, **10 ms CPU** per invocation, 5 cron trigger/akun | Cukup untuk pemicu & watchdog saja |
| Cloudflare Pages | Static hosting gratis | Frontend |
| GitHub Actions | Cron dapat telat 15–30+ menit; scheduled workflow dinonaktifkan setelah 60 hari tanpa aktivitas repo | Diatasi pemicu Cloudflare |
| Neon Free (cadangan) | 100 CU-jam & 0,5 GB per project; scale-to-zero 5 menit | Opsi migrasi |
| WhatsApp Cloud API | Utility template selalu berbayar | Ditunda |
| Telegram Bot API | Gratis | Kanal utama |

*Akhir dokumen v1.1.*
