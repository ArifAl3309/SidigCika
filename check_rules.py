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

coll = next((c for c in collections if c['name'] == 'submissions'), None)
if coll:
    print('=== SUBMISSIONS API RULES ===')
    print('listRule   :', repr(coll.get('listRule')))
    print('viewRule   :', repr(coll.get('viewRule')))
    print('createRule :', repr(coll.get('createRule')))
    print('updateRule :', repr(coll.get('updateRule')))
    print('deleteRule :', repr(coll.get('deleteRule')))
else:
    print('Koleksi submissions tidak ditemukan!')
