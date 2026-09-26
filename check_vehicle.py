import json
import sys
sys.path.insert(0, 'tools')
from admin_api import call_supabase

# Use same path as ensure_public_image_urls.py
print('Testing query 1: /vehicles?select=id,images')
result = call_supabase('GET', '/vehicles?select=id,images')
print(f'Result: {json.dumps(result, indent=2)}')

print('\n\nTesting query 2: /vehicles?id=eq.fzz949')
result2 = call_supabase('GET', '/vehicles?id=eq.fzz949')
print(f'Result: {json.dumps(result2, indent=2)}')

if result.get('ok') and result.get('data'):
    print(f'\n\nFound {len(result["data"])} vehicles')
    for vehicle in result['data']:
        print(f"  - {vehicle.get('id')}: {len(vehicle.get('images', []))} images")
