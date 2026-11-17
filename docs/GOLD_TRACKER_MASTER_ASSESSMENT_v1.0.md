# GOLD TRACKER — MASTER ASSESSMENT & INITIAL SOLUTION BLUEPRINT

**Document ID:** GT-DOC-001  
**Versi:** 1.0 — Initial Assessment  
**Tanggal:** 30 Oktober 2026  
**Status:** DRAFT / For Review (belum ada implementasi atau hasil pengujian)  
**Target:** Private web application, scheduled data, operasional Rp0 dalam batas layanan gratis  
**Peran penyusunan:** Software Analyst, Product Intelligence, Solution Architect, End-to-End Engineering

---

## 1. Executive Summary

**Rekomendasi utama:** bangun *Gold Tracker* sebagai aplikasi web privat dengan **Cloudflare Pages + Workers + D1 + Access + Cron Triggers**, frontend **React/TypeScript**, repositori **GitHub**, dan notifikasi **Telegram Bot**. Fokus awal adalah membuktikan melalui *proof of concept* (PoC) bahwa hosting, autentikasi/otorisasi, basis data, pembaruan harga terjadwal, dan alert dapat berjalan dalam paket gratis **tanpa mengaktifkan billing berbayar**.

Aplikasi ditujukan untuk:

1. Memantau harga emas dunia dan Indonesia dengan sumber serta waktu pembaruan jelas.
2. Mengelola transaksi, kepemilikan emas, valuasi, konversi, proyeksi, dan laporan periodik.
3. Mengeluarkan *decision support* beli/jual yang transparan, dapat dijelaskan, dan diuji secara historis.
4. Mengumpulkan berita dan informasi perusahaan/industri emas global maupun Indonesia.
5. Mengontrol akses pengguna berdasarkan daftar akun, peran, dan masa berlaku (termasuk unlimited).
6. Memproses data secara terjadwal, bukan real-time; memberikan notifikasi Telegram (WhatsApp dievaluasi kemudian).

**Batasan utama:** Target **Rp0 adalah target desain, bukan jaminan biaya nol selamanya**. Kuota dan kebijakan layanan free tier dapat berubah. Harga domestik, buyback, dan berita mempunyai batas akses/izin pengambilan data yang harus diperiksa sebelum integrasi. Rekomendasi transaksi adalah alat bantu analisis, bukan jaminan hasil investasi.

### Assessment kelayakan awal

Skor di bawah adalah estimasi desain, **bukan** hasil uji lapangan atau probabilitas pasti.

| Kebutuhan | Estimasi kelayakan MVP | Prioritas |
|---|---:|---|
| Monitoring harga emas | 95% | P0 |
| Manajemen aset emas | 98% | P0 |
| Konversi dan proyeksi | 98% | P0 |
| Rekomendasi beli/jual dengan justifikasi | 80% | P1 |
| Berita & company intelligence | 90% | P1 |
| Login privat dan batas masa akses | 95% | P0 |
| Scheduled update | 98% | P0 |
| Operasional dalam free tier | 85% | P0 |
| Notifikasi Telegram | 98% | P1 |
| WhatsApp otomatis yang tetap Rp0 | 45% | P2 |

**Prioritas:** P0 = fondasi wajib; P1 = pengayaan penting; P2 = pelengkap.

---

## 2. Scope & Business Requirements

### 2.1 Functional requirements

| ID | Requirement | Kriteria utama |
|---|---|---|
| FR-01 | Monitor harga XAU/USD | Riwayat, pergerakan harga, sumber data, timestamp |
| FR-02 | Monitor emas Indonesia | Harga retail dan buyback bila sumber legal/andal tersedia |
| FR-03 | Portofolio emas | Beli, jual, jumlah gram, produk/pecahan, biaya, metode cost basis |
| FR-04 | Konversi | XAU/USD → perkiraan IDR/gram, konversi berat dan kurs |
| FR-05 | Proyeksi periodik | Skenario konservatif/dasar/optimistis, asumsi eksplisit |
| FR-06 | Analisis beli/jual | Sinyal, alasan, tingkat keyakinan, risiko, timestamp, invalidation condition |
| FR-07 | Berita & informasi perusahaan | Sumber, tanggal, kategori, relevansi, ringkasan dampak |
| FR-08 | Manajemen pengguna | Whitelist, role, active/suspended, expiry/unlimited |
| FR-09 | Scheduler | Update harga, berita, kalkulasi, laporan dan notifikasi |
| FR-10 | Telegram alert | Pengaturan preferensi, log kirim, retry, deduplikasi |
| FR-11 | Reporting/export | Ekspor CSV, laporan portfolio, snapshot periodik |
| FR-12 | Quality monitoring | Data freshness, validasi sumber, error log, fallback |

