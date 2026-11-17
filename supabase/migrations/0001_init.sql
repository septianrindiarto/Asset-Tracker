-- =====================================================================
-- Gold Tracker — Migration 0001 (Fase 1 / PoC)
-- Isi   : tabel inti, fungsi akses, Row Level Security (RLS), data awal
-- Cara  : Supabase Dashboard › SQL Editor › New query › tempel › Run
-- Aman dijalankan ulang? TIDAK (pakai sekali di project baru).
-- =====================================================================

-- ---------- 1. PROFIL & AKSES PENGGUNA ----------
create table public.profiles (
  user_id      uuid primary key references auth.users(id) on delete cascade,
  email        text not null,
  display_name text,
  role         text not null default 'user'   check (role in ('admin','user','viewer')),
  status       text not null default 'active' check (status in ('active','suspended','revoked')),
  access_start timestamptz not null default now(),
  access_end   timestamptz,                    -- NULL = unlimited
  tg_chat_id   bigint,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);
comment on column public.profiles.access_end is 'NULL berarti akses unlimited';

-- ---------- 2. KONFIGURASI (semua parameter yang bisa diubah dari UI) ----------
create table public.app_config (
  key         text primary key,
  value       jsonb not null,
  description text,
  updated_at  timestamptz not null default now(),
  updated_by  uuid
);

-- ---------- 3. PRODUK EMAS ----------
create table public.products (
  id             text primary key,
  category       text not null check (category in ('bar','digital','jewelry','coin','related')),
  brand          text not null,
  name           text not null,
  pricing_method text not null check (pricing_method in ('api','scrape','manual','formula')),
  source_ref     jsonb,                -- mis. {"sell_url": "...", "buyback_url": "..."}
  active         boolean not null default true,
  sort_order     int not null default 100
);

-- ---------- 4. HARGA (snapshot terjadwal) ----------
create table public.price_snapshots (
  id             bigint generated always as identity primary key,
  instrument     text not null,        -- XAU_USD | USD_IDR | SPOT_IDR_G | <product id>
  price_type     text not null check (price_type in ('spot','sell','buyback','rate')),
  price          numeric(18,4) not null check (price > 0),
  currency       text not null,        -- USD | IDR
  unit           text not null,        -- troy_oz | gram | usd
  source         text not null,
  observed_at    timestamptz not null, -- waktu harga menurut sumber
  fetched_at     timestamptz not null default now(),
  slot           timestamptz not null, -- fetched_at dibulatkan ke jam → kunci anti-duplikat
  quality_status text not null default 'ok' check (quality_status in ('ok','needs_review','manual')),
  note           text,
  unique (instrument, price_type, source, slot)
);
create index price_snapshots_lookup on public.price_snapshots (instrument, price_type, observed_at desc);

-- ---------- 5. LOG JOB OTOMATIS ----------
create table public.job_runs (
  id           bigint generated always as identity primary key,
  job          text not null,
  trigger      text,
  started_at   timestamptz not null default now(),
  finished_at  timestamptz,
  status       text not null default 'running' check (status in ('running','success','partial','failed','skipped')),
  rows_written int not null default 0,
  detail       jsonb
);
create index job_runs_lookup on public.job_runs (job, started_at desc);

-- ---------- 6. FUNGSI AKSES ----------
-- has_access(): TRUE bila user login aktif & dalam masa berlaku.
create or replace function public.has_access()
returns boolean language sql stable security definer set search_path = public as $$
  select exists (
    select 1 from public.profiles p
    where p.user_id = auth.uid()
      and p.status = 'active'
      and p.access_start <= now()
      and (p.access_end is null or p.access_end > now())
  );
$$;

create or replace function public.is_admin()
returns boolean language sql stable security definer set search_path = public as $$
  select public.has_access() and exists (
    select 1 from public.profiles p where p.user_id = auth.uid() and p.role = 'admin'
  );
$$;

revoke execute on function public.has_access() from anon;
revoke execute on function public.is_admin() from anon;

