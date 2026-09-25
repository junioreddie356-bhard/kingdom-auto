#!/usr/bin/env python3
from flask import Flask, request, jsonify
import os, json, hashlib, binascii, shutil, re
from urllib import request as urllib_request
from urllib import error as urllib_error
from urllib.parse import quote
from werkzeug.utils import secure_filename
import tempfile, mimetypes
try:
    from PIL import Image
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

app = Flask(__name__)

CREDS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'admin', 'creds.json')
IMAGES_ROOT = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'images')

ALLOWED_EXT = {
    'png','jpg','jpeg','gif','webp','svg','bmp','avif','jfif','heic','heif','tif','tiff','ico'
}


def get_request_files():
    candidates = ['files', 'files[]', 'file', 'images', 'images[]']
    seen = set()
    files = []
    for key in candidates:
        for uploaded in list(request.files.getlist(key)):
            if uploaded and uploaded.filename and uploaded.filename not in seen:
                files.append(uploaded)
                seen.add(uploaded.filename)
    if files:
        return files

    for uploaded in request.files.values():
        if uploaded and uploaded.filename and uploaded.filename not in seen:
            files.append(uploaded)
            seen.add(uploaded.filename)
    return files


def allowed_filename(filename):
    if not filename or not isinstance(filename, str):
        return False
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT

def verify_password(password, creds):
    if not creds:
        return False
    if 'hash' in creds and 'salt' in creds:
        salt = binascii.unhexlify(creds['salt'])
        iters = int(creds.get('iterations', 100000))
        dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iters, dklen=32)
        return binascii.hexlify(dk).decode('ascii') == creds['hash']
    # fallback plaintext
    return creds.get('password') == password


def get_allowed_admin_origin():
    candidates = [
        os.environ.get('ADMIN_ALLOWED_ORIGIN'),
        os.environ.get('SITE_URL'),
        os.environ.get('VERCEL_PROJECT_PRODUCTION_URL'),
        'https://kingdom-auto-mobile.vercel.app',
        'https://www.kingdom-auto-mobile.vercel.app',
        'http://localhost:8000',
        'http://127.0.0.1:8000'
    ]
    seen = set()
    for candidate in candidates:
        if not candidate:
            continue
        cleaned = candidate.strip().rstrip('/')
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
    return sorted(seen)


@app.before_request
def enforce_production_admin_security():
    if request.method == 'OPTIONS':
        return None

    path = request.path.lower()
    is_admin_route = path.startswith('/admin') or path.startswith('/api/admin')
    if not is_admin_route:
        return None

    if os.environ.get('VERCEL') or os.environ.get('VERCEL_ENV'):
        proto = request.headers.get('X-Forwarded-Proto', request.scheme)
        if proto != 'https':
            resp = jsonify({'error': 'HTTPS required in production'}), 403
            return resp


@app.after_request
def apply_admin_security_headers(resp):
    if request.path.lower().startswith('/admin') or request.path.lower().startswith('/api/admin'):
        origin = request.headers.get('Origin')
        allowed = get_allowed_admin_origin()
        if origin and origin.rstrip('/') in allowed:
            resp.headers['Access-Control-Allow-Origin'] = origin
            resp.headers['Access-Control-Allow-Credentials'] = 'true'
            resp.headers['Vary'] = 'Origin'
        elif allowed:
            resp.headers['Access-Control-Allow-Origin'] = allowed[0]
            resp.headers['Access-Control-Allow-Credentials'] = 'true'
            resp.headers['Vary'] = 'Origin'
        else:
            resp.headers['Access-Control-Allow-Origin'] = 'null'
        resp.headers['X-Frame-Options'] = 'DENY'
        resp.headers['X-Content-Type-Options'] = 'nosniff'
        resp.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return resp


