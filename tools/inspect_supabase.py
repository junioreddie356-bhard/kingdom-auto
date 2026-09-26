import importlib.util, os, json

admin_path = os.path.join(os.path.dirname(__file__), 'admin_api.py')
spec = importlib.util.spec_from_file_location('tools.admin_api', admin_path)
admin_api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(admin_api)

cfg = admin_api.get_supabase_settings()
bucket = admin_api.resolve_storage_bucket()

def mask(s):
    if not s:
        return None
    s = str(s)
    if len(s) > 8:
        return s[:4] + '...' + s[-4:]
    return s

envs = {k: os.environ.get(k) for k in ['SUPABASE_STORAGE_BUCKET','SUPABASE_BUCKET','SUPABASE_SERVICE_ROLE_KEY','SUPABASE_SERVICE_KEY','SUPABASE_KEY','SUPABASE_ANON_KEY','VERCEL','VERCEL_ENV','SITE_URL']}

out = {
    'supabase_url': cfg.get('url'),
    'resolved_bucket': bucket,
    'service_key_present': bool(cfg.get('service_key')),
    'anon_key_present': bool(cfg.get('anon_key')),
    'service_key_preview': mask(cfg.get('service_key')),
    'anon_key_preview': mask(cfg.get('anon_key')),
    'env_overrides': {k: (v if v is None else ('<set>' if len(v)>0 else '')) for k,v in envs.items()}
}
print(json.dumps(out, indent=2))