### 2.2 Non-functional requirements

- **Biaya:** tidak bergantung pada layanan berbayar untuk fitur inti; hindari konfigurasi yang dapat otomatis menaikkan biaya.
- **Privasi:** portofolio tiap pengguna terisolasi di backend; admin bukan otomatis pembaca semua aset pribadi.
- **Keamanan:** seluruh request privat melalui HTTPS dan otorisasi sisi server, bukan hanya pembatasan tampilan UI.
- **Ketahanan:** sumber data bermasalah tidak menimpa snapshot valid terakhir; status data *stale* terlihat.
- **Auditability:** semua rekomendasi dapat ditelusuri ke input, versi aturan, dan waktu kalkulasi.
- **Maintainability:** kode sederhana/modular, dokumentasi singkat dan mudah dipindahkan bila layanan berubah.
- **Usability:** desain responsif untuk desktop dan HP; dashboard mudah dipahami pengguna awam.
- **Testability:** setiap fitur mempunyai acceptance criteria dan tes yang dapat dijalankan ulang.

### 2.3 Out of scope awal

- Trading/eksekusi order otomatis ke broker atau toko emas.
- Feed tick-by-tick real-time atau ultra-low-latency.
- Model AI berbayar sebagai dependensi wajib.
- WhatsApp otomatis sebagai syarat rilis MVP.
- Jaminan profit, prediksi harga pasti, dan nasihat finansial personal yang definitif.

---

## 3. Opsi Arsitektur & Keputusan

| Opsi | Komponen | Keunggulan | Kekurangan / risiko | Keputusan |
|---|---|---|---|---|
| **A: Cloudflare** | Pages, Workers, D1, Access, Cron | Satu ekosistem, SQL, scheduling native, cocok web privat skala kecil | Integrasi auth–API perlu desain teliti; kuota harus diuji | **Pilihan utama** |
| B: Firebase | Hosting, Auth, Firestore, GitHub Actions | Auth mudah, layanan terkelola | Relasi transaksi/analitik lebih rumit; scheduling gratis perlu komponen terpisah | Alternatif |
| C: Supabase | Auth, PostgreSQL, Pages/Vercel | PostgreSQL dan developer experience baik | Risiko pause/limit proyek free; lebih banyak vendor | Alternatif |

**Alasan memilih A:** kebutuhan utama lebih banyak berupa operasi terjadwal dan pengolahan data terstruktur daripada interaksi real-time. Cloudflare D1 cukup sesuai untuk transaction ledger, snapshots, dan tabel analisis; Workers Cron mengurangi kebutuhan orkestrator eksternal. Semua ini tetap **hipotesis desain** sampai PoC berhasil.

### 3.1 Technology stack awal

| Layer | Rekomendasi |
|---|---|
| Frontend | React + TypeScript + Vite |
| UI | Tailwind CSS |
| Chart | Recharts / TradingView Lightweight Charts (cek lisensi) |
| Hosting | Cloudflare Pages |
| Backend | Cloudflare Workers |
| Database | Cloudflare D1 (SQLite-compatible SQL) |
| Identity gate | Cloudflare Access |
| Application authorization | Worker + tabel role/expiry di D1 |
| Scheduler | Workers Cron Triggers |
| Notification | Telegram Bot API |
| Repository | GitHub Private |
| Unit/integration testing | Vitest |
| E2E testing | Playwright |
| Backup/export | Ekspor data terjadwal/manual dan uji restore |

### 3.2 Arsitektur logis

```text
User (browser/HP/laptop)
         |
         v
 Cloudflare Pages (web UI)
         |
         v
 Cloudflare Access (identity/session gate)
         |
         v
 Cloudflare Workers (API + validasi user + expiry + tenant isolation)
         |
         +--------------------------> Cloudflare D1
         |                             users, roles, portfolios,
         |                             transactions, prices,
         |                             signals, news, logs
         |
         +<--- Cron Scheduler <----- Scheduled jobs
         |                             data fetch, calculations,
         |                             quality checks, digests
         |
         +----> Telegram Bot API (notification)
         |
         +<---- Data providers (spot, FX, retail, buyback, news)
```

