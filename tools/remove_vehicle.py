#!/usr/bin/env python3
import argparse
import json
import os
import shutil
import urllib.request
from urllib.parse import quote


def remove_from_file(path, target_link):
    if not os.path.exists(path):
        return False
    with open(path, 'r', encoding='utf-8') as f:
        s = f.read()
    if target_link not in s:
        return False
    # naive: remove the article that contains the link
    start = s.find('<article', s.find(target_link)-200)
    if start == -1:
        return False
    end = s.find('</article>', start)
    if end == -1:
        return False
    end += len('</article>')
    new = s[:start] + s[end:]
    with open(path, 'w', encoding='utf-8') as f:
        f.write(new)
    return True


DEFAULT_SUPABASE_URL = 'https://invsxcmcczwckmfkynzk.supabase.co'
DEFAULT_SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImludnN4Y21jY3p3Y2ttZmt5bnprIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTA0NzE0NTEsImV4cCI6MjEwNjA0NzQ1MX0._zv75lSG6VIkk_Fxoh_aH25NRHO1DvXyqBJwaT_2-YM'


def delete_supabase_vehicle(vehicle_id):
    url = os.environ.get('SUPABASE_URL') or os.environ.get('SUPABASE_PROJECT_URL') or DEFAULT_SUPABASE_URL
    key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY') or os.environ.get('SUPABASE_SERVICE_KEY') or os.environ.get('SUPABASE_ANON_KEY') or os.environ.get('SUPABASE_PUBLIC_KEY') or 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImludnN4Y21jY3p3Y2ttZmt5bnprIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc5MDQ3MTQ1MSwiZXhwIjoyMTA2MDQ3NDUxfQ.F74Q3jOr4SWAG00Y9PbI1wS248ZatVEaiRWWtKfiZtI'

    delete_url = f"{url.rstrip('/')}/rest/v1/vehicles?id=eq.{quote(vehicle_id)}"
    req = urllib.request.Request(
        delete_url,
        method='DELETE',
        headers={
            'apikey': key,
            'Authorization': f'Bearer {key}',
            'Content-Type': 'application/json'
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            body = response.read().decode('utf-8', errors='ignore')
            return {'status': 'deleted', 'http_status': getattr(response, 'status', None), 'body': body}
    except Exception as exc:
        return {'status': 'error', 'reason': str(exc)}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--id', required=True)
    args = p.parse_args()
    repo_root = os.path.dirname(os.path.dirname(__file__))
    target = f'vehicle-{args.id}.html'
    target_path = os.path.join(repo_root, target)
    if os.path.exists(target_path):
        os.remove(target_path)
        print('Removed', target_path)
    else:
        print(target_path, 'not found')

    image_dir = os.path.join(repo_root, 'images', args.id)
    if os.path.isdir(image_dir):
        shutil.rmtree(image_dir, ignore_errors=True)
        print('Removed image directory', image_dir)

    changed = False
    for f in ('stock.html', 'index.html'):
        path = os.path.join(repo_root, f)
        if remove_from_file(path, target):
            print('Updated', f)
            changed = True
    if not changed:
        print('No references removed from stock/index')

    result = delete_supabase_vehicle(args.id)
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