def write_creds(username, password, iterations=100000):
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations, dklen=32)
    data = {
        'username': username,
        'salt': binascii.hexlify(salt).decode('ascii'),
        'hash': binascii.hexlify(dk).decode('ascii'),
        'iterations': iterations
    }
    os.makedirs(os.path.dirname(CREDS_PATH), exist_ok=True)
    with open(CREDS_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    return data


DEFAULT_SUPABASE_URL = 'https://spckgpxzcxvogjamfsqr.supabase.co'
DEFAULT_SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNwY2tncHh6Y3h2b2dqYW1mc3FyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODg1NDg2NjQsImV4cCI6MjEwNDEyNDY2NH0.h52gkl9ms2vT785SUTmAT_IDzNfaa2jUpepEGIW0yZw'


def get_supabase_settings():
    return {
        'url': (os.environ.get('SUPABASE_URL') or os.environ.get('SUPABASE_PROJECT_URL') or DEFAULT_SUPABASE_URL).strip().rstrip('/'),
        'service_key': (os.environ.get('SUPABASE_SERVICE_ROLE_KEY') or os.environ.get('SUPABASE_SERVICE_KEY') or os.environ.get('SUPABASE_KEY') or DEFAULT_SUPABASE_ANON_KEY).strip(),
        'anon_key': (os.environ.get('SUPABASE_ANON_KEY') or os.environ.get('SUPABASE_PUBLIC_KEY') or DEFAULT_SUPABASE_ANON_KEY).strip()
    }


def supabase_enabled():
    cfg = get_supabase_settings()
    return bool(cfg['url'] and (cfg['service_key'] or cfg['anon_key']))


def get_public_storage_base_url():
    # Resolve and validate the storage bucket before returning the public base URL.
    cfg = get_supabase_settings()
    bucket = resolve_storage_bucket()
    if bucket and str(bucket).lower() == 'public':
        return cfg['url'].rstrip('/') + '/storage/v1/object/public'
    return cfg['url'].rstrip('/') + f'/storage/v1/object/public/{bucket}'


def sanitize_storage_filename(name: str) -> str:
    """Return a safe filename for Supabase storage: use werkzeug.secure_filename
    then replace spaces and multiple underscores. Keeps the original extension."""
    if not name or not isinstance(name, str):
        return name
    # Use secure_filename to remove unsafe chars
    safe = secure_filename(name)
    # Replace spaces/percent encodings with underscore and collapse duplicates
    safe = re.sub(r"[\s%]+", '_', safe)
    safe = re.sub(r'_+', '_', safe)
    return safe


def build_public_image_urls(paths):
    if not paths:
        return []
    base = get_public_storage_base_url()
    urls = []
    for path in paths:
        normalized = str(path).strip().lstrip('/')
        if not normalized:
            continue

        if normalized.startswith('http://') or normalized.startswith('https://'):
            if '/storage/v1/object/public/' in normalized:
                normalized = normalized.split('/storage/v1/object/public/', 1)[1]
            normalized = normalized.strip('/').replace('public/', '', 1) if normalized.strip('/').startswith('public/') else normalized.strip('/')
            if normalized.startswith('images/') or normalized.startswith('vehicles/'):
                urls.append(base + '/' + quote(normalized, safe='/'))
            else:
                urls.append(base + '/' + quote(normalized, safe='/'))
            continue

        if normalized.startswith('storage/v1/object/'):
            normalized = normalized.replace('storage/v1/object/public/', '', 1)

        normalized = normalized.replace('public/', '', 1) if normalized.startswith('public/') else normalized
        normalized = normalized.replace('images/', '', 1) if normalized.startswith('images/') else normalized
        normalized = normalized.strip('/')
        if not normalized:
            continue

        ext = os.path.splitext(normalized.split('?', 1)[0].split('#', 1)[0])[1].lower().lstrip('.')
        if ext in ALLOWED_EXT:
            if normalized.startswith(('images/', '../images/', './images/')):
                urls.append(normalized)
            else:
                urls.append(base + '/' + quote(normalized, safe='/'))
            continue

        urls.append(base + '/' + quote(normalized, safe='/'))
    return urls


def get_existing_vehicle_image_urls(vehicle_id):
    """Return existing gallery URLs from the database and the local filesystem."""
    if not vehicle_id:
        return []

    urls = []
    existing = call_supabase('GET', f"/vehicles?id=eq.{quote(vehicle_id, safe='')}&select=images")
    rows = existing.get('data') if existing.get('ok') else []
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict):
                continue
            image_list = row.get('images', [])
            if isinstance(image_list, list):
                urls.extend(image_list)

    target_dir = os.path.join(IMAGES_ROOT, vehicle_id)
    if os.path.isdir(target_dir):
        for filename in sorted(os.listdir(target_dir)):
            if not allowed_filename(filename) or filename.lower() == 'thumb.jpg':
                continue
            urls.extend(build_public_image_urls([
                os.path.join('vehicles', vehicle_id, filename).replace('\\', '/')
            ]))

    seen = set()
    ordered = []
    for url in urls:
        value = str(url).strip()
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


# Cache for resolved bucket name to avoid repeated network calls
_RESOLVED_STORAGE_BUCKET = None


def bucket_exists(bucket_name):
    cfg = get_supabase_settings()
    key = cfg.get('service_key') or cfg.get('anon_key')
    if not cfg['url'] or not key or not bucket_name:
        return False
    endpoint = cfg['url'].rstrip('/') + f'/storage/v1/bucket/{bucket_name}'
    req = urllib_request.Request(endpoint, headers={
        'apikey': key,
        'Authorization': f'Bearer {key}'
    }, method='GET')
    try:
        with urllib_request.urlopen(req, timeout=10) as resp:
            code = getattr(resp, 'status', None) or resp.getcode()
            return int(code) == 200
    except urllib_error.HTTPError as he:
        if getattr(he, 'code', None) == 404:
            return False
        return False
    except Exception:
        return False


def resolve_storage_bucket():
    """Return a validated storage bucket name. Tries environment then common defaults.
    Caches the result in-module for subsequent calls."""
    global _RESOLVED_STORAGE_BUCKET
    if _RESOLVED_STORAGE_BUCKET:
        return _RESOLVED_STORAGE_BUCKET

    env_bucket = (os.environ.get('SUPABASE_STORAGE_BUCKET') or os.environ.get('SUPABASE_BUCKET') or '').strip()
    candidates = []
    if env_bucket:
        candidates.append(env_bucket)
    # common fallback candidates
    candidates.extend(['public', 'images'])

    for c in candidates:
        if not c:
            continue
        try:
            if bucket_exists(c):
                _RESOLVED_STORAGE_BUCKET = c
                return c
        except Exception:
            continue

    # final fallback: use env or 'public'
    _RESOLVED_STORAGE_BUCKET = env_bucket or 'public'
    return _RESOLVED_STORAGE_BUCKET


def upload_file_to_supabase_storage(file_obj, storage_path, content_type='application/octet-stream'):
    cfg = get_supabase_settings()
    key = cfg.get('service_key') or cfg.get('anon_key')
    bucket = resolve_storage_bucket()
    if not cfg['url'] or not key:
        raise RuntimeError('Supabase not configured')

    endpoint = cfg['url'].rstrip('/') + f'/storage/v1/object/{bucket}/{storage_path.lstrip("/")}'
    payload = file_obj.read() if hasattr(file_obj, 'read') else file_obj
    req = urllib_request.Request(endpoint, data=payload, headers={
        'apikey': key,
        'Authorization': f'Bearer {key}',
        'Content-Type': content_type,
        # Replacing a gallery can reuse a filename. Storage must overwrite it.
        'x-upsert': 'true',
    }, method='PUT')
    with urllib_request.urlopen(req, timeout=30) as resp:
        return resp.read()