**Keamanan desain:** Cloudflare Access memverifikasi identitas, tetapi Worker **tetap** memverifikasi user whitelist, role, status, expiry, serta kepemilikan objek untuk setiap API privat. Endpoint scheduler hanya dapat dipanggil oleh mekanisme yang diotorisasi. Rahasia/API token tidak dikirim ke browser.

### 3.3 Free-tier assumption register

Perlu verifikasi ulang ke pricing dan dokumentasi resmi tepat sebelum implementasi (kuota dan syarat dapat berubah):

- Cloudflare Pages: build/deploy dalam free tier.
- Cloudflare Workers: request/CPU/runtime dalam free tier.
- Cloudflare D1: kapasitas data serta batas baca/tulis harian.
- Cloudflare Access: batas jumlah pengguna dan pengaturan autentikasi yang didukung.
- Cloudflare Cron: jumlah trigger dan batas Workers.
- GitHub: repositori privat, CI usage, batas GitHub Actions bila dipakai.
- Data API: rate limit, lisensi, histori, komersial/nonkomersial, stabilitas.
- Telegram: kelayakan metode pengiriman dan rate limit.

**Gate biaya:** jangan menyambungkan payment method atau memilih layanan yang berisiko tagihan otomatis tanpa persetujuan eksplisit. Jika fitur tidak dapat terpenuhi secara gratis, munculkan sebagai *blocked/alternative*, bukan diam-diam memilih fitur berbayar.

---

## 4. Modul Utama

### M1 — Gold Market Monitor (P0)

- XAU/USD (harga spot), estimasi spot IDR/gram, harga emas retail domestik dan buyback jika tersedia.
- Grafik 7D, 30D, 90D, 1Y sesuai ketersediaan data.
- Perubahan absolut/persen serta perbedaan harga spot vs retail dan buyback.
- Source label, timestamp update, freshness status (*fresh*, *delayed*, *stale*, *unavailable*).
- Alur fallback jika harga lokal tidak dapat diakses otomatis.

### M2 — Portfolio Manager (P0)

- Catat transaksi beli/jual: tanggal, produk, merek, pecahan, berat, jumlah unit, harga, pajak/biaya, sumber transaksi, catatan.
- Transaction ledger sebagai *source of truth*; saldo gram dihitung dari transaksi.
- Nilai pasar, estimasi nilai likuidasi bersih, modal perolehan, unrealized P/L, realized P/L.
- Average cost atau cost-basis yang dipilih dan terdokumentasi; tangani lot bila dibutuhkan.
- Snapshot nilai portfolio harian/mingguan/bulanan, ekspor CSV.

### M3 — Investment Decision Intelligence (P1)

- Rule-based engine yang dapat dijalankan ulang, bukan sinyal AI tanpa bukti.
- Faktor kandidat: trend/MA, RSI/MACD, support/resistance, USD/IDR dan indikator makro, spread dan biaya jual-beli, volatilitas/risiko.
- Sinyal: `BUY_CANDIDATE`, `ACCUMULATE`, `HOLD`, `REDUCE_SELL_CANDIDATE`, `WAIT`.
- Setiap sinyal menyimpan indikator, nilai, bobot, alasan, risiko, invalidation trigger, timestamp, versi algoritme, dan data freshness.
- Bila data tidak cukup atau kualitas buruk, keluaran harus `INSUFFICIENT_DATA`, bukan rekomendasi dibuat-buat.
- Decision Journal + backtest untuk evaluasi kualitas dan drift model.

### M4 — News & Company Intelligence (P1)

- Berita ekonomi, kebijakan moneter, industri emas, pertambangan, ANTAM, dan perusahaan emas nasional/global.
- Preferensi sumber utama: rilis resmi regulator/perusahaan, sumber terpercaya, RSS dan API yang diizinkan.
- Simpan metadata/tautan/ringkasan pendek, bukan menyalin penuh konten berhak cipta.
- Klasifikasi topik, geografi (Indonesia/global), perusahaan, relevansi, efek potensial.
- Tampilkan perbedaan antara fakta berita dengan inferensi dampak pasar.

### M5 — Calculator & Projection (P0)

