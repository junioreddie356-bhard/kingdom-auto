import os, json, mimetypes, sys
from urllib import request as urllib_request, error as urllib_error
try:
    from tools import admin_api
except Exception:
    import importlib.util
    admin_path = os.path.join(os.path.dirname(__file__), 'admin_api.py')
    spec = importlib.util.spec_from_file_location('tools.admin_api', admin_path)
    admin_api = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(admin_api)

cfg = admin_api.get_supabase_settings()
bucket = admin_api.resolve_storage_bucket()
path = 'vehicles/fzz949/test-probe.jpg'
file_path = os.path.join('images_upload','fzz949', os.listdir(os.path.join('images_upload','fzz949'))[0])
with open(file_path,'rb') as fh:
    data = fh.read()
endpoint = cfg['url'].rstrip('/') + f'/storage/v1/object/{bucket}/{path.lstrip('/')}'

def try_key(key_name, key_value):
    headers = {
        'apikey': key_value,
        'Authorization': f'Bearer {key_value}',
        'Content-Type': mimetypes.guess_type(file_path)[0] or 'application/octet-stream',
        'x-upsert': 'true'
    }
    req = urllib_request.Request(endpoint, data=data, headers=headers, method='PUT')
    print('\nPUT', endpoint)
    print('Using', key_name)
    try:
        with urllib_request.urlopen(req, timeout=30) as resp:
            print('Status', getattr(resp,'status',None) or resp.getcode())
            body = resp.read()
            try:
                print('Body:', body.decode('utf-8'))
            except Exception:
                print('Binary response length', len(body))
    except urllib_error.HTTPError as he:
        print('HTTPError', getattr(he,'code',None))
        try:
            print('Body:', he.read().decode('utf-8'))
        except Exception as e:
            print('Could not read error body:', e)
    except Exception as e:
        print('Error', e)

service = cfg.get('service_key')
anon = cfg.get('anon_key')
try_key('service_key', service)
if anon and anon != service:
    try_key('anon_key', anon)
