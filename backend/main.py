"""
backend/main.py
FastAPI backend — FASE 1
Endpoint: GET /  dan  POST /api/submit

Fixes vs v1:
  - Custom RequestValidationError handler (format {"error", "message"})
  - Explicit fitz.open() exception → 400 invalid_pdf (corrupt PDF)
  - Removed redundant await file.seek(0) after file_bytes sudah ada
  - httpx.HTTPStatusError ditambahkan ke except chain
  - Semua raise_for_status() di get_admin_token di-cover oleh try/except luar
"""

import hashlib
import os
import time
from datetime import datetime, timezone

import fitz  # PyMuPDF
import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, Header, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# ─── Konfigurasi ────────────────────────────────────────────────────────────
load_dotenv()

PB_URL         = os.getenv("POCKETBASE_URL", "http://localhost:8090")
ADMIN_EMAIL    = os.getenv("POCKETBASE_ADMIN_EMAIL", "")
ADMIN_PASSWORD = os.getenv("POCKETBASE_ADMIN_PASSWORD", "")

# ─── Admin-token cache (module-level) ────────────────────────────────────────
_admin_token: str | None = None
_admin_token_expires: float = 0.0


async def get_admin_token() -> str:
    """Mengembalikan admin token PocketBase. Auto-refresh jika hampir expired."""
    global _admin_token, _admin_token_expires
    if _admin_token and time.time() < _admin_token_expires - 300:
        return _admin_token
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{PB_URL}/api/collections/_superusers/auth-with-password",
            json={"identity": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            timeout=10.0,
        )
        r.raise_for_status()          # HTTPStatusError → ditangkap try/except di submit()
        _admin_token = r.json()["token"]
        _admin_token_expires = time.time() + 86400
        return _admin_token


# ─── Aplikasi FastAPI ────────────────────────────────────────────────────────
app = FastAPI(title="Student Submission API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8090"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    allow_credentials=True,
)