- Konversi troy ounce ke gram, USD/IDR, konversi estimasi spot.
- Break-even penjualan setelah premium/spread/biaya/pajak yang dimasukkan user.
- Simulasi DCA, target gram, target rupiah, pertumbuhan periodik.
- Tiga skenario: konservatif, baseline, optimistis, dengan asumsi terlihat dan dapat diedit.

### M6 — Notifications (P1)

- Telegram price alerts, perubahan sinyal, daily/weekly digest, berita prioritas, status kegagalan scheduler.
- Konfigurasi per user: subscribe/unsubscribe, threshold, kategori, jadwal, timezone WIB.
- Retry dan dedupe event; tidak ada spam jika harga sama atau batch dihitung ulang.
- WhatsApp disimpan sebagai kandidat fase berikutnya setelah evaluasi biaya/API resmi.

### M7 — Administration & Security (P0)

- Invite/allowlist akun, role admin/user/viewer, aktif/suspend/revoke, expiry tanggal atau unlimited.
- Audit log peristiwa penting: login, perubahan hak, transaksi, perubahan data/sinyal admin.
- Proteksi data pengguna di seluruh API dan query.
- Indikator masa berlaku akun serta pengelolaan akses admin.

### Cross-cutting utilities

- **Data Quality Monitor:** kelengkapan, freshness, nilai outlier, kegagalan sumber, perbedaan provider.
- **Decision Journal:** arsip alasan dan hasil rekomendasi.
- **Portfolio Snapshot:** konsistensi grafik performance historis.
- **Export & Recovery:** backup, restore, dan perbaikan data.

---

## 5. Data Sources & Quality Policy

| Kategori | Kandidat | Mekanisme | Risiko/tindak lanjut |
|---|---|---|---|
| XAU/USD | Gold API | Endpoint API, scheduled | Validasi lisensi, limit, dan timestamp; uji silang |
| USD/IDR | Bank Indonesia | Sumber resmi jika akses tersedia | Jangan asumsikan halaman web = API |
| Harga Antam retail | Logam Mulia | Integrasi jika akses/izin mendukung; manual fallback | Struktur halaman, izin scraping, perbedaan pecahan |
| Harga Antam buyback | Logam Mulia | Sesuai akses legal, manual fallback | Potongan/pajak dan syarat transaksi |
| Berita global | World Gold Council, rilis bank sentral, penerbit terpercaya | RSS/API/tautan resmi | Hak cipta, rate limit, duplikasi |
| Berita Indonesia | BI, OJK, BEI/IDX, ANTAM, rilis perusahaan | Situs resmi/feed yang diizinkan | Timestamp, klasifikasi, peninjauan |
| Data perusahaan | Laporan tahunan/keterbukaan informasi/regulator | Metadata, rangkuman, link | Pembaruan tidak harus harian |

**Rumus estimasi harga spot:**

```text
spot_idr_per_gram = (xau_usd_per_troy_ounce * usd_idr) / 31.1034768
```

**Penting:** hasil konversi ini **bukan** harga retail atau harga buyback emas fisik. Harga fisik dapat memiliki premium, spread, biaya, dan pajak. Penilaian portofolio sebaiknya menampilkan estimasi nilai likuidasi **bersih** bila semua input tersedia.

### Standar kualitas data minimum

1. Setiap record harga menyertakan `source`, `observed_at`, `fetched_at`, `currency`, `unit`, `market_type`, dan `quality_status`.
2. Harga negatif/nol, timestamp tidak masuk akal, atau lonjakan ekstrem ditandai untuk review.
3. Tidak menimpa harga valid dengan data kosong atau data salah.
4. Jika API gagal, UI menampilkan data terakhir **beserta** label stale secara eksplisit.
5. Gunakan waktu UTC dalam database, tampilkan WIB pada UI.

---

## 6. Decision Engine Design

**Prinsip:** *Decision support*, bukan trading otomatis atau janji keuntungan. Keputusan akhir tetap pada pengguna.

### Model scoring awal (hipotesis, belum terkalibrasi)

| Faktor | Draft bobot |
|---|---:|
| Tren / moving average | 25% |
| Momentum: RSI, MACD | 20% |
| Support / resistance | 15% |
| Makro & USD/IDR | 15% |
| Valuasi, spread, break-even | 15% |
| Volatilitas dan risiko | 10% |
| **Total** | **100%** |

**Perhatian:** Bobot dan ambang sinyal bukan resep finansial yang sudah teruji. Perlu pengujian *out-of-sample* dan kalibrasi per instrumen (spot vs emas fisik).