def call_supabase(method, path, payload=None):
    cfg = get_supabase_settings()
    key = cfg['service_key'] or cfg['anon_key']
    if not cfg['url'] or not key:
        return {'source': 'local', 'ok': True}

    endpoint = f"{cfg['url']}/rest/v1{path}"
    headers = {
        'apikey': key,
        'Authorization': f"Bearer {key}",
        'Content-Type': 'application/json',
        'Prefer': 'resolution=merge-duplicates'
    }
    body = None if payload is None else json.dumps(payload).encode('utf-8')
    req = urllib_request.Request(endpoint, data=body, headers=headers, method=method.upper())

    try:
        with urllib_request.urlopen(req, timeout=20) as response:
            response_text = response.read().decode('utf-8')
            if not response_text:
                return {'source': 'supabase', 'ok': True}
            try:
                return {'source': 'supabase', 'ok': True, 'data': json.loads(response_text)}
            except Exception:
                return {'source': 'supabase', 'ok': True, 'data': response_text}
    except Exception as exc:
        return {'source': 'supabase', 'ok': False, 'error': str(exc)}


def normalize_vehicle_record(vid, title, brand, year_model, price, mileage, transmission, fuel, vin, condition, history, location, images, engine_capacity='', price_range='', shipping_cost='', service_fees='', duty='', port_charges='', total_landed_cost='', status='Available', featured=False):
    title_value = (title or '').strip() or f"{brand or 'Vehicle'} {year_model or ''}".strip() or vid
    normalized_images = []
    if images:
        for image in images:
            if not image:
                continue
            text = str(image).strip()
            if not text:
                continue
            if text.startswith('http://') or text.startswith('https://'):
                normalized_images.append(text)
            elif text.startswith('images/'):
                normalized_images.extend(build_public_image_urls([text]))
            else:
                normalized_images.append(text)
    payload = {
        'id': vid,
        'slug': vid,
        'title': title_value,
        'make': brand or '',
        'model': title_value or year_model or '',
        'price': price or 'Contact for pricing',
        'year': year_model or '',
        'mileage': mileage or '',
        'transmission': transmission or '',
        'fuel': fuel or '',
        'engine_capacity': engine_capacity or '',
        'location': location or '',
        'status': status or 'Available',
        'featured': bool(featured),
        'price_range': price_range or '',
        'shipping_cost': shipping_cost or '',
        'service_fees': service_fees or '',
        'duty': duty or '',
        'port_charges': port_charges or '',
        'total_landed_cost': total_landed_cost or '',
        'updated_at': __import__('datetime').datetime.utcnow().isoformat() + 'Z'
    }
    if vin:
        payload['vin'] = vin
    if condition:
        payload['condition'] = condition
    if history:
        payload['history'] = history
    if normalized_images:
        payload['images'] = normalized_images
    return payload


def sync_vehicle_to_supabase(vehicle_record):
    if not vehicle_record:
        return {'source': 'local', 'ok': True}
    if not supabase_enabled():
        return {'source': 'local', 'ok': True}
    return call_supabase('POST', '/vehicles?on_conflict=id', [vehicle_record])


def delete_vehicle_from_supabase(vehicle_id):
    if not vehicle_id or not supabase_enabled():
        return {'source': 'local', 'ok': True}
    return call_supabase('DELETE', f"/vehicles?id=eq.{quote(vehicle_id, safe='')}")


def valid_vehicle_id(vehicle_id):
    """Keep uploads inside the configured images directory."""
    return bool(vehicle_id and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,99}', vehicle_id))


def photo_record(vehicle_id, filename, content_type, size):
    """The API representation of a vehicle photo.

    `url` is the public asset URL while the remaining fields are useful to the
    dashboard without requiring it to infer information from the URL.
    """
    path = f'vehicles/{vehicle_id}/{filename}'
    return {
        'url': build_public_image_urls([path])[0],
        'filename': filename,
        'path': path,
        'contentType': content_type or mimetypes.guess_type(filename)[0] or 'application/octet-stream',
        'size': size,
        'uploadedAt': __import__('datetime').datetime.utcnow().isoformat() + 'Z'
    }


def sync_vehicle_photos(vehicle_id, image_urls):
    """Update only images, leaving all existing vehicle details intact."""
    # Ensure we store fully-qualified public URLs in the DB
    safe_images = build_public_image_urls(image_urls)
    existing = call_supabase('GET', f"/vehicles?id=eq.{quote(vehicle_id, safe='')}&select=id")
    payload = {
        'images': safe_images,
        'updated_at': __import__('datetime').datetime.utcnow().isoformat() + 'Z'
    }
    if existing.get('ok') and existing.get('data'):
        return call_supabase('PATCH', f"/vehicles?id=eq.{quote(vehicle_id, safe='')}", payload)
    record = {
        'id': vehicle_id,
        'slug': vehicle_id,
        'title': vehicle_id.replace('-', ' ').title(),
        'price': 'Contact for pricing',
        'images': safe_images,
        'updated_at': __import__('datetime').datetime.utcnow().isoformat() + 'Z'
    }
    return sync_vehicle_to_supabase(record)

@app.route('/api/admin/rotate', methods=['POST', 'OPTIONS'])
def api_rotate_alias():
    return rotate()

@app.route('/admin/rotate', methods=['POST', 'OPTIONS'])
def rotate():
    # simple CORS support for local dev
    if request.method == 'OPTIONS':
        resp = jsonify({'ok': True})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return resp

    body = request.get_json() or {}
    current = body.get('current_password')
    new_user = body.get('new_username')
    new_pass = body.get('new_password')
    if not (current and new_user and new_pass):
        resp = jsonify({'error': 'current_password, new_username and new_password required'})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp, 400
    # load existing creds
    if os.path.exists(CREDS_PATH):
        with open(CREDS_PATH, 'r', encoding='utf-8') as f:
            creds = json.load(f)
    else:
        creds = None

    if not verify_password(current, creds):
        resp = jsonify({'error':'current password invalid'})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp, 403

    new = write_creds(new_user, new_pass)
    resp = jsonify({'ok': True, 'creds': {'username': new['username']}})
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp


