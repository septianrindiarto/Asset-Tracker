# Fase 1 — Panduan Manual (PoC Rp0)

**Tujuan Fase 1:** membuktikan fondasi berjalan **gratis & otomatis**:
login hanya untuk yang diundang → masa akses dicek database → harga emas diambil terjadwal → tersimpan aman → laporan & alert ke Telegram.

**Estimasi waktu Anda:** ±2–3 jam (sekali saja). Tidak perlu kartu kredit di layanan mana pun.
**Urutan wajib:** A → B → C → D → E → (F opsional) → G → H → I → J → K.

> Notasi: `Menu › Submenu` = klik berurutan. Nama menu di dashboard layanan bisa sedikit berbeda dari panduan ini; cari kata kunci yang paling mirip.
> Semua perintah ditulis untuk **PowerShell di Windows**. Kalimat setelah tanda `#` adalah penjelasan, tidak perlu diketik.

---

## Peta yang akan Anda siapkan

```
GitHub (kode + job Python) ◄── dipicu ── Cloudflare Worker (jadwal + watchdog)
      │ tulis harga                              │ alert
      ▼                                          ▼
Supabase (database + login) ◄── baca ── Cloudflare Pages (web)     Telegram Bot
```

Catat semua nilai rahasia di **satu file Notepad sementara** (jangan disimpan di folder proyek). Hapus setelah semuanya selesai diisi.

| Nama | Didapat di langkah | Rahasia? |
|---|---|---|
| SUPABASE_URL | C8 | Tidak |
| Publishable/anon key | C8 | Tidak (aman di browser) |
| SUPABASE_SERVICE_KEY (secret key) | C8 | **YA** |
| TELEGRAM_BOT_TOKEN | D1 | **YA** |
| TELEGRAM_ADMIN_CHAT_ID | D3 | Tidak |
| GH_TOKEN | H1 | **YA** |
| MANUAL_KEY (buat sendiri, mis. 20 karakter acak) | H3 | **YA** |

---

## A. Pasang alat (sekali saja)

Buka **PowerShell** (tekan Start, ketik "PowerShell", Enter), lalu jalankan:

```powershell
winget install --id Git.Git -e              # Git: mencatat versi kode & mengirim ke GitHub
winget install --id Python.Python.3.12 -e   # Python: menjalankan job & tes di laptop (opsional tapi disarankan)
winget install --id OpenJS.NodeJS.LTS -e    # Node.js: dibutuhkan alat Cloudflare (wrangler)
```

**Tutup lalu buka lagi PowerShell**, kemudian cek:

```powershell
git --version      # harus tampil "git version ..."
python --version   # harus tampil "Python 3.12..."
node --version     # harus tampil "v20..." atau lebih baru
```

Jika `winget` tidak dikenal: unduh manual dari git-scm.com, python.org (centang **"Add python.exe to PATH"** saat instal), dan nodejs.org (versi LTS).

---

## B. Simpan kode ke GitHub (repo privat)

**B1.** Buka github.com → login/daftar → klik **+** (kanan atas) › **New repository**
- Repository name: `gold-tracker`
- Pilih **Private**
- **Jangan** centang "Add a README" (kita sudah punya)
- Klik **Create repository**

**B2.** Di PowerShell:

```powershell
cd "D:\Project\Gold Tracker"                 # masuk ke folder proyek
New-Item -ItemType Directory -Force .github\workflows | Out-Null   # membuat folder khusus GitHub Actions
Copy-Item setup\github-workflows\*.yml .github\workflows\ -Force  # menyalin 3 workflow (prices, ci, probe) ke tempat yang dibaca GitHub
git config --global user.name "Arhent"       # nama penulis commit (sekali seumur laptop)
git config --global user.email "EMAIL_GITHUB_ANDA"
git init                                     # menjadikan folder ini repositori Git
git add .                                    # menandai semua file untuk disimpan
git commit -m "Fase 1: PoC"                  # menyimpan snapshot pertama
git branch -M main                           # menamai cabang utama "main"
git remote add origin https://github.com/USERNAME_ANDA/gold-tracker.git   # menghubungkan ke repo GitHub
git push -u origin main                      # mengirim kode ke GitHub
```