### Output signal contract

```text
signal_id
asset / instrument / market
signal_type
score & confidence (jika telah terkalibrasi)
reason_codes & supporting_metrics
risk_factors
invalidation_conditions
input_data_timestamp & source_ids
rule_version
created_at / valid_until
quality_status
```

### Validasi kualitas sinyal

- Gunakan hanya informasi yang telah tersedia pada saat sinyal historis dibuat (*no look-ahead bias*).
- Bandingkan melawan buy-and-hold dan DCA sederhana.
- Masukkan biaya transaksi, spread harga fisik, serta asumsi pajak yang relevan.
- Ukur total return, drawdown, frekuensi transaksi, *win rate*, dan *risk-adjusted performance* jika data cukup.
- Simpan semua sinyal, termasuk yang gagal; hindari cherry-picking.
- Jangan menampilkan confidence seolah probabilitas keberhasilan sebelum kalibrasi.
- Bila hasil tidak kuat secara statistik, status fitur menjadi *experimental*.

### Contoh interpretasi (simulasi)

```text
Signal: WAIT / HOLD
Rationale: tren masih positif tetapi momentum melemah;
           spread emas fisik membuat pembelian agresif kurang menarik.
Risk: USD/IDR dan volatilitas spot dapat berubah signifikan.
Re-evaluation: harga mendekati zona akumulasi teruji atau tren kembali menguat.
Status: simulasi untuk demonstrasi format, bukan sinyal pasar aktual.
```

---

## 7. User Access, Roles & Expiry

### Role baseline

| Role | Akses utama |
|---|---|
| Admin | Kelola user, jadwal, sumber, konfigurasi, health logs; tidak otomatis berhak membuka data portfolio user lain |
| User | Dashboard dan portfolio pribadi; buat/ubah transaksi sendiri; menerima alert |
| Viewer | Melihat modul yang diizinkan, tidak mengubah transaksi |

### Field pengguna minimal

`user_id`, `identity_email`, `role`, `status`, `access_start_at`, `access_expires_at` (nullable untuk unlimited), `created_at`, `updated_at`.

### Business rules

1. Login berhasil pada identity provider **tidak otomatis** memberi izin menggunakan aplikasi.
2. Email harus tercatat di allowlist dan status active.
3. `access_start_at <= now` dan (`access_expires_at > now` atau null/unlimited).
4. Hak akses diperiksa di **backend** pada tiap request yang sensitif.
5. Expired/suspended/revoked tidak dapat mengakses API langsung, meskipun browser masih memiliki sesi identitas.
6. Semua query portfolio dibatasi `owner_user_id` dan diuji terhadap *horizontal privilege escalation*.
7. Semua jam disimpan UTC dan dapat ditampilkan dalam Asia/Jakarta.

**Catatan:** Cloudflare Access mengelola gerbang identitas dan sesi, tetapi expiry aplikasi spesifik Gold Tracker tetap memerlukan otorisasi Worker + D1.

---

## 8. Scheduling & Integrations

### Jadwal usulan (WIB, dapat dikonfigurasi)

| Job | Frekuensi awal | Dependensi | Tindakan bila gagal |
|---|---|---|---|
| Spot gold refresh | Setiap 4 jam | Provider API | Simpan data sebelumnya + stale flag + log |
| USD/IDR refresh | Harian setelah publikasi | Sumber kurs | Mark pending; tidak membuat angka palsu |
| Harga retail/buyback | Harian setelah publikasi | Sumber domestik / admin | Fallback manual + label sumber |
| Recalculate portfolio | Sesudah snapshot harga baru | D1 prices, transactions | Retain last snapshot + error log |
| Recalculate signals | Sesudah validasi harga | Engine, metrics | No-signal jika data tidak mencukupi |
| News refresh | 2× sehari | RSS/API sumber | Catat fetch failure; skip duplikat |
| Telegram digest | 1× sehari | Snapshot, preferences | Retry terbatas + dedupe |
| Weekly summary | Mingguan | Portfolio, signals | Retry + audit |

Cloudflare Cron didefinisikan dalam UTC; seluruh jadwal user-facing perlu dikonversi secara benar ke WIB. Frekuensi akhir disesuaikan limit provider dan rate limit layanan.

### n8n vs alternatif

