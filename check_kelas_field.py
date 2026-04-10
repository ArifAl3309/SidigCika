import httpx, json

PB_URL = 'http://localhost:8090'
EMAIL = 'arifaryyy16@gmail.com'
PASSWORD = '12345678'

r = httpx.post(f'{PB_URL}/api/collections/_superusers/auth-with-password',
    json={'identity': EMAIL, 'password': PASSWORD}, timeout=10)
token = r.json()['token']
headers = {'Authorization': f'Bearer {token}'}

r = httpx.get(f'{PB_URL}/api/collections', headers=headers, timeout=10)
collections = r.json()
if isinstance(collections, dict):
    collections = collections.get('items', [])

users_coll = next((c for c in collections if c['name'] == 'users'), None)
fields = users_coll.get('fields', users_coll.get('schema', []))

print('=== SEMUA FIELD DI KOLEKSI USERS ===')
for f in fields:
    print(f"  name={f.get('name')!r:20s} type={f.get('type')!r:12s} options={json.dumps(f.get('options', {}))}")

print()
# Ambil raw record user pertama untuk lihat struktur JSON aslinya
r2 = httpx.get(f'{PB_URL}/api/collections/users/records',
    headers=headers,
    params={'perPage': 1},
    timeout=10)
items = r2.json().get('items', [])
if items:
    print('=== RAW JSON USER PERTAMA ===')
    print(json.dumps(items[0], indent=2, ensure_ascii=False))
