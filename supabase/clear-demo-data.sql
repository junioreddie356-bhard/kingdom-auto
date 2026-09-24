-- Run once in Supabase SQL Editor if your database already contains old demo/test vehicles.
-- This clears inventory records so only vehicles you add through the admin panel appear.
delete from public.vehicles;
