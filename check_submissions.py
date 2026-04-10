import httpx

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

sub_coll = next((c for c in collections if c['name'] == 'submissions'), None)
if sub_coll:
    fields = sub_coll.get('fields', sub_coll.get('schema', []))
    print('=== SUBMISSIONS FIELD ===')
    for f in fields:
        print(f"  name={f.get('name')!r:20s}  type={f.get('type')!r:15s}")
else:
    print('Koleksi submissions tidak ditemukan!')
