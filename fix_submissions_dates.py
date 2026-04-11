import httpx
import uuid

PB_URL = 'http://localhost:8090'
EMAIL = 'arifaryyy16@gmail.com'
PASSWORD = '12345678'

r = httpx.post(f'{PB_URL}/api/collections/_superusers/auth-with-password', json={'identity': EMAIL, 'password': PASSWORD}, timeout=10)
token = r.json().get('token')

if not token:
    print("Could not get admin token")
    exit(1)

headers = {'Authorization': f'Bearer {token}'}

r = httpx.get(f'{PB_URL}/api/collections/submissions', headers=headers, timeout=10)
coll = r.json()

fields = coll.get('fields', [])
existing = [f['name'] for f in fields]

updated = False
if 'created' not in existing:
    fields.append({
        'hidden': False, 'id': f'autodate{uuid.uuid4().hex[:10]}', 'name': 'created', 
        'onCreate': True, 'onUpdate': False, 'presentable': False, 'system': False, 'type': 'autodate'
    })
    updated = True

if 'updated' not in existing:
    fields.append({
        'hidden': False, 'id': f'autodate{uuid.uuid4().hex[:10]}', 'name': 'updated', 
        'onCreate': True, 'onUpdate': True, 'presentable': False, 'system': False, 'type': 'autodate'
    })
    updated = True

if updated:
    print("Menambahkan 'created' dan 'updated' ke tabel submissions...")
    r_patch = httpx.patch(f'{PB_URL}/api/collections/{coll["id"]}', headers=headers, json={'fields': fields}, timeout=10)
    if r_patch.status_code == 200:
        print("SUCCESS! Fields 'created' dan 'updated' berhasil ditambahkan.")
        print("TOLONG REFRESH BROWSER (Ctrl+F5) untuk melihat hasilnya.")
        # Mari perbarui semua submissions yang sudah ada dengan mengisi `created` and `updated` dengan NOW
    else:
        print("ERROR:", r_patch.text)
else:
    print("Fields already exist!")