- **Cloudflare Cron (pilihan utama):** minimal layanan dan maintenance; sesuai untuk pekerjaan terjadwal sederhana.
- **GitHub Actions (alternatif):** cocok untuk batch job/CI terbatas; perhatikan limit, keandalan jadwal, dan pengamanan token.
- **n8n self-hosted (opsional):** perangkat lunaknya tersedia gratis, tetapi membutuhkan hosting/komputer selalu menyala dan maintenance; **tidak dimasukkan pada baseline**.
- **n8n Cloud:** tidak cocok untuk syarat Rp0 sebagai fondasi permanen.

### Telegram vs WhatsApp

- **Telegram:** baseline notifikasi otomatis via Bot API, dengan consent/opt-in dan perlindungan token.
- **WhatsApp Business Platform:** perlu assessment biaya/template/ketentuan resmi; jangan diasumsikan pesan notifikasi proaktif selalu gratis.
- Bungkus semua kanal di antarmuka `NotificationService` agar mudah diganti tanpa mengubah logic sinyal.

---

## 9. Rancangan Data (Initial Entity List)

Daftar ini adalah awal untuk ERD lengkap, bukan schema final.

| Entitas | Isi utama |
|---|---|
| `users` | Identitas, role, status, expiry |
| `user_preferences` | Waktu digest, kategori alert, timezone |
| `portfolio_accounts` | Kelompok portfolio dan owner |
| `gold_products` | Merek, jenis, pecahan, berat/unit |
| `transactions` | Beli/jual, waktu, berat, harga, biaya, referensi |
| `market_price_snapshots` | Spot, FX, retail, buyback, timestamp, sumber, kualitas |
| `portfolio_snapshots` | Valuasi periodik, per user/portfolio |
| `analytical_signals` | Skor, type, alasan, rule version, risk, validity |
| `signal_outcomes` | Hasil backtesting/performance tracking |
| `news_items` | Headline, link, source, topic, published time, relevansi |
| `companies` | Identitas perusahaan dan wilayah |
| `news_company_links` | Relasi berita–perusahaan |
| `notifications` | Tujuan, template, kanal, status, retry count |
| `scheduled_job_runs` | Job, waktu mulai/selesai, hasil/error |
| `audit_logs` | Perubahan kritis oleh actor, waktu, objek |

**Prinsip database:** idempotent scheduled ingestion, constraint validasi, indeks menurut waktu dan pemilik, migrasi schema terkontrol, dan backup/restore yang terbukti.

---

## 10. Roadmap Delivery

| Fase | Objektif | Artefak / output | Gate untuk lanjut |
|---|---|---|---|
| **0. Design baseline** | Definisi produk dan teknis | BRD, scope, UI sitemap/wireframe, ERD, API, backlog, test matrix | Review scope dan keputusan arsitektur |
| **1. Zero-cost PoC** | Membuktikan teknologi | URL online, login, expiry, DB, 1 API data, 1 Cron, test report | Semua fitur PoC lulus + tidak ada fitur berbayar |
| **2. Core MVP** | Dashboard & portfolio | Harga, grafik, transaksi, kalkulator, ekspor | Akurasi hitung, otorisasi, UX, restore |
| **3. Investment intelligence** | Sinyal yang dapat diaudit | Rule engine, jurnal, backtest, justifikasi | Backtesting & anti-look-ahead checks |
| **4. News & notifications** | Monitoring berita & Telegram | Feed, klasifikasi, alert, digest | Source compliance + anti-spam + retry |
| **5. Release hardening** | Stabilitas & keamanan | Security tests, load tests, observability, UAT | Penerimaan hasil tes dan recovery drill |

**Urutan prioritas:** Security dan kualitas data sejak Fase 1, bukan setelah semua fitur selesai.

### Testing & Acceptance Checklist

