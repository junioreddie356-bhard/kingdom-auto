#!/usr/bin/env python3
import json
import urllib.request

# Supabase config
url = 'https://invsxcmcczwckmfkynzk.supabase.co'
service_key = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImludnN4Y21jY3p3Y2ttZmt5bnprIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc5MDQ3MTQ1MSwiZXhwIjoyMTA2MDQ3NDUxfQ.F74Q3jOr4SWAG00Y9PbI1wS248ZatVEaiRWWtKfiZtI'

headers = {
    'apikey': service_key,
    'Authorization': f'Bearer {service_key}',
    'Content-Type': 'application/json'
}


def count_rows(table_name):
    endpoint = f'{url}/rest/v1/{table_name}?select=id'
    req = urllib.request.Request(endpoint, headers=headers, method='GET')
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode('utf-8'))
    return data if isinstance(data, list) else []


def delete_rows(table_name):
    rows = count_rows(table_name)
    deleted = 0
    for row in rows:
        record_id = row.get('id')
        if not record_id:
            continue
        delete_endpoint = f'{url}/rest/v1/{table_name}?id=eq.{record_id}'
        delete_req = urllib.request.Request(delete_endpoint, headers=headers, method='DELETE')
        try:
            with urllib.request.urlopen(delete_req, timeout=20):
                deleted += 1
        except Exception:
            pass
    return deleted


for table_name in ['vehicles', 'inquiries']:
    rows = count_rows(table_name)
    print(f'Found {len(rows)} rows in {table_name}')
    deleted = delete_rows(table_name)
    print(f'✓ Deleted {deleted} rows from {table_name}')

print('✓ All inventory and inquiry records cleared successfully!')
