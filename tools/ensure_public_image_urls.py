#!/usr/bin/env python3
"""Ensure every vehicle.images entry is a fully-qualified Supabase public URL.

Usage:
  python tools/ensure_public_image_urls.py --dry-run
  python tools/ensure_public_image_urls.py --apply

This script imports helpers from `tools/admin_api.py` and will print a preview
of changes. Use `--apply` to perform PATCH updates to the `vehicles` table.
"""
import sys
import argparse
from urllib.parse import quote
from datetime import datetime

try:
    from tools import admin_api
except Exception as e:
    print('Could not import tools.admin_api:', e)
    sys.exit(1)


def main(apply=False):
    print('Fetching vehicles list...')
    res = admin_api.call_supabase('GET', '/vehicles?select=id,images')
    if not res.get('ok'):
        print('Supabase query failed:', res.get('error'))
        return 1
    rows = res.get('data') or []
    if not rows:
        print('No vehicles found.')
        return 0

    updates = []
    for row in rows:
        vid = row.get('id') or row.get('slug')
        images = row.get('images') if isinstance(row.get('images'), list) else []
        normalized = admin_api.build_public_image_urls(images)
        if normalized != images:
            updates.append((vid, images, normalized))

    if not updates:
        print('All vehicle image lists are already public URLs.')
        return 0

    print(f'Found {len(updates)} vehicles with non-public image entries:')
    for vid, old, new in updates:
        print('\nVehicle:', vid)
        print('  old:', old)
        print('  new:', new)

    if not apply:
        print('\nDry run complete. Re-run with --apply to perform updates.')
        return 0

    print('\nApplying updates...')
    for vid, old, new in updates:
        payload = {
            'images': new,
            'updated_at': datetime.utcnow().isoformat() + 'Z'
        }
        resp = admin_api.call_supabase('PATCH', f"/vehicles?id=eq.{quote(vid, safe='')}", payload)
        if not resp.get('ok'):
            print('Failed to update', vid, 'error:', resp.get('error'))
        else:
            print('Updated', vid)

    print('Done.')
    return 0


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--apply', action='store_true', help='Apply updates (default: dry-run only)')
    args = p.parse_args()
    sys.exit(main(apply=args.apply))