# ─── Custom handler: FastAPI built-in 422 → format PRD ───────────────────────
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Pastikan FastAPI's built-in field-validation error (misal: field 'title'
    tidak dikirim sama sekali) menghasilkan format yang sama dengan error PRD.
    """
    # Cari field mana yang bermasalah untuk pesan yang lebih informatif
    first_error = exc.errors()[0] if exc.errors() else {}
    loc = first_error.get("loc", [])
    field = loc[-1] if loc else "field"

    if field == "title":
        message = "Judul wajib diisi."
    elif field == "file":
        message = "File PDF wajib disertakan."
    else:
        message = f"Field '{field}' tidak valid atau wajib diisi."

    return JSONResponse(
        status_code=422,
        content={"error": "validation_error", "message": message},
    )


# ─── GET / ───────────────────────────────────────────────────────────────────
@app.get("/")
async def health_check():
    return {"status": "ok"}


# ─── POST /api/submit ────────────────────────────────────────────────────────
@app.post("/api/submit")
async def submit(
    file: UploadFile = File(...),
    title: str = Form(...),
    description: str = Form(""),
    authorization: str = Header(default=""),
):
    print(">>> HIT SUBMIT ENDPOINT! <<<")
    try:
        # ── Validasi header Authorization (lokal, tanpa network) ─────────────
        if not authorization.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={
                    "error": "unauthorized",
                    "message": "Token tidak valid atau sudah expired.",
                },
            )
        token = authorization.removeprefix("Bearer ").strip()

        # ── Validasi panjang field form (lokal, tanpa network) ───────────────
        if not title or not title.strip():
            return JSONResponse(
                status_code=422,
                content={
                    "error": "validation_error",
                    "message": "Judul wajib diisi.",
                },
            )
        if len(title) > 150:
            return JSONResponse(
                status_code=422,
                content={
                    "error": "validation_error",
                    "message": "Judul maksimal 150 karakter.",
                },
            )
        if len(description) > 500:
            return JSONResponse(
                status_code=422,
                content={
                    "error": "validation_error",
                    "message": "Deskripsi maksimal 500 karakter.",
                },
            )

        # ── LANGKAH 1: Verifikasi token user ke PocketBase ───────────────────
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{PB_URL}/api/collections/users/auth-refresh",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10.0,
            )
        if r.status_code != 200:
            return JSONResponse(
                status_code=401,
                content={
                    "error": "unauthorized",
                    "message": "Token tidak valid atau sudah expired.",
                },
            )
        user_data = r.json()["record"]
        user_id   = user_data["id"]
        user_role = user_data.get("role", "student")  # noqa: F841

        # ── LANGKAH 2: Cek cooldown (5 menit = 300 detik) ───────────────────
        admin_token = await get_admin_token()
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{PB_URL}/api/collections/submissions/records",
                headers={"Authorization": f"Bearer {admin_token}"},
                params={
                    "filter": f'(user_id="{user_id}")',
                    "perPage": 50,
                    "page": 1,
                },
                timeout=10.0,
            )
        data = r.json()
        items = data.get("items", [])
        if items:
            items.sort(key=lambda x: x.get("created", ""), reverse=True)
            last_str = items[0]["created"]
            # Format ISO PocketBase: "2024-01-15 14:30:00.000Z"
            last_dt = datetime.fromisoformat(last_str.replace("Z", "+00:00"))
            selisih = (datetime.now(timezone.utc) - last_dt).total_seconds()
            if selisih < 300:
                sisa = int(300 - selisih)
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "cooldown",
                        "message": "Tunggu sebelum submit lagi.",
                        "retry_after_seconds": sisa,
                    },
                )

        # ── LANGKAH 3: Validasi file ─────────────────────────────────────────
        file_bytes = await file.read()
        if len(file_bytes) > 5 * 1024 * 1024:
            print("ERROR 400: file_too_large")
            return JSONResponse(
                status_code=400,
                content={
                    "error": "file_too_large",
                    "message": "Ukuran file maksimal 5MB.",
                },
            )
        if file.content_type != "application/pdf":
            print(f"ERROR 400: invalid_content_type ({file.content_type})")
            return JSONResponse(
                status_code=400,
                content={
                    "error": "invalid_pdf",
                    "message": "File harus berformat PDF.",
                },
            )

        # ── LANGKAH 4: Hitung hash SHA-256 ───────────────────────────────────
        file_hash = hashlib.sha256(file_bytes).hexdigest()

        # ── LANGKAH 5: Cek duplikat ──────────────────────────────────────────
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{PB_URL}/api/collections/submissions/records",
                headers={"Authorization": f"Bearer {admin_token}"},
                params={"filter": f'(file_hash="{file_hash}")'},
                timeout=10.0,
            )
        if r.json().get("totalItems", 0) > 0:
            return JSONResponse(
                status_code=409,
                content={
                    "error": "duplicate_file",
                    "message": "File ini sudah pernah dikumpulkan.",
                },
            )

        # ── LANGKAH 6: Hitung word count via PyMuPDF ─────────────────────────
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            text = " ".join(page.get_text() for page in doc)
            word_count = len(text.split())
        except Exception as e:
            # PDF corrupt atau tidak bisa dibaca oleh fitz
            print(f"ERROR 400: fitz parsing failed - {e}")
            return JSONResponse(
                status_code=400,
                content={
                    "error": "invalid_pdf",
                    "message": "File harus berformat PDF.",
                },
            )

        if word_count == 0:
            print("ERROR 400: empty_pdf (word_count = 0)")
            return JSONResponse(
                status_code=400,
                content={
                    "error": "empty_pdf",
                    "message": "PDF tidak mengandung teks yang bisa dibaca.",
                },
            )

        # ── LANGKAH 7: Hitung score ───────────────────────────────────────────
        score = 100 + (20 if word_count > 500 else 0)

        # ── LANGKAH 8: Simpan ke PocketBase ──────────────────────────────────
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{PB_URL}/api/collections/submissions/records",
                headers={"Authorization": f"Bearer {admin_token}"},
                data={
                    "user_id":     user_id,
                    "title":       title,
                    "description": description,
                    "file_hash":   file_hash,
                    "word_count":  str(word_count),
                    "score":       str(score),
                    "status":      "processed",
                },
                files={
                    "file": (file.filename, file_bytes, "application/pdf")
                },
                timeout=30.0,
            )
        r.raise_for_status()
        record_id = r.json()["id"]

        # ── LANGKAH 9: Kembalikan response sukses ─────────────────────────────
        return JSONResponse(
            status_code=200,
            content={
                "submission_id": record_id,
                "title":         title,
                "word_count":    word_count,
                "score":         score,
            },
        )

    # ── LANGKAH 10: Tangani semua exception ──────────────────────────────────
    except httpx.RequestError:
        return JSONResponse(
            status_code=500,
            content={
                "error": "server_error",
                "message": "Terjadi kesalahan. Coba lagi.",
            },
        )
    except httpx.HTTPStatusError as e:
        import traceback
        traceback.print_exc()
        print("Response text:", e.response.text if hasattr(e.response, 'text') else 'No response text')
        return JSONResponse(
            status_code=500,
            content={
                "error": "server_error",
                "message": f"Terjadi kesalahan: {str(e)}",
            },
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "error": "server_error",
                "message": f"Terjadi kesalahan: {str(e)}",
            },
        )