-- Profil dibuat otomatis saat admin mengundang user (baris baru di auth.users).
create or replace function public.handle_new_user()
returns trigger language plpgsql security definer set search_path = public as $$
declare d int;
begin
  select (value #>> '{}')::int into d from public.app_config where key = 'default_access_days';
  d := coalesce(d, 30);
  insert into public.profiles (user_id, email, display_name, access_end)
  values (new.id, new.email, split_part(new.email, '@', 1),
          case when d <= 0 then null else now() + make_interval(days => d) end)
  on conflict (user_id) do nothing;
  return new;
end $$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

create or replace function public.touch_updated_at()
returns trigger language plpgsql as $$
begin new.updated_at := now(); return new; end $$;

create trigger profiles_touch before update on public.profiles
  for each row execute function public.touch_updated_at();
create trigger app_config_touch before update on public.app_config
  for each row execute function public.touch_updated_at();

-- ---------- 7. ROW LEVEL SECURITY ----------
-- Job Python memakai secret/service key → melewati RLS (hanya di server).
-- Browser memakai publishable/anon key → WAJIB lolos policy di bawah.
alter table public.profiles        enable row level security;
alter table public.app_config      enable row level security;
alter table public.products        enable row level security;
alter table public.price_snapshots enable row level security;
alter table public.job_runs        enable row level security;

-- Profil: user boleh melihat profilnya sendiri (agar UI bisa menampilkan "akses berakhir").
create policy profiles_read_own_or_admin on public.profiles
  for select to authenticated using (user_id = auth.uid() or public.is_admin());
create policy profiles_admin_update on public.profiles
  for update to authenticated using (public.is_admin()) with check (public.is_admin());

create policy config_read on public.app_config
  for select to authenticated using (public.has_access());
create policy config_admin_insert on public.app_config
  for insert to authenticated with check (public.is_admin());
create policy config_admin_update on public.app_config
  for update to authenticated using (public.is_admin()) with check (public.is_admin());

create policy products_read on public.products
  for select to authenticated using (public.has_access());
create policy products_admin_write on public.products
  for all to authenticated using (public.is_admin()) with check (public.is_admin());

create policy prices_read on public.price_snapshots
  for select to authenticated using (public.has_access());
create policy prices_admin_manual_insert on public.price_snapshots
  for insert to authenticated with check (public.is_admin() and quality_status = 'manual');

create policy job_runs_admin_read on public.job_runs
  for select to authenticated using (public.is_admin());

-- ---------- 8. DATA AWAL ----------
insert into public.app_config (key, value, description) values
  ('default_access_days', '30', 'Masa akses default user baru (hari). 0 = unlimited'),
  ('stale_hours', '{"spot": 8, "brand": 24}', 'Batas umur data sebelum dianggap basi'),
  ('quality', '{"max_jump_pct": 5}', 'Perubahan harga > X% dari data terakhir → needs_review'),
  ('sources', '{"xau": true, "fx": true, "antam": true, "ubs": false, "galeri24": false}', 'Sumber data aktif'),
  ('notify', '{"admin_each_run": true}', 'PoC: kirim ringkasan ke admin setiap job harga selesai'),
  ('schedule', '{"prices_wib": ["09:15","13:15","17:15","21:15"]}', 'Jadwal ambil harga (WIB) — referensi untuk pemicu');

insert into public.products (id, category, brand, name, pricing_method, source_ref, sort_order) values
  ('antam',     'bar',     'Antam',     'Logam Mulia Antam',        'scrape',  '{"sell_url":"https://www.logammulia.com/id/harga-emas-hari-ini","buyback_url":"https://www.logammulia.com/id/sell/gold"}', 10),
  ('ubs',       'bar',     'UBS',       'Emas UBS',                 'manual',  null, 20),
  ('galeri24',  'bar',     'Galeri24',  'Emas Galeri24',            'manual',  null, 30),
  ('pegadaian', 'digital', 'Pegadaian', 'Tabungan Emas Pegadaian',  'manual',  null, 40),
  ('jewelry',   'jewelry', 'Umum',      'Perhiasan (rumus kadar)',  'formula', null, 80),
  ('dinar',     'coin',    'Umum',      'Dinar / koin (rumus kadar)','formula', null, 90);
