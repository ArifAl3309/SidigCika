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

# Cek koleksi users
users_coll = next((c for c in collections if c['name'] == 'users'), None)
if users_coll:
    print('=== KOLEKSI USERS — FIELDS ===')
    fields = users_coll.get('fields', users_coll.get('schema', []))
    for f in fields:
        print(f"  name={f.get('name')!r:20s}  type={f.get('type')!r:15s}  required={f.get('required')}")
    print()

# Cek beberapa akun user yang ada
r2 = httpx.get(f'{PB_URL}/api/collections/users/records',
    headers=headers,
    params={'perPage': 10, 'fields': 'id,name,email,role,kelas'},
    timeout=10)
data = r2.json()
items = data.get('items', [])
print('=== AKUN USERS YANG ADA ===')
for u in items:
    print(f"  name={u.get('name')!r:20s}  kelas={u.get('kelas')!r:10s}  role={u.get('role')!r}")
print(f'Total: {data.get("totalItems", 0)} akun')