Saat `git push` pertama, jendela login GitHub muncul → pilih **Sign in with your browser** → izinkan.

✅ **Cek:** refresh halaman repo di GitHub → folder `docs`, `jobs`, `web`, dll. muncul.

> Setiap kali saya mengirim file baru ke folder ini, cukup jalankan 3 perintah (jika saya menyebut ada workflow baru, jalankan dulu baris `Copy-Item` di atas):
> ```powershell
> git add .
> git commit -m "pesan singkat perubahan"
> git push
> ```

---

## C. Supabase (database + login)

**C1. Buat project**
1. Buka supabase.com → **Start your project** → login dengan GitHub.
2. **New project** → isi:
   - Name: `gold-tracker`
   - Database Password: klik **Generate**, lalu simpan di password manager (jarang dipakai, tapi jangan sampai hilang)
   - Region: **Southeast Asia (Singapore)** (paling dekat dengan Indonesia)
3. **Create new project** → tunggu ±2 menit sampai status hijau.

**C2. Jalankan skema database**
1. Menu kiri **SQL Editor** › **New query**.
2. Buka file `D:\Project\Gold Tracker\supabase\migrations\0001_init.sql` dengan Notepad → **Ctrl+A**, **Ctrl+C**.
3. Tempel di SQL Editor → klik **Run**.
4. ✅ Harus muncul *"Success. No rows returned"*. Jika error, salin pesannya ke saya. **Jangan** dijalankan dua kali.
5. Klik **New query** lagi → tempel isi `supabase\migrations\0002_galeri24_source.sql` → **Run** → ✅ *Success*.
   *Fungsinya:* mengalihkan sumber harga Antam/UBS/Galeri24/Lotus Archi ke situs Galeri24 (Logam Mulia memblokir akses otomatis).

**C3. Cek tabel**: menu **Table Editor** → harus ada `profiles`, `app_config`, `products`, `price_snapshots`, `job_runs`. Isi `products` = 7 baris (setelah 0002).

**C4. Tutup pendaftaran umum (wajib)**
**Authentication › Sign In / Providers**:
- **Email**: pastikan *enabled*.
- Matikan **Allow new users to sign up** → **Save**.
  *Fungsinya:* orang asing tidak bisa membuat akun sendiri. Hanya yang Anda undang yang bisa masuk.

**C5. URL sementara**: **Authentication › URL Configuration** → Site URL: `http://localhost:8000` → Save. (Diganti di langkah G3.)

**C6. Undang diri sendiri**: **Authentication › Users › Add user › Send invitation** → isi email Anda → kirim.
*Fungsinya:* membuat akun Anda. Database otomatis membuat profil dengan masa akses default 30 hari.
Email undangan tidak perlu diklik sekarang.

**C7. Jadikan diri Anda admin unlimited**: **SQL Editor › New query**:

```sql
update profiles set role = 'admin', access_end = null where email = 'EMAIL_ANDA';
select email, role, status, access_end from profiles;
```

✅ Baris Anda: role `admin`, access_end kosong (NULL = unlimited).

**C8. Ambil alamat & kunci**: **Project Settings › API Keys** (kadang di **Settings › API**):
- **Project URL** → `https://xxxx.supabase.co` (bisa juga di **Settings › Data API** atau tombol **Connect**)
- **Publishable key** (`sb_publishable_...`) — atau, di project lama, **anon public** (`eyJ...`)
- **Secret key** (`sb_secret_...`, klik *Reveal*) — atau **service_role** (`eyJ...`)

⚠️ Secret key = kunci utama database. Hanya untuk GitHub Secrets dan Worker. **Jangan** taruh di `web/`, chat, atau screenshot.

> Catatan: email login/undangan memakai pengirim bawaan Supabase yang dibatasi beberapa email per jam. Untuk PoC cukup. Jika email tidak datang, tunggu sebentar dan cek folder spam. Pengirim email sendiri (SMTP gratis) disiapkan di Fase 5.