| ID | Test | Status awal |
|---|---|---|
| T-01 | Deployment HTTPS dapat diakses oleh akun yang diizinkan | NOT TESTED |
| T-02 | Pengguna tidak masuk whitelist ditolak | NOT TESTED |
| T-03 | Akun expired/suspended ditolak dari seluruh API privat | NOT TESTED |
| T-04 | User A tidak dapat membaca/mengubah portfolio User B | NOT TESTED |
| T-05 | Data harga tersimpan dengan source dan timestamp benar | NOT TESTED |
| T-06 | API gagal tidak menghapus harga valid terakhir | NOT TESTED |
| T-07 | Kalkulasi transaction ledger dan P/L cocok contoh manual | NOT TESTED |
| T-08 | Konversi XAU/USD → IDR/gram akurat pada input uji | NOT TESTED |
| T-09 | Sinyal bisa dihitung ulang dari input dan rule version | NOT TESTED |
| T-10 | Backtest bebas look-ahead bias yang jelas | NOT TESTED |
| T-11 | Scheduled job aman dijalankan ulang (idempotent) | NOT TESTED |
| T-12 | Telegram menghindari alert duplikat dan mendukung retry | NOT TESTED |
| T-13 | Backup diekspor dan dapat di-*restore* | NOT TESTED |
| T-14 | Operasional PoC tidak melewati batas free tier | NOT TESTED |

**Definition of Done (DoD):** implementasi selesai + kriteria diterima + tes lulus + review keamanan/data + dokumentasi diperbarui + biaya tetap Rp0.

---

## 11. Risk Register

| Risk ID | Risiko | Severity | Mitigasi / gate |
|---|---|---|---|
| R-01 | API harga berhenti / rate limit | HIGH | Alternatif sumber, caching, quality status, graceful degradation |
| R-02 | Harga domestik tak dapat diambil secara legal/stabil | HIGH | Periksa syarat akses; input admin; tampilkan sumber |
| R-03 | Sinyal beli/jual tidak akurat | HIGH | Backtest, benchmark, paper evaluation, transparansi asumsi |
| R-04 | Free tier berubah atau kuota habis | HIGH | Monitoring usage, kurangi frekuensi, rencana migrasi |
| R-05 | Expired account masih bisa akses API | CRITICAL | Server-side checks, negative tests, audit |
| R-06 | Kebocoran portfolio antar-pengguna | CRITICAL | Owner filtering, authorization middleware, E2E security tests |
| R-07 | Kehilangan/korupsi data | CRITICAL | Backup, export, restore drills, transaction integrity |
| R-08 | Artikel salah klasifikasi atau ada isu hak cipta | MEDIUM | Trusted sources, metadata & link, review, tidak menyalin full text |
| R-09 | Notifikasi gagal atau spam | MEDIUM | Retry bounded, dedupe, per-user preference, logs |
| R-10 | Provider/stack gratis tidak cocok di lapangan | HIGH | PoC segera, penggantian komponen modular |

---

## 12. Protokol Pengerjaan Hemat Kuota ChatGPT

**Tujuan:** sederhana, satu sumber dokumentasi, meminimalkan diskusi berulang, namun menjaga disiplin engineering.

1. **Master document tunggal:** `GOLD_TRACKER_MASTER.md` menjadi source of truth; versi assessment ini adalah dokumen awal untuk diadopsi dan direvisi.
2. **Satu fase/satu batch pekerjaan:** tiap sesi memiliki task ID dan batasan ruang lingkup.
3. **Desain sebelum coding:** kriteria penerimaan jelas sebelum menulis implementasi.
4. **Testing dan review wajib:** tidak menyatakan `DONE` berdasarkan tampilan saja.
5. **Jangan ulang keputusan:** update decision log jika ada perubahan alasan/arsitektur.
6. **Minimal dependensi:** hindari n8n, AI API berbayar, microservices, dan konfigurasi kompleks bila belum dibutuhkan.
7. **Log ringkas setiap pekerjaan:** objective → changes → test → findings → status → next action.
8. **Kredensial:** jangan menyimpan token/API key/email pribadi dalam dokumen Markdown publik/repo. Gunakan pengelolaan secret yang aman.

### Format laporan task standar

```text
Task ID: GT-xxx
Objective: ...
Scope: ...
Deliverables: ...
Test evidence: PASS / FAIL / NOT TESTED
Review / risk: ...
Status: DONE / PENDING / BLOCKED
Next action: ...
```

---

## 13. Decision Log (Baseline)

