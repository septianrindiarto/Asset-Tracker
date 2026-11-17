# Gold Tracker

Aplikasi web privat untuk memantau harga emas, mengelola semua jenis emas, rekomendasi beli/jual yang transparan, berita, dan notifikasi Telegram — berjalan di layanan gratis.

| Folder | Isi |
|---|---|
| `docs/` | Master document, mockup, rencana & panduan per fase |
| `supabase/migrations/` | Skema database, aturan akses (RLS), data awal |
| `jobs/` | Job Python terjadwal (harga, nanti berita & analisis) + tes |
| `worker/` | Cloudflare Worker: pemicu jadwal & watchdog |
| `web/` | Aplikasi web (Fase 1: PoC login + harga) |
| `setup/github-workflows/` | Workflow GitHub Actions (`prices`, `ci`, `probe`) — disalin ke `.github/workflows/` (lihat `setup/README.md`) |

Mulai dari **`docs/phases/PHASE1_GUIDE.md`**.

Status: **Fase 1 — PoC** (lihat `docs/phases/PHASE_PLAN.md`).
