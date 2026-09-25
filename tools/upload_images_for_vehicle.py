#!/usr/bin/env python3
"""Upload local image files for a vehicle to Supabase Storage and sync the vehicle record.

Usage:
  # dry-run (list files and targets)
  python tools/upload_images_for_vehicle.py --vehicle fzz949 --dir images_upload/fzz949 --dry-run

  # perform upload and sync
  python tools/upload_images_for_vehicle.py --vehicle fzz949 --dir images_upload/fzz949 --apply

Place image files locally under the directory you pass to `--dir`.
The script uses the same Supabase helpers as the admin API (`tools/admin_api.py`).
"""
import os, sys, argparse, mimetypes
from urllib.parse import quote
from datetime import datetime

try:
    from tools import admin_api
except Exception:
    # fallback import by path
    import importlib.util, os as _os
    admin_path = _os.path.join(_os.path.dirname(__file__), 'admin_api.py')
    spec = importlib.util.spec_from_file_location('tools.admin_api', admin_path)
    admin_api = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(admin_api)


def list_files(dirpath):
    if not os.path.isdir(dirpath):
        return []
    files = []
    for fname in sorted(os.listdir(dirpath)):
        path = os.path.join(dirpath, fname)
        if os.path.isfile(path):
            files.append(path)
    return files


def upload_files(vehicle_id, dirpath, apply=False):
    files = list_files(dirpath)
    if not files:
        print('No files found in', dirpath)
        return 1

    photos = []
    for path in files:
        fname = os.path.basename(path)
        safe_name = admin_api.sanitize_storage_filename(fname)
        storage_path = f'vehicles/{vehicle_id}/{safe_name}'
        ctype = mimetypes.guess_type(path)[0] or 'application/octet-stream'
        print('Will upload:', path, '->', storage_path, 'content-type:', ctype)

    if not apply:
        print('\nDry run complete. Re-run with --apply to perform uploads and sync.')
        return 0

    # perform uploads
    if not admin_api.supabase_enabled():
        print('Supabase configuration missing or disabled. Aborting.')
        return 1

    uploaded_urls = []
    for path in files:
        fname = os.path.basename(path)
        safe_name = admin_api.sanitize_storage_filename(fname)
        storage_path = f'vehicles/{vehicle_id}/{safe_name}'
        ctype = mimetypes.guess_type(path)[0] or 'application/octet-stream'
        try:
            with open(path, 'rb') as fh:
                admin_api.upload_file_to_supabase_storage(fh, storage_path, ctype)
            print('Uploaded', path)
            uploaded_urls.append(storage_path)
        except Exception as e:
            print('Upload failed for', path, '->', e)

    # build public URLs
    public_urls = admin_api.build_public_image_urls(uploaded_urls)
    print('\nPublic URLs:')
    for u in public_urls:
        print(' ', u)

    # merge with existing images (append)
    existing = admin_api.get_existing_vehicle_image_urls(vehicle_id)
    new_urls = [u for u in public_urls if u not in existing]
    final = existing + new_urls

    # sync
    resp = admin_api.sync_vehicle_photos(vehicle_id, final)
    if not resp.get('ok'):
        print('Failed to sync vehicle record:', resp.get('error'))
        return 1
    print('Vehicle record updated successfully.')
    return 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--vehicle', required=True, help='Vehicle id to associate files with')
    p.add_argument('--dir', required=True, help='Local directory containing image files to upload')
    p.add_argument('--apply', action='store_true', help='Perform uploads and sync (default: dry-run)')
    args = p.parse_args()
    return upload_files(args.vehicle, args.dir, apply=args.apply)


if __name__ == '__main__':
    sys.exit(main())
