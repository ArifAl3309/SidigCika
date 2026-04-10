"""
fix_score_schema.py
Otomatis update field 'score' di koleksi 'submissions' PocketBase:
  - default: 0
  - required: False  (hindari zero-value bug di Go)
Jalankan sekali saja dari folder project.
"""
import httpx, json

PB_URL    = "http://localhost:8090"
EMAIL     = "arifaryyy16@gmail.com"
PASSWORD  = "12345678"

def main():
    # 1. Login sebagai superuser
    print(">> Login sebagai superuser...")
    r = httpx.post(
        f"{PB_URL}/api/collections/_superusers/auth-with-password",
        json={"identity": EMAIL, "password": PASSWORD},
        timeout=10,
    )
    r.raise_for_status()
    token = r.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("   OK - token didapat")

    # 2. Ambil daftar koleksi, cari 'submissions'
    print(">> Mencari koleksi 'submissions'...")
    r = httpx.get(f"{PB_URL}/api/collections", headers=headers, timeout=10)
    r.raise_for_status()
    collections = r.json()

    # Handle both list and {"items": [...]} format
    if isinstance(collections, dict):
        collections = collections.get("items", [])

    coll = next((c for c in collections if c["name"] == "submissions"), None)
    if not coll:
        print("   ERROR: koleksi 'submissions' tidak ditemukan!")
        return

    coll_id = coll["id"]
    print(f"   OK - id={coll_id}")

    # 3. Temukan field 'score' dan patch
    print(">> Mengupdate field 'score'...")
    fields = coll.get("fields", coll.get("schema", []))
    updated = False
    for f in fields:
        if f.get("name") == "score":
            print(f"   Sebelum: required={f.get('required')}, default={f.get('default')}")
            f["required"] = False   # hilangkan required agar 0 tidak dianggap blank
            f["default"]  = 0      # set default = 0
            updated = True
            print(f"   Sesudah: required={f.get('required')}, default={f.get('default')}")
            break

    if not updated:
        print("   ERROR: field 'score' tidak ditemukan di schema!")
        return

    # 4. Patch koleksi — kirim seluruh schema kembali
    key = "fields" if "fields" in coll else "schema"
    payload = {key: fields}
    r = httpx.patch(
        f"{PB_URL}/api/collections/{coll_id}",
        headers=headers,
        json=payload,
        timeout=15,
    )
    print(f">> PocketBase response: {r.status_code}")
    if r.status_code in (200, 204):
        print("   SUKSES! Field 'score' sudah di-update.")
        print("   - required : False")
        print("   - default  : 0")
        print("\nSekarang coba submit lagi dari browser.")
    else:
        print(f"   ERROR: {r.text}")

if __name__ == "__main__":
    main()