---

## D. Bot Telegram

**D1.** Di Telegram, cari **@BotFather** (centang biru) → kirim `/newbot`
- Nama tampilan: `Gold Tracker Arhent`
- Username: harus diakhiri `bot`, mis. `goldtracker_arhent_bot`
- BotFather membalas **token** seperti `123456789:AA...` → catat (**rahasia**).

**D2.** Buka bot Anda (klik link dari BotFather) → tekan **Start** → kirim pesan `halo`.

**D3.** Di browser buka (ganti TOKEN):
`https://api.telegram.org/botTOKEN/getUpdates`
Cari `"chat":{"id":123456789` → angka itu = **TELEGRAM_ADMIN_CHAT_ID**.
Jika hasilnya `"result":[]`, kirim `halo` lagi ke bot lalu refresh.

---

## E. Pasang rahasia di GitHub & jalankan job pertama

**E1.** Repo GitHub › **Settings › Secrets and variables › Actions › New repository secret**. Buat satu per satu:

| Name | Value |
|---|---|
| `SUPABASE_URL` | Project URL |
| `SUPABASE_SERVICE_KEY` | Secret key Supabase |
| `TELEGRAM_BOT_TOKEN` | Token bot |
| `TELEGRAM_ADMIN_CHAT_ID` | Chat id |
| `METALCHARTS_API_KEY` | *(opsional, lewati dulu)* |

*Fungsinya:* job membaca nilai ini saat berjalan. Nilainya tersembunyi, bahkan dari log.

**E2.** Tab **Actions**. Jika ada tombol *"I understand my workflows, go ahead and enable them"* → klik.

**E3.** Klik workflow **prices** (kiri) › **Run workflow** › biarkan default › **Run workflow**.
Tunggu 1–2 menit, lalu klik run tersebut untuk melihat log.

✅ **Cek:**
- Run berwarna hijau ✓.
- Telegram menerima pesan **✅ Gold Tracker · prices (success)** atau **⚠️ (partial)**. *Partial wajar di awal* bila scraping Antam belum cocok — diselesaikan di langkah I.
- Supabase **Table Editor › price_snapshots** berisi baris `XAU_USD`, `USD_IDR`, `SPOT_IDR_G`.
- **job_runs** berisi 1 baris berstatus `success`/`partial`.

Workflow **ci** juga berjalan otomatis setiap `git push` dan harus hijau (18 tes lulus).

---

## F. (Opsional) Uji di laptop

```powershell
cd "D:\Project\Gold Tracker"
python -m venv .venv                     # membuat lingkungan Python khusus proyek (tidak mengganggu Python lain)
.\.venv\Scripts\Activate.ps1             # mengaktifkannya; awal baris berubah menjadi (.venv)
```

Jika muncul *"running scripts is disabled on this system"*:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned   # izinkan skrip lokal untuk akun Anda saja; jawab Y
.\.venv\Scripts\Activate.ps1
```

Lanjutkan:

```powershell
pip install -r jobs\requirements.txt     # memasang library yang dibutuhkan job
python -m pytest jobs\tests -q           # menjalankan tes otomatis → harap "18 passed, 2 skipped"
copy .env.example .env                   # membuat file rahasia lokal (tidak ikut ke GitHub)
notepad .env                             # isi nilai seperti di E1, lalu simpan
python -m jobs.prices --dry-run          # coba ambil harga TANPA menyimpan ke database/Telegram
python -m jobs.prices --trigger laptop   # ambil & simpan sungguhan
```

---

## G. Web di Cloudflare Pages

**G1. Isi konfigurasi web**: buka `web\config.js` dengan Notepad → ganti:
- `SUPABASE_URL` → Project URL
- `SUPABASE_ANON_KEY` → **Publishable/anon key** (BUKAN secret key)

Simpan, lalu:

```powershell
git add .
git commit -m "Isi konfigurasi web"
git push
```

**G2. Deploy**
1. Buka dash.cloudflare.com → daftar/login.
2. **Workers & Pages › Create › Pages › Connect to Git** (atau *Import an existing Git repository*) → hubungkan akun GitHub → pilih repo `gold-tracker`.
3. Build settings:
   - Framework preset: **None**
   - Build command: *(kosong)*
   - Build output directory: `web`
4. **Save and Deploy** → tunggu ±1 menit → dapat URL `https://gold-tracker-xxx.pages.dev`.
*Fungsinya:* setiap `git push`, web otomatis diperbarui.

