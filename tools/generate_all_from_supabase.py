#!/usr/bin/env python3
"""Generate static vehicle pages by fetching inventory from Supabase and
invoking the existing `generate_vehicle.py` for each record.

Usage:
  python tools/generate_all_from_supabase.py --supabase-url URL --service-key KEY

If env vars SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are present they'll be used.
"""
import os
import sys
import json
import argparse
import subprocess
from urllib.parse import quote_plus

try:
    import requests
except Exception:
    print('Please install requests: pip install requests')
    raise


def get_supabase_rows(url, key, table='vehicles'):
    headers = {
        'apikey': key,
        'Authorization': f'Bearer {key}',
        'Accept': 'application/json'
    }
    endpoint = url.rstrip('/') + f'/rest/v1/{table}?select=*'
    resp = requests.get(endpoint, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--supabase-url')
    p.add_argument('--service-key')
    p.add_argument('--table', default='vehicles')
    args = p.parse_args()

    supabase_url = args.supabase_url or os.environ.get('SUPABASE_URL')
    service_key = args.service_key or os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
    if not supabase_url or not service_key:
        print('SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required (env or args)')
        sys.exit(2)

    print('Fetching vehicles from Supabase...')
    rows = get_supabase_rows(supabase_url, service_key, table=args.table)
    print(f'Fetched {len(rows)} rows')

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    gen_script = os.path.join(repo_root, 'tools', 'generate_vehicle.py')
    if not os.path.exists(gen_script):
        print('generate_vehicle.py not found in tools/; aborting')
        sys.exit(1)

    failures = []
    for r in rows:
        vid = r.get('id') or r.get('slug') or r.get('vehicle_id')
        if not vid:
            print('Skipping record without id')
            continue
        title = r.get('title') or r.get('name') or ''
        price = str(r.get('price') or r.get('price_range') or '')
        year = str(r.get('year') or '')
        transmission = r.get('transmission') or ''
        fuel = r.get('fuel') or ''
        mileage = str(r.get('mileage') or '')
        vin = r.get('vin') or ''
        condition = r.get('condition') or ''
        history = r.get('history') or ''
        location = r.get('location') or ''
        brand = r.get('brand') or r.get('make') or ''
        year_model = r.get('year') or ''
        images = r.get('images') or []
        images_arg = ','.join(images) if isinstance(images, list) else images or ''

        cmd = [sys.executable, gen_script,
               '--id', str(vid),
               '--title', title,
               '--price', price,
               '--year', year,
               '--transmission', transmission,
               '--fuel', fuel,
               '--mileage', mileage,
               '--vin', vin,
               '--condition', condition,
               '--history', history,
               '--location', location,
               '--brand', brand,
               '--year-model', year_model,
               '--images', images_arg]

        print('Generating', vid)
        try:
            proc = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True, timeout=60)
            if proc.returncode != 0:
                print('Generation failed for', vid, proc.returncode)
                print(proc.stdout)
                print(proc.stderr)
                failures.append((vid, proc.stdout + proc.stderr))
        except Exception as e:
            print('Exception generating', vid, e)
            failures.append((vid, str(e)))

    if failures:
        print('Completed with failures:', len(failures))
        for v, out in failures:
            print('FAILED', v, out[:400])
        sys.exit(1)

    # Commit generated files
    try:
        subprocess.run(['git', 'add', '--all'], cwd=repo_root, check=True)
        subprocess.run(['git', 'commit', '-m', 'chore: generate vehicle pages from Supabase'], cwd=repo_root, check=True)
        subprocess.run(['git', 'push'], cwd=repo_root, check=True)
        print('Committed and pushed generated pages')
    except subprocess.CalledProcessError as e:
        print('Git commit/push failed or nothing to commit:', e)


if __name__ == '__main__':
    main()
