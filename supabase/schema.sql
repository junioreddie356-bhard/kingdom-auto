-- Kingdom AutoMobile production database + image storage
create extension if not exists pgcrypto;

create table if not exists public.vehicles (
  id text primary key,
  slug text unique,
  title text,
  make text,
  model text,
  fuel text,
  price text,
  year text,
  mileage text,
  transmission text,
  engine_capacity text,
  vin text,
  condition text,
  history text,
  location text,
  status text not null default 'Available',
  featured boolean not null default false,
  price_range text,
  shipping_cost text,
  service_fees text,
  duty text,
  port_charges text,
  total_landed_cost text,
  images jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.vehicles
  add column if not exists slug text,
  add column if not exists title text,
  add column if not exists make text,
  add column if not exists model text,
  add column if not exists fuel text,
  add column if not exists price text,
  add column if not exists year text,
  add column if not exists mileage text,
  add column if not exists transmission text,
  add column if not exists engine_capacity text,
  add column if not exists vin text,
  add column if not exists condition text,
  add column if not exists history text,
  add column if not exists location text,
  add column if not exists status text default 'Available',
  add column if not exists featured boolean default false,
  add column if not exists price_range text,
  add column if not exists shipping_cost text,
  add column if not exists service_fees text,
  add column if not exists duty text,
  add column if not exists port_charges text,
  add column if not exists total_landed_cost text,
  add column if not exists images jsonb default '[]'::jsonb,
  add column if not exists created_at timestamptz not null default now(),
  add column if not exists updated_at timestamptz not null default now();

create table if not exists public.inquiries (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  vehicle text,
  vehicle_id text,
  name text,
  contact text,
  message text,
  status text default 'new',
  reply text,
  history jsonb default '[]'::jsonb
);

alter table public.inquiries
  add column if not exists created_at timestamptz not null default now(),
  add column if not exists vehicle text,
  add column if not exists vehicle_id text,
  add column if not exists name text,
  add column if not exists contact text,
  add column if not exists message text,
  add column if not exists status text default 'new',
  add column if not exists reply text,
  add column if not exists history jsonb default '[]'::jsonb;

-- The browser needs read-only access to inventory and inquiries can be created
-- by customers. Admin writes are performed by the server-side service role.
alter table public.vehicles enable row level security;
alter table public.inquiries enable row level security;

drop policy if exists "Public can read vehicles" on public.vehicles;
drop policy if exists "Public can manage vehicles" on public.vehicles;
drop policy if exists "Public can insert inquiries" on public.inquiries;
drop policy if exists "Public can update inquiries" on public.inquiries;
drop policy if exists "Public can read inquiries" on public.inquiries;

create policy "Public can read vehicles"
on public.vehicles for select using (true);

create policy "Public can insert inquiries"
on public.inquiries for insert with check (true);

-- Public Storage bucket: customers must be able to load the images whose URLs
-- are stored in vehicles.images. The service role performs uploads/deletes.
insert into storage.buckets (id, name, public)
values ('public', 'public', true)
on conflict (id) do update set public = true;

drop policy if exists "Public can read dealership images" on storage.objects;
create policy "Public can read dealership images"
on storage.objects for select
using (bucket_id = 'public');

create index if not exists vehicles_created_at_idx on public.vehicles (created_at desc);
create index if not exists vehicles_status_idx on public.vehicles (status);
create index if not exists vehicles_make_idx on public.vehicles (make);

create or replace function public.set_vehicle_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists vehicles_updated_at on public.vehicles;
create trigger vehicles_updated_at
before update on public.vehicles
for each row execute function public.set_vehicle_updated_at();