**G3. Daftarkan URL web ke Supabase**: **Authentication › URL Configuration**
- Site URL: URL pages.dev Anda
- Redirect URLs › **Add URL**: URL yang sama → Save.
*Fungsinya:* link login di email mengarah ke web Anda.

**G4. Coba login**: buka URL pages.dev → isi email Anda → **Kirim link masuk** → buka email → klik link.
✅ Harus tampil: **Akses aktif ✓**, kartu harga, tabel harga, dan **Log job (admin)**.

---

## H. Cloudflare Worker (pemicu tepat waktu + watchdog)

**H1. Token GitHub untuk Worker**
GitHub › foto profil › **Settings › Developer settings › Personal access tokens › Fine-grained tokens › Generate new token**:
- Token name: `gold-tracker-worker`
- Expiration: pilih yang terpanjang yang tersedia → **catat tanggal kedaluwarsanya di kalender**
- Repository access: **Only select repositories** → `gold-tracker`
- Permissions › Repository permissions › **Actions: Read and write**
- **Generate token** → salin (hanya tampil sekali).
*Fungsinya:* izin terbatas agar Worker hanya bisa menjalankan workflow di repo ini.

**H2.** Buka `worker\wrangler.toml` → ganti `GANTI_USERNAME_GITHUB` dengan username GitHub Anda → simpan.

**H3. Pasang & deploy** (PowerShell):

```powershell
cd "D:\Project\Gold Tracker\worker"
npm install                                   # memasang wrangler (alat resmi Cloudflare) ke folder ini
npm test                                      # tes logika watchdog → "semua tes lulus"
npx wrangler login                            # browser terbuka → klik Allow (izinkan wrangler mengelola akun Cloudflare Anda)
npx wrangler secret put GH_TOKEN              # simpan rahasia ke Worker; tempel nilai lalu Enter
npx wrangler secret put SUPABASE_URL
npx wrangler secret put SUPABASE_SERVICE_KEY
npx wrangler secret put TELEGRAM_BOT_TOKEN
npx wrangler secret put TELEGRAM_ADMIN_CHAT_ID
npx wrangler secret put MANUAL_KEY            # kata sandi buatan Anda untuk memicu manual via URL
npx wrangler deploy                           # mengunggah Worker + mendaftarkan 2 jadwal cron
```

- Saat `secret put` pertama ditanya *"create a new Worker?"* → jawab **Y**.
- Teks yang ditempel tidak terlihat. Itu normal, cukup tempel lalu tekan Enter.
- Output `deploy` menampilkan URL `https://gold-tracker-scheduler.<nama>.workers.dev` dan 2 *schedules*.

**H4. Uji**: buka di browser (ganti KEY dan URL):
- `https://gold-tracker-scheduler.<nama>.workers.dev/run?job=prices&key=KEY` → `{"ok": true ...}`. Di GitHub **Actions** muncul run baru dengan trigger `manual-url`.
- `.../watchdog?key=KEY&test=1` → Telegram menerima **🧪 Tes watchdog**.

**H5.** Kembali ke folder utama lalu simpan perubahan wrangler.toml:

```powershell
cd ..
git add .
git commit -m "Konfigurasi worker"
git push
```

Mulai sekarang job harga berjalan **otomatis** pukul 09:15, 13:15, 17:15, 21:15 WIB tanpa laptop, tanpa Claude.

---

## I. Sumber harga merek ✅ (sudah selesai, 18 Nov 2026)

