import httpx

PB_URL = 'http://localhost:8090'
EMAIL = 'arifaryyy16@gmail.com'
PASSWORD = '12345678'

r = httpx.post(f'{PB_URL}/api/collections/_superusers/auth-with-password',
    json={'identity': EMAIL, 'password': PASSWORD}, timeout=10)
token = r.json()['token']
headers = {'Authorization': f'Bearer {token}'}

r = httpx.get(f'{PB_URL}/api/collections', headers=headers, timeout=10)
collections = r.json().get('items', [])
sub_coll = next((c for c in collections if c['name'] == 'submissions'), None)

print('=== SUBMISSIONS CURRENT RULES ===')
print('listRule:', repr(sub_coll.get('listRule')))
print('viewRule:', repr(sub_coll.get('viewRule')))

# Update listRule to allow viewing if status == 'accepted' or it is their own submission
new_list_rule = "@request.auth.id != '' && (@request.auth.id = user_id || @request.auth.role = 'teacher' || @request.auth.role = 'admin' || status = 'accepted')"
new_view_rule = "@request.auth.id != '' && (@request.auth.id = user_id || @request.auth.role = 'teacher' || @request.auth.role = 'admin' || status = 'accepted')"

print()
print('UPDATING RULES to allow Pameran access...')
r_update = httpx.patch(f'{PB_URL}/api/collections/{sub_coll["id"]}', headers=headers,
    json={'listRule': new_list_rule, 'viewRule': new_view_rule}, timeout=10)

if r_update.status_code == 200:
    print('UPDATE SUCCESS!')
    up = r_update.json()
    print('New listRule:', repr(up.get('listRule')))
else:
    print('UPDATE ERROR:', r_update.text)
