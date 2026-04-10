"""
add_kelas_field.py
Menambahkan field 'kelas' (Plain Text, required) ke koleksi users di PocketBase.
Jalankan sekali saja.
"""
import httpx

PB_URL = 'http://localhost:8090'
EMAIL = 'arifaryyy16@gmail.com'
PASSWORD = '12345678'

# Login
r = httpx.post(f'{PB_URL}/api/collections/_superusers/auth-with-password',
    json={'identity': EMAIL, 'password': PASSWORD}, timeout=10)
r.raise_for_status()
token = r.json()['token']
headers = {'Authorization': f'Bearer {token}'}
print('OK - Login berhasil')

# Ambil koleksi users
r = httpx.get(f'{PB_URL}/api/collections', headers=headers, timeout=10)
collections = r.json()
if isinstance(collections, dict):
    collections = collections.get('items', [])

users_coll = next((c for c in collections if c['name'] == 'users'), None)
if not users_coll:
    print('ERROR: koleksi users tidak ditemukan!')
    exit(1)

coll_id = users_coll['id']
fields = users_coll.get('fields', users_coll.get('schema', []))

# Cek apakah kelas sudah ada
if any(f.get('name') == 'kelas' for f in fields):
    print('Field kelas SUDAH ADA. Tidak perlu ditambah.')
else:
    # Tambah field kelas
    fields.append({
        'name': 'kelas',
        'type': 'text',
        'required': False,   # False dulu agar akun lama tidak error
        'options': {'min': None, 'max': None, 'pattern': ''}
    })

    key = 'fields' if 'fields' in users_coll else 'schema'
    r = httpx.patch(
        f'{PB_URL}/api/collections/{coll_id}',
        headers=headers,
        json={key: fields},
        timeout=15,
    )
    print(f'PocketBase response: {r.status_code}')
    if r.status_code == 200:
        print('SUKSES! Field "kelas" berhasil ditambahkan ke koleksi users.')
        print()
        print('LANGKAH SELANJUTNYA:')
        print('Buka http://localhost:8090/_/')
        print('→ Collections → users → klik akun siswa')
        print('→ Isi field "kelas" dengan nilai: XI.1 / XI.2 / XI.3 / XI.4 / XI.5')
        print('→ Save')
    else:
        print('ERROR:', r.text)