# aliases to be tolerant of trailing slashes or alternate paths
@app.route('/admin/upload/', methods=['POST', 'OPTIONS', 'GET'])
@app.route('/upload', methods=['POST', 'OPTIONS', 'GET'])
@app.route('/api/admin/upload', methods=['POST', 'OPTIONS', 'GET'])
@app.route('/api/admin/upload/', methods=['POST', 'OPTIONS', 'GET'])
def upload_alias():
    return upload()


@app.route('/admin/upload', methods=['POST', 'OPTIONS'])
def upload():
    if request.method == 'OPTIONS':
        resp = jsonify({'ok': True})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return resp

    current = (request.form.get('current_password') or '').strip()
    if not current:
        return jsonify({'error': 'current_password required'}), 400
    creds = None
    if os.path.exists(CREDS_PATH):
        with open(CREDS_PATH, 'r', encoding='utf-8') as f:
            creds = json.load(f)
    if not verify_password(current, creds):
        return jsonify({'error': 'current password invalid'}), 403

    vehicle_id = (request.form.get('id') or '').strip()
    mode = (request.form.get('mode') or 'append').lower()
    if not valid_vehicle_id(vehicle_id):
        return jsonify({'error': 'A valid vehicle ID is required.'}), 400
    if mode not in ('append', 'replace'):
        return jsonify({'error': 'mode must be append or replace'}), 400

    files = get_request_files()
    if not files:
        return jsonify({'error': 'Select at least one image to upload.'}), 400
    invalid = [f.filename for f in files if not allowed_filename(f.filename)]
    if invalid:
        return jsonify({'error': 'Only supported image files can be uploaded.', 'invalidFiles': invalid}), 400

    # Stage first so a failed replacement never destroys the current gallery.
    staging_dir = tempfile.mkdtemp(prefix='kingdom-photo-')
    photos = []
    backup_dir = None
    try:
        for index, uploaded in enumerate(files, start=1):
            filename = sanitize_storage_filename(uploaded.filename)
            if not filename:
                continue
            # Prevent same-name files in a multi-file selection from overwriting.
            stem, ext = os.path.splitext(filename)
            filename = filename if index == 1 or not os.path.exists(os.path.join(staging_dir, filename)) else f'{stem}-{index}{ext}'
            staged_path = os.path.join(staging_dir, filename)
            uploaded.save(staged_path)
            photos.append(photo_record(vehicle_id, filename, uploaded.content_type, os.path.getsize(staged_path)))
        if not photos:
            return jsonify({'error': 'No valid image files were received.'}), 400

        is_serverless = bool(os.environ.get('VERCEL') or os.environ.get('VERCEL_ENV'))
        if is_serverless:
            # Vercel's filesystem is temporary. Persist each image before adding
            # its public URL to the vehicle record, otherwise the dashboard would
            # show a broken image after the request ends.
            if not supabase_enabled():
                return jsonify({'error': 'Persistent image storage is not configured.'}), 503
            try:
                for photo in photos:
                    staged_path = os.path.join(staging_dir, photo['filename'])
                    with open(staged_path, 'rb') as image_file:
                        upload_file_to_supabase_storage(image_file, photo['path'], photo['contentType'])
            except Exception as exc:
                return jsonify({'error': 'Image upload to persistent storage failed.', 'details': str(exc)}), 502
        else:
            target_dir = os.path.join(IMAGES_ROOT, vehicle_id)
            if mode == 'replace' and os.path.isdir(target_dir):
                # Retain a rollback copy until the database points at the new gallery.
                backup_dir = tempfile.mkdtemp(prefix=f'{vehicle_id}-backup-', dir=IMAGES_ROOT)
                os.rmdir(backup_dir)
                shutil.move(target_dir, backup_dir)
            os.makedirs(target_dir, exist_ok=True)
            for photo in photos:
                shutil.move(os.path.join(staging_dir, photo['filename']), os.path.join(target_dir, photo['filename']))

            # Keep a small local thumbnail for existing media views.
            if PIL_AVAILABLE:
                try:
                    first = os.path.join(target_dir, photos[0]['filename'])
                    img = Image.open(first)
                    img.thumbnail((800, 600))
                    img.convert('RGB').save(os.path.join(target_dir, 'thumb.jpg'), 'JPEG', quality=85)
                except Exception:
                    pass

        new_urls = [photo['url'] for photo in photos]
        # Ensure any newly produced URLs are normalized to full public URLs
        try:
            new_urls = build_public_image_urls(new_urls)
        except Exception:
            # fallback: keep original list
            pass
        if mode == 'append':
            old_urls = [url for url in get_existing_vehicle_image_urls(vehicle_id) if url not in new_urls]
            new_urls = old_urls + new_urls
        sync = sync_vehicle_photos(vehicle_id, new_urls)
        if not sync.get('ok', True):
            if backup_dir and os.path.isdir(backup_dir):
                backup_target = os.path.join(backup_dir, vehicle_id)
                if os.path.isdir(backup_target):
                    shutil.rmtree(target_dir, ignore_errors=True)
                    shutil.move(backup_target, target_dir)
                backup_dir = None
            return jsonify({'error': 'Photos saved but the vehicle record could not be updated.', 'details': sync.get('error')}), 502
        resp = jsonify({'ok': True, 'mode': mode, 'photos': photos, 'files': new_urls, 'count': len(photos)})
    finally:
        shutil.rmtree(staging_dir, ignore_errors=True)
        if backup_dir and os.path.isdir(backup_dir):
            shutil.rmtree(backup_dir, ignore_errors=True)
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp


@app.route('/admin/create_vehicle', methods=['POST', 'OPTIONS'])
@app.route('/api/admin/create_vehicle', methods=['POST', 'OPTIONS'])
def create_vehicle_alias():
    return create_vehicle()

@app.route('/admin/create_vehicle/', methods=['POST', 'OPTIONS'])
def create_vehicle():
    if request.method == 'OPTIONS':
        resp = jsonify({'ok': True})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return resp

    # authenticate using current password in form
    current = request.form.get('current_password') or (request.json and request.json.get('current_password'))
    if not current:
        resp = jsonify({'error':'current_password required'})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp, 400

    # load existing creds
    if os.path.exists(CREDS_PATH):
        with open(CREDS_PATH, 'r', encoding='utf-8') as f:
            creds = json.load(f)
    else:
        creds = None
    if not verify_password(current, creds):
        resp = jsonify({'error':'current password invalid'})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp, 403

    # gather metadata
    vid = request.form.get('id')
    brand = request.form.get('brand','').strip()
    title = (request.form.get('title') or request.form.get('name') or '').strip()
    year_model = request.form.get('year_model','').strip()
    engine_capacity = request.form.get('engine_capacity','').strip()
    price = request.form.get('price','').strip()
    price_range = request.form.get('price_range','').strip()
    shipping_cost = request.form.get('shipping_cost','').strip()
    service_fees = request.form.get('service_fees','').strip()
    duty = request.form.get('duty','').strip()
    port_charges = request.form.get('port_charges','').strip()
    total_landed_cost = request.form.get('total_landed_cost','').strip()
    current_location = request.form.get('current_location','').strip() or request.form.get('location','Tamale')
    year = request.form.get('year','').strip() or year_model
    transmission = request.form.get('transmission','')
    fuel = request.form.get('fuel','')
    mileage = request.form.get('mileage','')
    vin = request.form.get('vin','')
    condition = request.form.get('condition','')
    history = request.form.get('history','')
    status = request.form.get('status','Available').strip() or 'Available'
    featured = (request.form.get('featured','') or '').lower() in ('1','true','yes','on')
    location = current_location

    if not vid:
        resp = jsonify({'error':'id required'})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp, 400

    if not title:
        title = ' '.join(part for part in [brand, year_model] if part).strip() or 'New Vehicle'

    if not price and price_range:
        price = price_range

    # save files similar to upload
    files = get_request_files()
    saved = []
    file_write_ok = True
    try:
        target_dir = os.path.join(IMAGES_ROOT, vid)
        os.makedirs(target_dir, exist_ok=True)
        for f in files:
            filename = secure_filename(f.filename)
            if not filename:
                continue
            safe_filename = sanitize_storage_filename(filename)
            out_path = os.path.join(target_dir, safe_filename)
            f.save(out_path)
            saved.append(f'vehicles/{vid}/{safe_filename}')
            if PIL_AVAILABLE and allowed_filename(filename):
                try:
                    img = Image.open(out_path)
                    img.thumbnail((800,600))
                    thumb_path = os.path.join(target_dir, 'thumb.jpg')
                    img.convert('RGB').save(thumb_path, 'JPEG', quality=85)
                except Exception:
                    pass
    except Exception as exc:
        file_write_ok = False
        print(f'Create vehicle file write failed in serverless environment: {exc}')

    # Build images argument for generator: use saved paths or existing images in folder
    images_arg = ''
    # If the client passed explicit public image URLs, prefer them
    try:
        if request.form.get('images'):
            # images can be a JSON array string
            raw = request.form.get('images')
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list) and parsed:
                    image_paths_for_record = parsed
            except Exception:
                # maybe a comma separated list
                image_paths_for_record = [p.strip() for p in raw.split(',') if p.strip()]
    except Exception:
        pass
    try:
        if saved:
            images_arg = ','.join(saved)
        else:
            target_dir = os.path.join(IMAGES_ROOT, vid)
            existing = [os.path.join('vehicles', vid, fn).replace('\\','/') for fn in os.listdir(target_dir) if allowed_filename(fn)]
            images_arg = ','.join(existing)
    except Exception:
        images_arg = ''

    # If client provided explicit public image URLs, keep them. Otherwise derive from saved files or existing folder.
    if not ('image_paths_for_record' in locals() and image_paths_for_record):
        image_paths_for_record = []
        if saved:
            image_paths_for_record = build_public_image_urls([
                os.path.join('vehicles', vid, os.path.basename(path)).replace('\\', '/')
                for path in saved
            ])
        if not image_paths_for_record and os.path.isdir(os.path.join(IMAGES_ROOT, vid)):
            image_paths_for_record = build_public_image_urls([
                os.path.join('vehicles', vid, fn).replace('\\', '/')
                for fn in os.listdir(os.path.join(IMAGES_ROOT, vid))
                if allowed_filename(fn)
            ])
    vehicle_record = normalize_vehicle_record(
        vid,
        title,
        brand,
        year_model,
        price or price_range or 'Contact for pricing',
        mileage,
        transmission,
        fuel,
        vin,
        condition,
        history,
        current_location,
        image_paths_for_record,
        engine_capacity,
        price_range,
        shipping_cost,
        service_fees,
        duty,
        port_charges,
        total_landed_cost,
        status,
        featured
    )

    # Ensure the vehicle_record.images are full public URLs before syncing
    try:
        if 'images' in vehicle_record and vehicle_record['images']:
            vehicle_record['images'] = build_public_image_urls(vehicle_record['images'])
    except Exception:
        pass

    import subprocess, sys
    repo_root = os.path.dirname(os.path.dirname(__file__))
    # In serverless environments (Vercel), attempt generation in a temp dir and upload to Supabase Storage.
    is_vercel = bool(os.environ.get('VERCEL') or os.environ.get('VERCEL_ENV'))
    ok = True
    out = ''
    if is_vercel:
        tmp = None
        try:
            tmp = tempfile.mkdtemp(prefix=f'vehicle-{vid}-')
            images_list = []
            if saved:
                # saved paths are relative to repo root; copy referenced files into tmp if they exist
                for rel in saved:
                    src = os.path.join(repo_root, rel.replace('/', os.sep))
                    if os.path.exists(src):
                        dst = os.path.join(tmp, os.path.basename(src))
                        try:
                            shutil.copyfile(src, dst)
                            images_list.append(os.path.basename(dst))
                        except Exception:
                            pass
            elif images_arg:
                images_list = [os.path.basename(p.strip()) for p in images_arg.split(',') if p.strip()]

            # also save any newly uploaded files from this request
            for f in files:
                filename = secure_filename(f.filename)
                if not filename:
                    continue
                path = os.path.join(tmp, filename)
                try:
                    f.save(path)
                    if os.path.basename(path) not in images_list:
                        images_list.append(os.path.basename(path))
                except Exception:
                    pass

            # generate a simple HTML page in tmp
            main_image_html = ''
            thumbs_html = ''
            if images_list:
                main_image_html = f'<img src="{images_list[0]}" alt="{title} main"/>'
                thumbs_html = ''.join([f'<div class="thumb"><img src="{p}"/></div>' for p in images_list])

            html_content = f"""<!doctype html><html><head><meta charset=\"utf-8\"><title>{title}</title></head><body><h1>{title}</h1><div class=\"gallery\">{main_image_html}<div class=\"thumbs\">{thumbs_html}</div></div><div class=\"price\">{price or price_range or 'Contact for pricing'}</div></body></html>"""
            html_name = f'vehicle-{vid}.html'
            html_path = os.path.join(tmp, html_name)
            with open(html_path, 'w', encoding='utf-8') as fh:
                fh.write(html_content)

            # thumbnail generation
            if images_list and PIL_AVAILABLE:
                try:
                    first = os.path.join(tmp, images_list[0])
                    im = Image.open(first)
                    im.thumbnail((400,300))
                    thumb_path = os.path.join(tmp, 'thumb.jpg')
                    im.convert('RGB').save(thumb_path, 'JPEG', quality=85)
                except Exception:
                    pass

            # upload tmp files to Supabase Storage
            def supabase_upload(bucket, dest_path, data_bytes, content_type='application/octet-stream'):
                cfg = get_supabase_settings()
                key = cfg.get('service_key') or cfg.get('anon_key')
                if not cfg['url'] or not key:
                    raise RuntimeError('Supabase not configured')
                endpoint = cfg['url'].rstrip('/') + f'/storage/v1/object/{bucket}/{dest_path}'
                req = urllib_request.Request(endpoint, data=data_bytes, headers={
                    'apikey': key,
                    'Authorization': f'Bearer {key}',
                    'Content-Type': content_type
                }, method='PUT')
                with urllib_request.urlopen(req, timeout=30) as resp:
                    return resp.read()

            bucket = os.environ.get('SUPABASE_STORAGE_BUCKET') or os.environ.get('SUPABASE_BUCKET') or 'public'
            cfg = get_supabase_settings()
            public_base = cfg['url'].rstrip('/') + f'/storage/v1/object/public/{bucket}'
            uploaded_urls = []
            upload_errors = []
            for root, dirs, files_in_tmp in os.walk(tmp):
                for fname in files_in_tmp:
                    abs_path = os.path.join(root, fname)
                    rel_path = os.path.relpath(abs_path, tmp).replace('\\','/')
                    # sanitize filename portion to avoid spaces/unsafe chars in storage
                    dest_name = os.path.basename(rel_path)
                    safe_name = sanitize_storage_filename(dest_name)
                    dest = f'vehicles/{vid}/{safe_name}'
                    try:
                        with open(abs_path, 'rb') as fh:
                            data = fh.read()
                        ctype = mimetypes.guess_type(fname)[0] or 'application/octet-stream'
                        supabase_upload(bucket, dest, data, ctype)
                        uploaded_urls.append(public_base + '/' + quote(dest))
                    except Exception as e:
                        upload_errors.append({'file': abs_path, 'error': str(e)})
                        print('Upload failed for', abs_path, e)

            vehicle_record['images'] = [
                u for u in uploaded_urls
                if os.path.splitext(u.split('?', 1)[0].split('#', 1)[0].lower())[1].lstrip('.') in ALLOWED_EXT
            ]
            globals()['uploaded_urls'] = vehicle_record['images']
            globals()['upload_errors'] = upload_errors
            # `page_url` is not present in the live `vehicles` table schema, so skip storing it.
            out = 'Generated and uploaded files to Supabase Storage.'
            ok = True
        except Exception as exc:
            ok = False
            out = f'Vehicle temp generation/upload failed: {exc}'
            print(out)
        finally:
            if tmp and os.path.isdir(tmp):
                try:
                    shutil.rmtree(tmp)
                except Exception:
                    pass
    else:
        gen = os.path.join(repo_root, 'tools', 'generate_vehicle.py')
        cmd = [
            sys.executable, gen,
            '--id', vid,
            '--title', title,
            '--price', price or price_range or 'Price on request',
            '--year', str(year or ''),
            '--transmission', transmission,
            '--fuel', fuel,
            '--mileage', mileage,
            '--vin', vin,
            '--condition', condition,
            '--history', history,
            '--location', location,
            '--brand', brand,
            '--year-model', year_model,
            '--engine-capacity', engine_capacity,
            '--price-range', price_range,
            '--shipping-cost', shipping_cost,
            '--service-fees', service_fees,
            '--duty', duty,
            '--port-charges', port_charges,
            '--total-landed-cost', total_landed_cost,
            '--current-location', current_location,
            '--images', images_arg
        ]
        try:
            proc = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True, timeout=60)
            ok = proc.returncode == 0
            out = proc.stdout + '\n' + proc.stderr
        except Exception as e:
            ok = False
            out = str(e)
            print(f'generate_vehicle subprocess failed: {e}')

    # Always sync core vehicle metadata to Supabase; if uploads succeeded we attached image URLs/page_url above
    supabase_result = sync_vehicle_to_supabase(vehicle_record)

    globals()['uploaded_urls'] = globals().get('uploaded_urls', uploaded_urls if 'uploaded_urls' in locals() else [])
    globals()['upload_errors'] = globals().get('upload_errors', upload_errors if 'upload_errors' in locals() else [])
    resp_payload = {
        'ok': ok,
        'output': out or 'Vehicle synced to database; static file generation may have been skipped in serverless mode.',
        'serverless_fallback': is_vercel and not (globals().get('file_write_ok', True) and ok),
        'supabase': supabase_result,
        'uploaded_urls': globals().get('uploaded_urls', []),
        'upload_errors': globals().get('upload_errors', [])
    }
    resp = jsonify(resp_payload)
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp


@app.route('/api/admin/regenerate_thumbs', methods=['POST', 'OPTIONS'])
def api_regenerate_thumbs_alias():
    return regenerate_thumbs()

@app.route('/admin/regenerate_thumbs', methods=['POST', 'OPTIONS'])
def regenerate_thumbs():
    if request.method == 'OPTIONS':
        resp = jsonify({'ok': True})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return resp

    # require auth via current_password
    current = request.form.get('current_password') or (request.json and request.json.get('current_password'))
    if not current:
        resp = jsonify({'error':'current_password required'})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp, 400

    # load existing creds
    if os.path.exists(CREDS_PATH):
        with open(CREDS_PATH, 'r', encoding='utf-8') as f:
            creds = json.load(f)
    else:
        creds = None
    if not verify_password(current, creds):
        resp = jsonify({'error':'current password invalid'})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp, 403

    vid = request.form.get('id') or (request.json and request.json.get('id'))
    sizes = request.form.get('sizes') or (request.json and request.json.get('sizes')) or '800x600'
    if not vid:
        resp = jsonify({'error':'id required'})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp, 400

    # parse sizes
    size_list = []
    try:
        for part in sizes.split(','):
            part = part.strip()
            if not part: continue
            w,h = part.lower().split('x')
            size_list.append((int(w), int(h)))
    except Exception:
        resp = jsonify({'error':'invalid sizes format'})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp, 400

    target_dir = os.path.join(IMAGES_ROOT, vid)
    if not os.path.isdir(target_dir):
        resp = jsonify({'error':'images folder not found for id: '+vid})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp, 404

    written = []
    # pick source image
    candidates = [n for n in os.listdir(target_dir) if allowed_filename(n)]
    if not candidates:
        resp = jsonify({'error':'no source images found in folder'})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp, 400
    src_name = '1.jpg' if '1.jpg' in candidates else candidates[0]
    src_path = os.path.join(target_dir, src_name)

    if not PIL_AVAILABLE:
        resp = jsonify({'error':'Pillow not available on server'})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp, 500

    try:
        from PIL import Image
        for idx, (w,h) in enumerate(size_list):
            out_name = f'thumb_{w}x{h}.jpg'
            out_path = os.path.join(target_dir, out_name)
            try:
                img = Image.open(src_path)
                img.thumbnail((w,h))
                if img.mode in ('RGBA','P'):
                    img = img.convert('RGB')
                img.save(out_path, 'JPEG', quality=85)
                written.append(os.path.relpath(out_path, os.path.dirname(os.path.dirname(__file__))).replace('\\','/'))
            except Exception as e:
                # continue on error
                written.append({'error': str(e), 'file': out_name})
            # write thumb.jpg for first size
            if idx == 0:
                primary = os.path.join(target_dir, 'thumb.jpg')
                try:
                    img = Image.open(src_path)
                    img.thumbnail((w,h))
                    if img.mode in ('RGBA','P'):
                        img = img.convert('RGB')
                    img.save(primary, 'JPEG', quality=85)
                    written.append(os.path.relpath(primary, os.path.dirname(os.path.dirname(__file__))).replace('\\','/'))
                except Exception as e:
                    written.append({'error': str(e), 'file': 'thumb.jpg'})
    except Exception as e:
        resp = jsonify({'error': 'thumbnail generation failed: '+str(e)})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp, 500

    resp = jsonify({'ok': True, 'written': written})
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp


@app.route('/api/admin/list_media', methods=['GET', 'OPTIONS'])
def api_list_media_alias():
    return list_media()

@app.route('/admin/list_media', methods=['GET', 'OPTIONS'])
def list_media():
    if request.method == 'OPTIONS':
        resp = jsonify({'ok': True})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return resp

    media = []

    # Production/Vercel: the durable source of truth is Supabase. The vehicle
    # row contains the complete public gallery, so the admin media page can
    # display the same images customers see after a deployment.
    rows = call_supabase('GET', '/vehicles?select=id,images&order=created_at.desc')
    if rows.get('ok') and isinstance(rows.get('data'), list):
        for row in rows['data']:
            vehicle_id = row.get('id') or 'unknown'
            image_values = row.get('images') if isinstance(row.get('images'), list) else []
            files = []
            for index, value in enumerate(image_values, start=1):
                url = str(value or '').strip()
                if not url:
                    continue
                path = url
                if '/storage/v1/object/public/' in path:
                    path = path.split('/storage/v1/object/public/', 1)[1]
                files.append({
                    'name': path.rsplit('/', 1)[-1] or f'photo-{index}',
                    'path': url,
                    'url': url,
                    'size': 0
                })
            if files:
                media.append({'vehicle_id': vehicle_id, 'files': files})

    # Local development fallback.
    if not media:
        repo_root = os.path.dirname(os.path.dirname(__file__))
        media_root = os.path.join(repo_root, 'images')
        if os.path.isdir(media_root):
            for entry in sorted(os.listdir(media_root)):
                full_path = os.path.join(media_root, entry)
                if not os.path.isdir(full_path):
                    continue
                files = []
                for file_name in sorted(os.listdir(full_path)):
                    file_path = os.path.join(full_path, file_name)
                    if os.path.isfile(file_path):
                        files.append({
                            'name': file_name,
                            'path': os.path.relpath(file_path, repo_root).replace('\\', '/'),
                            'url': build_public_image_urls([f'vehicles/{entry}/{file_name}'])[0],
                            'size': os.path.getsize(file_path)
                        })
                if files:
                    media.append({'vehicle_id': entry, 'files': files})

    resp = jsonify({'ok': True, 'media': media})
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp


@app.route('/api/admin/delete_media', methods=['POST', 'OPTIONS'])
def api_delete_media_alias():
    return delete_media()

@app.route('/admin/delete_media', methods=['POST', 'OPTIONS'])
def delete_media():
    if request.method == 'OPTIONS':
        resp = jsonify({'ok': True})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return resp

    current = request.form.get('current_password') or (request.json and request.json.get('current_password'))
    file_path = request.form.get('file_path') or (request.json and request.json.get('file_path'))
    vehicle_id = request.form.get('vehicle_id') or (request.json and request.json.get('vehicle_id'))

    if not current:
        resp = jsonify({'error': 'current_password required'})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp, 400

    if not file_path and not vehicle_id:
        resp = jsonify({'error': 'file_path or vehicle_id required'})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp, 400

    if os.path.exists(CREDS_PATH):
        with open(CREDS_PATH, 'r', encoding='utf-8') as f:
            creds = json.load(f)
    else:
        creds = None

    if not verify_password(current, creds):
        resp = jsonify({'error': 'current password invalid'})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp, 403

    repo_root = os.path.dirname(os.path.dirname(__file__))
    target_path = os.path.join(repo_root, file_path) if file_path else os.path.join(repo_root, 'images', vehicle_id)

    if not os.path.exists(target_path):
        resp = jsonify({'error': 'target not found'})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp, 404

    try:
        if os.path.isdir(target_path):
            shutil.rmtree(target_path)
        else:
            os.remove(target_path)
        resp = jsonify({'ok': True, 'removed': target_path})
    except Exception as exc:
        resp = jsonify({'error': str(exc)})
        resp.status_code = 500

    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp


@app.route('/api/admin/delete_vehicle', methods=['POST', 'OPTIONS'])
def api_delete_vehicle_alias():
    return delete_vehicle()


@app.route('/api/admin/debug_vehicle', methods=['POST', 'OPTIONS'])
def api_debug_vehicle():
    # protected debug helper to inspect Supabase vehicle row
    if request.method == 'OPTIONS':
        resp = jsonify({'ok': True})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return resp

    current = request.form.get('current_password') or (request.json and request.json.get('current_password'))
    vid = request.form.get('id') or (request.json and request.json.get('id'))
    if not current or not vid:
        resp = jsonify({'error': 'current_password and id are required'})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp, 400

    # verify creds
    if os.path.exists(CREDS_PATH):
        with open(CREDS_PATH, 'r', encoding='utf-8') as f:
            creds = json.load(f)
    else:
        creds = None
    if not verify_password(current, creds):
        resp = jsonify({'error':'current password invalid'})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp, 403

    # query supabase for vehicle row
    try:
        path = f"/vehicles?id=eq.{quote(vid, safe='')}&select=*"
        result = call_supabase('GET', path)
        resp = jsonify({'ok': True, 'result': result})
    except Exception as exc:
        resp = jsonify({'ok': False, 'error': str(exc)})
        resp.status_code = 500
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp

@app.route('/admin/delete_vehicle', methods=['POST', 'OPTIONS'])
def delete_vehicle():
    if request.method == 'OPTIONS':
        resp = jsonify({'ok': True})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return resp

    current = request.form.get('current_password') or (request.json and request.json.get('current_password'))
    vid = request.form.get('id') or (request.json and request.json.get('id'))

    if not current:
        resp = jsonify({'error': 'current_password required'})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp, 400

    if not vid:
        resp = jsonify({'error': 'id required'})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp, 400

    if os.path.exists(CREDS_PATH):
        with open(CREDS_PATH, 'r', encoding='utf-8') as f:
            creds = json.load(f)
    else:
        creds = None

    if not verify_password(current, creds):
        resp = jsonify({'error': 'current password invalid'})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp, 403

    repo_root = os.path.dirname(os.path.dirname(__file__))
    remove_script = os.path.join(repo_root, 'tools', 'remove_vehicle.py')
    try:
        import subprocess, sys
        proc = subprocess.run([sys.executable, remove_script, '--id', vid], cwd=repo_root, capture_output=True, text=True, timeout=60)
        output = (proc.stdout or '') + (proc.stderr or '')
        ok = proc.returncode == 0
        if ok:
            delete_vehicle_from_supabase(vid)
        resp = jsonify({'ok': ok, 'output': output, 'deleted_id': vid})
    except Exception as exc:
        resp = jsonify({'ok': False, 'error': str(exc), 'deleted_id': vid})
        resp.status_code = 500

    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp

if __name__ == '__main__':
    print('URL map:', app.url_map)
    app.run(host='127.0.0.1', port=5001)
