import httpx
import asyncio

async def test():
    client = httpx.AsyncClient()
    resp = await client.post('http://127.0.0.1:8090/api/collections/_superusers/auth-with-password', json={'identity': 'arifaryyy16@gmail.com', 'password': '12345678'})
    token = resp.json().get('token')
    resp2 = await client.get('http://127.0.0.1:8090/api/collections/submissions', headers={'Authorization': f'Bearer {token}'})
    print(resp2.status_code, resp2.text)

asyncio.run(test())
