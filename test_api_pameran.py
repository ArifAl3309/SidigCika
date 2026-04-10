import httpx

PB_URL = 'http://localhost:8090'

# test login
r = httpx.post(f'{PB_URL}/api/collections/users/auth-with-password',
    json={'identity': 'arif@student.sch.id', 'password': '12345678'}, timeout=10)
if r.status_code != 200:
    print('Gagal login student:', r.text)
    exit(1)

token = r.json()['token']
headers = {'Authorization': f'Bearer {token}'}

# cURL sama persis dengan yang dipanggil pameran.html sekarang
r_pameran = httpx.get(f'{PB_URL}/api/collections/submissions/records', 
    params={
        'filter': 'status = "accepted"',
        'sort': '-updated',
        'expand': 'user_id'
    }, headers=headers, timeout=10)

print('STATUS:', r_pameran.status_code)
if r_pameran.status_code != 200:
    print('ERROR:', r_pameran.text)
else:
    data = r_pameran.json()
    print('BERHASIL! Total items:', len(data.get('items', [])))
