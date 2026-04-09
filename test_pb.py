import httpx
import asyncio

async def test():
    client = httpx.AsyncClient()
    resp = await client.post('http://127.0.0.1:8090/api/collections/_superusers/auth-with-password', json={'identity': 'arifaryyy16@gmail.com', 'password': '12345678'})
    print('Admin Login:', resp.status_code)
    try:
        token = resp.json().get('token')
    except Exception as e:
        print('Error:', e)
        return

    resp2 = await client.get('http://127.0.0.1:8090/api/collections/submissions/records?expand=user_id', headers={'Authorization': f'Bearer {token}'})
    print('Submissions API status:', resp2.status_code)
    print('Submissions API Response:', resp2.text)

asyncio.run(test())