| ID | Keputusan sementara | Status | Alasan |
|---|---|---|---|
| D-01 | Private web app, bukan native mobile app | PROPOSED | Responsif, satu deployment, biaya lebih rendah |
| D-02 | Cloudflare stack sebagai pilihan utama | PROPOSED | Integrasi hosting/API/DB/cron/access dalam free tier |
| D-03 | Data scheduled, bukan real-time | ACCEPTED AS REQUIREMENT | Hemat resource dan kompleksitas |
| D-04 | Telegram prioritas, WA belakangan | PROPOSED | Biaya dan integrasi lebih sesuai |
| D-05 | Rule-based signal engine sebelum AI generatif | PROPOSED | Transparan, dapat diuji & diaudit |
| D-06 | n8n tidak wajib untuk MVP | PROPOSED | Cron native lebih simpel |
| D-07 | Transaction ledger + portfolio snapshot | PROPOSED | Keakuratan, histori, audit |
| D-08 | PoC Rp0 sebelum coding seluruh fitur | PROPOSED | Validasi risiko paling awal |

---

## 14. Open Questions untuk Phase 0

Pertanyaan ini **tidak menghalangi assessment awal**, tetapi harus dikunci sebelum implementasi detail:

1. Fokus emas: fisik Antam saja, produk lain, tabungan emas, atau seluruhnya?
2. Portfolio dikelola untuk satu pemilik per akun atau ada portfolio kelompok?
3. Produk/harga domestik prioritas: Antam, UBS, Pegadaian, atau kombinasi?
4. Jumlah pengguna awal dan target maksimal untuk kontrol akses?
5. Sinyal investasi difokuskan pada emas spot, emas fisik, atau dua konteks terpisah?
6. Apakah ada sumber data yang sudah dimiliki atau wajib dipakai?
7. Format laporan/ekspor yang diperlukan: CSV saja atau PDF juga?
8. Batas umur data yang dianggap stale (misal spot 8 jam, retail 2 hari)?

---

## 15. Rekomendasi Next Step

### Immediate next work: `GT-001 — Solution Design v1.0`

Buat dan review satu spesifikasi yang memuat:

- BRD ringkas + user stories prioritas.
- Detail alur login, hak akses, expiry/unlimited.
- Sitemap dan wireframe dashboard utama.
- Database ERD + ownership model.
- Backend endpoint contract dan ingestion lifecycle.
- Data source assessment dan schedule matrix terverifikasi.
- Signal/decision-engine specification serta validation plan.
- Backlog per fase dengan testing/acceptance criteria.
- Cost & provider limits checklist terkini.

**Kemudian:** `GT-002 — Zero-Cost Technical PoC`. Jangan mengembangkan semua modul sampai PoC lolos.

### Final Recommendation

**Pilih arsitektur Cloudflare sebagai baseline kerja dan uji secara dini melalui PoC.** Fokus MVP pada keandalan harga, ketepatan nilai portfolio, dan keamanan akses. Setelah fondasi lolos, bangun investment intelligence dan berita dengan pengujian terukur. Target tanpa biaya harus dicek pada setiap fase, bukan hanya di awal.

---

## 16. Referensi Awal (harus diperiksa ulang saat eksekusi)

- Cloudflare Pricing / Plans: https://www.cloudflare.com/plans/
- Cloudflare Workers Pricing: https://developers.cloudflare.com/workers/platform/pricing/
- Cloudflare D1 Pricing: https://developers.cloudflare.com/d1/platform/pricing/
- Cloudflare Pages Limits: https://developers.cloudflare.com/pages/platform/limits/
- Cloudflare Access: https://developers.cloudflare.com/cloudflare-one/identity/
- Workers Cron Triggers: https://developers.cloudflare.com/workers/configuration/cron-triggers/
- Gold API Documentation: https://gold-api.com/docs
- Bank Indonesia Kurs: https://www.bi.go.id/id/fungsi-utama/moneter/informasi-kurs/default.aspx
- Logam Mulia Harga Emas: https://www.logammulia.com/id/harga-emas-hari-ini
- Logam Mulia Buyback: https://www.logammulia.com/id/sell/gold
- Telegram Bot API: https://core.telegram.org/bots/api
- GitHub Actions: https://docs.github.com/en/actions
- n8n Self-hosting: https://docs.n8n.io/hosting/
- Supabase Pricing: https://supabase.com/pricing
- Firebase Pricing: https://firebase.google.com/pricing

**Disclaimer sumber:** Referensi merupakan titik awal kajian, bukan pernyataan bahwa seluruh API bisa diakses secara otomatis, gratis tanpa batas, atau diizinkan untuk scraping. Kuota dan syarat layanan harus diverifikasi ulang pada tanggal eksekusi.

---

*End of Gold Tracker Master Assessment v1.0 — dokumen assessment dan rencana awal, bukan klaim aplikasi sudah dibangun atau diuji.*
