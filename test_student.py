import httpx
import asyncio

async def test():
    client = httpx.AsyncClient()
    # Try multiple common passwords
    for pwd in ['12345678', 'password', 'password123']:
        resp = await client.post('http://127.0.0.1:8090/api/collections/users/auth-with-password', json={'identity': 'arif@student.sch.id', 'password': pwd})
        if resp.status_code == 200:
            print('Student Login success with', pwd)
            token = resp.json().get('token')
            resp2 = await client.get('http://127.0.0.1:8090/api/collections/submissions/records', headers={'Authorization': f'Bearer {token}'})
            print('Student Submissions API status:', resp2.status_code)
            print('Student Submissions API Response:', resp2.text)
            
            resp3 = await client.get('http://127.0.0.1:8090/api/collections/submissions/records?filter=user_id="3xj4m4lxnzm2zmk"', headers={'Authorization': f'Bearer {token}'})
            print('Student Submissions (filtered) API status:', resp3.status_code)
            print('Filtered:', resp3.text)
            return
    print("Could not login as student!")

asyncio.run(test())
