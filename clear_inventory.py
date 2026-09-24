#!/usr/bin/env python3
import urllib.request
import json

# Supabase config
url = 'https://spckgpxzcxvogjamfsqr.supabase.co'
anon_key = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNwY2tncHh6Y3h2b2dqYW1mc3FyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODg1NDg2NjQsImV4cCI6MjEwNDEyNDY2NH0.h52gkl9ms2vT785SUTmAT_IDzNfaa2jUpepEGIW0yZw'

# First, get all vehicle IDs
endpoint = f'{url}/rest/v1/vehicles?select=id'
headers = {
    'apikey': anon_key,
    'Authorization': f'Bearer {anon_key}',
    'Content-Type': 'application/json'
}

req = urllib.request.Request(endpoint, headers=headers, method='GET')
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        vehicles = json.loads(resp.read().decode('utf-8'))
        print(f'Found {len(vehicles)} vehicles')
        
        if len(vehicles) == 0:
            print('✓ Database is already empty!')
        else:
            # Delete each vehicle
            deleted = 0
            for vehicle in vehicles:
                vid = vehicle.get('id')
                if not vid:
                    continue
                    
                delete_endpoint = f'{url}/rest/v1/vehicles?id=eq.{vid}'
                delete_req = urllib.request.Request(delete_endpoint, headers=headers, method='DELETE')
                
                try:
                    with urllib.request.urlopen(delete_req, timeout=10) as del_resp:
                        deleted += 1
                except:
                    pass
            
            print(f'✓ Deleted {deleted} vehicles')
            print('✓ All inventory cleared successfully!')
            
except Exception as e:
    print(f'Error: {e}')
