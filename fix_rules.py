import httpx

PB_URL = 'http://localhost:8090'
EMAIL = 'arifaryyy16@gmail.com'
PASSWORD = '12345678'

r = httpx.post(f'{PB_URL}/api/collections/_superusers/auth-with-password',
    json={'identity': EMAIL, 'password': PASSWORD}, timeout=10)
token = r.json()['token']
headers = {'Authorization': f'Bearer {token}'}

# Get submissions collection
r = httpx.get(f'{PB_URL}/api/collections', headers=headers, timeout=10)
collections = r.json()
if isinstance(collections, dict):
    collections = collections.get('items', [])

coll = next((c for c in collections if c['name'] == 'submissions'), None)
if not coll:
    print('ERROR: koleksi submissions tidak ditemukan!')
    exit(1)

coll_id = coll['id']
print('Sebelum updateRule :', repr(coll.get('updateRule')))
print('Sebelum deleteRule :', repr(coll.get('deleteRule')))

# Patch dengan rule yang benar sesuai spec PRD v3
payload = {
    'updateRule': "@request.auth.role = 'teacher' || @request.auth.role = 'admin'",
    'deleteRule': "@request.auth.role = 'teacher' || @request.auth.role = 'admin'",
}

r = httpx.patch(
    f'{PB_URL}/api/collections/{coll_id}',
    headers=headers,
    json=payload,
    timeout=15,
)
print('PocketBase response:', r.status_code)
if r.status_code == 200:
    updated = r.json()
    print('Sesudah updateRule :', repr(updated.get('updateRule')))
    print('Sesudah deleteRule :', repr(updated.get('deleteRule')))
    print('\nSUKSES! Sekarang guru bisa ACC, Tolak, dan Hapus submission.')
else:
    print('ERROR:', r.text)