Hasil probe: logammulia.com **diblokir** (403 Akamai, dari GitHub maupun laptop). galeri24.co.id **bisa diakses** (200) dan memuat 19 merek sekaligus. Parser Galeri24 sudah dibuat & diuji dengan halaman asli (Antam 1 g: jual Rp2.553.000 · buyback Rp2.281.000 per 17 Nov).
Catatan: buyback yang ditampilkan = buyback di outlet Galeri24/Pegadaian (bisa berbeda dari butik Logam Mulia).

---

## J. Checklist pengujian Fase 1

Centang setelah dicoba. Laporkan **hanya yang GAGAL**.

| ID | Cara uji | Hasil yang diharapkan | ✓ |
|---|---|---|---|
| T-01 | Buka web, login dengan email Anda | "Akses aktif ✓", harga tampil | ☐ |
| T-02 | Di web, isi email yang **tidak** diundang → Kirim | "Email ini belum diundang admin." | ☐ |
| T-03 | Undang email kedua (mis. `emailanda+tes@gmail.com`, Gmail mendukung "+"), login sekali. Lalu SQL: `update profiles set access_end = now() - interval '1 day' where email='emailanda+tes@gmail.com';` → refresh web akun tes | "Masa akses berakhir...", harga **tidak** tampil | ☐ |
| T-03b | SQL: `update profiles set access_end = null where email='emailanda+tes@gmail.com';` → refresh | Akses kembali aktif | ☐ |
| T-05 | Table Editor › price_snapshots | Kolom source, observed_at, slot, quality_status terisi | ☐ |
| T-06 | Actions › prices › Run workflow, isi **simulate_fail** = `xau` | Telegram ⚠️ partial "xau: simulasi gagal"; job_runs `partial`; harga XAU lama tetap ada | ☐ |
| T-11 | Run workflow prices **2× dalam jam yang sama**, lalu SQL: `select instrument, price_type, slot, count(*) from price_snapshots group by 1,2,3 having count(*) > 1;` | **0 baris** (tidak ada duplikat) | ☐ |
| T-14 | Setelah 3 hari: Supabase › **Usage**; GitHub › Settings › **Billing** › Actions; Cloudflare › Workers › Metrics | Semua jauh di bawah batas gratis | ☐ |
| T-15 | Actions › prices › **⋯ › Disable workflow**. Tunggu jadwal berikutnya + ±1,5 jam | Telegram: gagal memicu (dari Worker) **dan** "job harga belum sukses sejak..." (dari watchdog). Setelah itu **Enable workflow** lagi | ☐ |

---

## K. Laporan ke saya (format hemat)

```text
Task      : GT-001 Fase 1 PoC
Selesai   : A B C D E G H I J  (coret yang belum)
Gagal     : T-xx — pesan error / screenshot singkat
Catatan   : ...
```

---

## Masalah umum

| Gejala | Penyebab & solusi |
|---|---|
| Run **prices** merah: `KeyError: 'SUPABASE_URL'` | Secret belum dibuat/salah nama di E1 (huruf besar semua, persis) |
| `Supabase POST ... 401` | Secret key salah (mungkin terisi publishable key). Ulangi E1 |
| Telegram tidak menerima | Belum menekan Start di bot (D2) atau chat id salah (D3) |
| Link login membuka localhost | G3 belum diisi URL pages.dev |
| Email login tidak datang | Batas email bawaan Supabase; tunggu ±1 jam / cek spam |
| `wrangler` minta login berulang | Jalankan `npx wrangler login` lagi, pastikan akun Cloudflare yang sama |
| Worker `/run` → `ok:false, status 404` | `GH_OWNER`/`GH_REPO` salah di wrangler.toml, atau workflow belum ada di branch main |
| Worker `/run` → `status 403` | Token GitHub tanpa izin *Actions: Read and write* atau repo tidak dipilih |
| Secret bocor (mis. ter-commit) | Supabase › API Keys › buat secret key baru & hapus yang lama; BotFather `/revoke`; GitHub token › Regenerate. Lalu perbarui E1 & H3 |
