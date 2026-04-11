import httpx

PB_URL = 'http://localhost:8090'
EMAIL = 'arifaryyy16@gmail.com'
PASSWORD = '12345678'  # Assuming from fix_pameran_rules.py

r = httpx.post(f'{PB_URL}/api/collections/_superusers/auth-with-password',
    json={'identity': EMAIL, 'password': PASSWORD}, timeout=10)
token = r.json().get('token')

if not token:
    print("Could not get admin token")
    exit(1)

headers = {'Authorization': f'Bearer {token}'}

r = httpx.get(f'{PB_URL}/api/collections/users', headers=headers, timeout=10)
user_coll = r.json()

print('=== USERS CURRENT RULES ===')
print('listRule:', getattr(user_coll, 'get', lambda x: None)('listRule'))
print('viewRule:', getattr(user_coll, 'get', lambda x: None)('viewRule'))

new_view_rule = "@request.auth.id != ''"

print('\nUPDATING viewRule to allow all authenticated users to view others (needed for expansion)...')
r_update = httpx.patch(f'{PB_URL}/api/collections/{user_coll.get("id")}', headers=headers,
    json={'viewRule': new_view_rule}, timeout=10)

if r_update.status_code == 200:
    print('UPDATE SUCCESS!')
    print('New viewRule:', r_update.json().get('viewRule'))
else:
    print('UPDATE ERROR:', r_update.text)
