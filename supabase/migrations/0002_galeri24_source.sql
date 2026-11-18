-- =====================================================================
-- Gold Tracker — Migration 0002 (Fase 1.1)
-- Sumber harga merek dipindah ke galeri24.co.id karena logammulia.com
-- memblokir akses otomatis (403 dari GitHub & dari laptop, 17 Nov 2026).
-- Cara: Supabase › SQL Editor › New query › tempel › Run (sekali saja).
-- =====================================================================

-- Antam, UBS, Galeri24 → diambil otomatis dari halaman Galeri24
update public.products set pricing_method = 'scrape',
  source_ref = '{"provider":"galeri24","vendor":"ANTAM"}'
  where id = 'antam';
update public.products set pricing_method = 'scrape',
  source_ref = '{"provider":"galeri24","vendor":"UBS"}'
  where id = 'ubs';
update public.products set pricing_method = 'scrape',
  source_ref = '{"provider":"galeri24","vendor":"GALERI 24"}'
  where id = 'galeri24';

-- Lotus Archi juga tersedia di halaman yang sama
insert into public.products (id, category, brand, name, pricing_method, source_ref, sort_order)
values ('lotus', 'bar', 'Lotus Archi', 'Emas Lotus Archi', 'scrape',
        '{"provider":"galeri24","vendor":"LOTUS ARCHI"}', 35)
on conflict (id) do update set pricing_method = excluded.pricing_method, source_ref = excluded.source_ref;

-- Saklar sumber kini per penyedia (provider), bukan per produk
update public.app_config
  set value = '{"xau": true, "fx": true, "galeri24": true, "logammulia": false}',
      description = 'Sumber data aktif per penyedia'
  where key = 'sources';

-- Catatan untuk UI: buyback di sini = buyback outlet Galeri24/Pegadaian
insert into public.app_config (key, value, description) values
  ('price_notes', '{"galeri24": "Harga jual & buyback di outlet Galeri24/Pegadaian; buyback butik Logam Mulia bisa berbeda."}',
   'Keterangan sumber harga yang ditampilkan ke user')
on conflict (key) do nothing;
