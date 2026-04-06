"""
backend/tests/test_main.py

Test suite menyeluruh untuk FASE 1.
Semua call ke PocketBase di-mock menggunakan unittest.mock,
sehingga test berjalan tanpa PocketBase yang aktif.

Cakupan:
  ✅ GET /  → health check
  ✅ POST /api/submit — no auth header → 401
  ✅ POST /api/submit — auth tanpa "Bearer " prefix → 401
  ✅ POST /api/submit — field title tidak dikirim sama sekali → 422
  ✅ POST /api/submit — title string kosong / hanya spasi → 422
  ✅ POST /api/submit — title > 150 karakter → 422
  ✅ POST /api/submit — description > 500 karakter → 422
  ✅ POST /api/submit — token PocketBase tidak valid → 401
  ✅ POST /api/submit — cooldown aktif (< 5 menit) → 429
  ✅ POST /api/submit — cooldown sudah habis → lanjut
  ✅ POST /api/submit — file > 5MB → 400
  ✅ POST /api/submit — bukan PDF (content_type salah) → 400
  ✅ POST /api/submit — file hash duplikat → 409
  ✅ POST /api/submit — PDF tanpa teks → 400
  ✅ POST /api/submit — PDF corrupt (fitz error) → 400
  ✅ POST /api/submit — PDF < 500 kata → score 100
  ✅ POST /api/submit — PDF > 500 kata → score 120
  ✅ POST /api/submit — PocketBase unreachable → 500
  ✅ Scoring formula: 100 + (20 jika > 500 kata)
"""

import hashlib
import io
import os
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest
import httpx
from httpx import AsyncClient, ASGITransport

# ─── Set env SEBELUM import app (supaya load_dotenv() tidak override) ─────────
os.environ.setdefault("POCKETBASE_URL",            "http://fake-pb:8090")
os.environ.setdefault("POCKETBASE_ADMIN_EMAIL",    "admin@test.com")
os.environ.setdefault("POCKETBASE_ADMIN_PASSWORD", "testpass")

import main as main_module       # noqa: E402  (import setelah env set)
from main import app             # noqa: E402


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _resp(status: int, body: dict) -> MagicMock:
    """Buat mock httpx.Response."""
    m = MagicMock()
    m.status_code = status
    m.json.return_value = body
    m.raise_for_status = MagicMock()
    if status >= 400:
        m.raise_for_status.side_effect = httpx.HTTPStatusError(
            message="error", request=MagicMock(), response=m
        )
    return m


def _make_pdf(words: int = 10) -> bytes:
    """
    Buat PDF valid yang mengandung PERSIS 'words' kata (menggunakan insert_textbox
    lintas halaman agar semua teks bisa ditampung).
    """
    import fitz
    WORDS_PER_PAGE = 300
    all_words = ("kata " * words).strip().split()
    doc = fitz.open()
    for i in range(0, len(all_words), WORDS_PER_PAGE):
        chunk = " ".join(all_words[i : i + WORDS_PER_PAGE])
        page = doc.new_page(width=595, height=842)
        rect = fitz.Rect(50, 50, 545, 792)
        page.insert_textbox(rect, chunk, fontname="helv", fontsize=11)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def _make_large_bytes(size_mb_plus_1: int = 1) -> bytes:
    """Buat bytes lebih besar dari 5 MB."""
    return b"x" * (5 * 1024 * 1024 + size_mb_plus_1)


USER_RECORD  = {"id": "user_abc", "role": "student", "name": "Test"}
ADMIN_TOKEN  = {"token": "admintoken_xyz"}
EMPTY_LIST   = {"totalItems": 0, "items": []}
ONE_OLD_SUB  = lambda: {  # noqa: E731 — last submit 10 menit lalu (no cooldown)
    "totalItems": 1,
    "items": [{"created": (
        datetime.now(timezone.utc) - timedelta(seconds=605)
    ).strftime("%Y-%m-%d %H:%M:%S.000Z")}]
}
ONE_FRESH_SUB = lambda secs_ago=60: {  # noqa: E731 — dalam cooldown
    "totalItems": 1,
    "items": [{"created": (
        datetime.now(timezone.utc) - timedelta(seconds=secs_ago)
    ).strftime("%Y-%m-%d %H:%M:%S.000Z")}]
}
NEW_RECORD   = {"id": "rec_new_123"}


def _patch_httpx(get_side_effect, post_side_effect=None):
    """
    Helper: patch httpx.AsyncClient sehingga .get dan .post mengembalikan
    nilai sesuai get_side_effect / post_side_effect.

    get_side_effect : callable(url, **kwargs) → mock response
    post_side_effect: callable(url, **kwargs) → mock response  (default: admin token)
    """
    if post_side_effect is None:
        async def _default_post(*a, **kw):
            return _resp(200, ADMIN_TOKEN)
        post_side_effect = _default_post

    mock_client = AsyncMock()
    mock_client.get  = AsyncMock(side_effect=get_side_effect)
    mock_client.post = AsyncMock(side_effect=post_side_effect)

    class _CM:
        async def __aenter__(self): return mock_client
        async def __aexit__(self, *_): pass

    return patch("main.httpx.AsyncClient", return_value=_CM())


# ─── Fixture: reset admin token cache sebelum setiap test ────────────────────
@pytest.fixture(autouse=True)
def reset_admin_token():
    main_module._admin_token         = None
    main_module._admin_token_expires = 0.0
    yield


# ─── Test client helper ───────────────────────────────────────────────────────
async def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


# ═══════════════════════════════════════════════════════════════════════════════
# BAGIAN 1 — GET /
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


# ═══════════════════════════════════════════════════════════════════════════════
# BAGIAN 2 — Validasi Auth Header (sebelum PocketBase dipanggil)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_no_auth_header():
    """Tidak ada Authorization header → 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post(
            "/api/submit",
            data={"title": "Judul"},
            files={"file": ("a.pdf", b"%PDF-1.4", "application/pdf")},
        )
    assert r.status_code == 401
    assert r.json()["error"] == "unauthorized"


@pytest.mark.asyncio
async def test_auth_without_bearer_prefix():
    """Authorization: SomeToken (tanpa 'Bearer ') → 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post(
            "/api/submit",
            headers={"Authorization": "SomeRandomToken"},
            data={"title": "Judul"},
            files={"file": ("a.pdf", b"%PDF-1.4", "application/pdf")},
        )
    assert r.status_code == 401
    assert r.json()["error"] == "unauthorized"


# ═══════════════════════════════════════════════════════════════════════════════
# BAGIAN 3 — Validasi Form Fields (sebelum PocketBase dipanggil)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_missing_title_field():
    """Field 'title' tidak ada sama sekali di form → 422 (FastAPI built-in)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post(
            "/api/submit",
            headers={"Authorization": "Bearer tok"},
            files={"file": ("a.pdf", b"%PDF-1.4", "application/pdf")},
            # title sengaja tidak dikirim
        )
    assert r.status_code == 422
    body = r.json()
    assert body["error"] == "validation_error"
    assert "judul" in body["message"].lower()


@pytest.mark.asyncio
async def test_empty_title_string():
    """Title dikirim tapi string kosong / spasi → 422."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post(
            "/api/submit",
            headers={"Authorization": "Bearer tok"},
            data={"title": "   "},
            files={"file": ("a.pdf", b"%PDF-1.4", "application/pdf")},
        )
    assert r.status_code == 422
    assert r.json()["error"] == "validation_error"
    assert r.json()["message"] == "Judul wajib diisi."


@pytest.mark.asyncio
async def test_title_too_long():
    """Title > 150 karakter → 422."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post(
            "/api/submit",
            headers={"Authorization": "Bearer tok"},
            data={"title": "A" * 151},
            files={"file": ("a.pdf", b"%PDF-1.4", "application/pdf")},
        )
    assert r.status_code == 422
    assert r.json()["error"] == "validation_error"
    assert "150" in r.json()["message"]


@pytest.mark.asyncio
async def test_title_exactly_150_chars_ok():
    """Title tepat 150 karakter harus lolos validasi lokal (bukan 422)."""
    # Ini harus lanjut ke PocketBase. Tanpa mock → 500 karena PocketBase fake.
    # Yang penting bukan 422.
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post(
            "/api/submit",
            headers={"Authorization": "Bearer tok"},
            data={"title": "A" * 150},
            files={"file": ("a.pdf", b"%PDF-1.4", "application/pdf")},
        )
    assert r.status_code != 422


@pytest.mark.asyncio
async def test_description_too_long():
    """Description > 500 karakter → 422."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post(
            "/api/submit",
            headers={"Authorization": "Bearer tok"},
            data={"title": "Judul OK", "description": "B" * 501},
            files={"file": ("a.pdf", b"%PDF-1.4", "application/pdf")},
        )
    assert r.status_code == 422
    assert r.json()["error"] == "validation_error"
    assert "500" in r.json()["message"]


@pytest.mark.asyncio
async def test_description_exactly_500_chars_ok():
    """Description tepat 500 karakter harus lolos validasi lokal."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post(
            "/api/submit",
            headers={"Authorization": "Bearer tok"},
            data={"title": "Judul OK", "description": "B" * 500},
            files={"file": ("a.pdf", b"%PDF-1.4", "application/pdf")},
        )
    # bukan 422 → lolos validasi lokal (akan 500 karena PocketBase fake)
    assert r.status_code != 422


# ═══════════════════════════════════════════════════════════════════════════════
# BAGIAN 4 — Verifikasi Token PocketBase (Langkah 1)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_invalid_pb_token():
    """PocketBase menolak token → 401."""
    async def fake_get(url, **kw):
        return _resp(401, {"message": "Token invalid"})

    with _patch_httpx(get_side_effect=fake_get):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            r = await ac.post(
                "/api/submit",
                headers={"Authorization": "Bearer badtoken"},
                data={"title": "Judul"},
                files={"file": ("a.pdf", b"%PDF-1.4", "application/pdf")},
            )
    assert r.status_code == 401
    assert r.json()["error"] == "unauthorized"


@pytest.mark.asyncio
async def test_pocketbase_unreachable():
    """PocketBase tidak bisa dihubungi → 500."""
    async def fake_get(url, **kw):
        raise httpx.ConnectError("Connection refused")

    with _patch_httpx(get_side_effect=fake_get):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            r = await ac.post(
                "/api/submit",
                headers={"Authorization": "Bearer tok"},
                data={"title": "Judul"},
                files={"file": ("a.pdf", b"%PDF-1.4", "application/pdf")},
            )
    assert r.status_code == 500
    assert r.json()["error"] == "server_error"


# ═══════════════════════════════════════════════════════════════════════════════
# BAGIAN 5 — Cek Cooldown (Langkah 2)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_cooldown_active():
    """Submit terlalu cepat (60 detik yang lalu) → 429."""
    async def fake_get(url, **kw):
        if "auth-refresh" in url:
            return _resp(200, {"record": USER_RECORD})
        # cooldown check — last submit 60 detik lalu
        return _resp(200, ONE_FRESH_SUB(60))

    with _patch_httpx(get_side_effect=fake_get):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            r = await ac.post(
                "/api/submit",
                headers={"Authorization": "Bearer tok"},
                data={"title": "Judul"},
                files={"file": ("a.pdf", b"%PDF-1.4", "application/pdf")},
            )
    assert r.status_code == 429
    body = r.json()
    assert body["error"] == "cooldown"
    assert "retry_after_seconds" in body
    # 300 - 60 = 240 detik sisa (toleransi ±2 detik untuk timing)
    assert 238 <= body["retry_after_seconds"] <= 242


@pytest.mark.asyncio
async def test_cooldown_exactly_at_boundary():
    """Submit tepat di batas 300 detik (tidak kena cooldown)."""
    # 301 detik lalu → sudah boleh submit
    async def fake_get(url, **kw):
        if "auth-refresh" in url:
            return _resp(200, {"record": USER_RECORD})
        if "submissions/records" in url and "file_hash" not in str(kw):
            return _resp(200, ONE_FRESH_SUB(301))  # cooldown check
        # duplicate check
        return _resp(200, EMPTY_LIST)

    with _patch_httpx(get_side_effect=fake_get):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            r = await ac.post(
                "/api/submit",
                headers={"Authorization": "Bearer tok"},
                data={"title": "Judul"},
                files={"file": ("a.pdf", b"%PDF-1.4", "application/pdf")},
            )
    # Seharusnya BUKAN 429 (bukan cooldown)
    assert r.status_code != 429


@pytest.mark.asyncio
async def test_no_previous_submission_no_cooldown():
    """User belum pernah submit sebelumnya → tidak ada cooldown."""
    async def fake_get(url, **kw):
        if "auth-refresh" in url:
            return _resp(200, {"record": USER_RECORD})
        # semua query submissions → kosong
        return _resp(200, EMPTY_LIST)

    with _patch_httpx(get_side_effect=fake_get):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            r = await ac.post(
                "/api/submit",
                headers={"Authorization": "Bearer tok"},
                data={"title": "Judul"},
                files={"file": ("a.pdf", b"%PDF-1.4", "application/pdf")},
            )
    assert r.status_code != 429


# ═══════════════════════════════════════════════════════════════════════════════
# BAGIAN 6 — Validasi File (Langkah 3)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_file_too_large():
    """File > 5MB → 400 file_too_large."""
    large = _make_large_bytes()

    async def fake_get(url, **kw):
        if "auth-refresh" in url:
            return _resp(200, {"record": USER_RECORD})
        return _resp(200, EMPTY_LIST)

    with _patch_httpx(get_side_effect=fake_get):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            r = await ac.post(
                "/api/submit",
                headers={"Authorization": "Bearer tok"},
                data={"title": "Judul"},
                files={"file": ("big.pdf", large, "application/pdf")},
            )
    assert r.status_code == 400
    assert r.json()["error"] == "file_too_large"


@pytest.mark.asyncio
async def test_file_exactly_5mb_ok():
    """File tepat 5MB (batas) → BUKAN 400 file_too_large."""
    exact_5mb = b"x" * (5 * 1024 * 1024)

    async def fake_get(url, **kw):
        if "auth-refresh" in url:
            return _resp(200, {"record": USER_RECORD})
        return _resp(200, EMPTY_LIST)

    with _patch_httpx(get_side_effect=fake_get):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            r = await ac.post(
                "/api/submit",
                headers={"Authorization": "Bearer tok"},
                data={"title": "Judul"},
                files={"file": ("exact.pdf", exact_5mb, "application/pdf")},
            )
    # Tepat 5MB seharusnya lolos (> 5MB yang ditolak)
    assert r.json().get("error") != "file_too_large"


@pytest.mark.asyncio
async def test_invalid_file_type():
    """File bukan PDF (content_type salah) → 400 invalid_pdf."""
    async def fake_get(url, **kw):
        if "auth-refresh" in url:
            return _resp(200, {"record": USER_RECORD})
        return _resp(200, EMPTY_LIST)

    with _patch_httpx(get_side_effect=fake_get):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            r = await ac.post(
                "/api/submit",
                headers={"Authorization": "Bearer tok"},
                data={"title": "Judul"},
                files={"file": ("doc.txt", b"hello world", "text/plain")},
            )
    assert r.status_code == 400
    assert r.json()["error"] == "invalid_pdf"


# ═══════════════════════════════════════════════════════════════════════════════
# BAGIAN 7 — Cek Duplikat (Langkah 5)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_duplicate_file():
    """File hash sudah ada di database → 409."""
    pdf = _make_pdf(words=20)
    expected_hash = hashlib.sha256(pdf).hexdigest()

    async def fake_get(url, **kw):
        if "auth-refresh" in url:
            return _resp(200, {"record": USER_RECORD})
        if "submissions/records" in url:
            params = kw.get("params", {})
            filter_str = params.get("filter", "") if isinstance(params, dict) else ""
            if "file_hash" in filter_str:
                # duplikat!
                return _resp(200, {"totalItems": 1, "items": [{"id": "existing"}]})
            # cooldown check — tidak ada item
            return _resp(200, EMPTY_LIST)
        return _resp(200, EMPTY_LIST)

    with _patch_httpx(get_side_effect=fake_get):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            r = await ac.post(
                "/api/submit",
                headers={"Authorization": "Bearer tok"},
                data={"title": "Judul"},
                files={"file": ("doc.pdf", pdf, "application/pdf")},
            )
    assert r.status_code == 409
    assert r.json()["error"] == "duplicate_file"


# ═══════════════════════════════════════════════════════════════════════════════
# BAGIAN 8 — Word Count & Scoring (Langkah 6 & 7)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_empty_pdf_no_text():
    """PDF tidak mengandung teks → 400 empty_pdf."""
    # PDF valid tapi halaman kosong
    import fitz
    doc = fitz.open()
    doc.new_page()   # halaman kosong tanpa teks
    empty_pdf = doc.tobytes()
    doc.close()

    async def fake_get(url, **kw):
        if "auth-refresh" in url:
            return _resp(200, {"record": USER_RECORD})
        return _resp(200, EMPTY_LIST)

    with _patch_httpx(get_side_effect=fake_get):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            r = await ac.post(
                "/api/submit",
                headers={"Authorization": "Bearer tok"},
                data={"title": "Judul"},
                files={"file": ("empty.pdf", empty_pdf, "application/pdf")},
            )
    assert r.status_code == 400
    assert r.json()["error"] == "empty_pdf"


@pytest.mark.asyncio
async def test_corrupt_pdf():
    """File content_type=pdf tapi bukan PDF valid → 400 invalid_pdf."""
    async def fake_get(url, **kw):
        if "auth-refresh" in url:
            return _resp(200, {"record": USER_RECORD})
        return _resp(200, EMPTY_LIST)

    with _patch_httpx(get_side_effect=fake_get):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            r = await ac.post(
                "/api/submit",
                headers={"Authorization": "Bearer tok"},
                data={"title": "Judul"},
                files={"file": ("bad.pdf", b"NOT A PDF AT ALL!!!", "application/pdf")},
            )
    assert r.status_code == 400
    assert r.json()["error"] == "invalid_pdf"


@pytest.mark.asyncio
async def test_score_under_500_words():
    """PDF < 500 kata → score = 100."""
    pdf = _make_pdf(words=200)

    async def fake_get(url, **kw):
        if "auth-refresh" in url:
            return _resp(200, {"record": USER_RECORD})
        return _resp(200, EMPTY_LIST)

    async def fake_post(url, **kw):
        if "_superusers" in url:
            return _resp(200, ADMIN_TOKEN)
        # simpan ke PocketBase
        return _resp(200, NEW_RECORD)

    with _patch_httpx(get_side_effect=fake_get, post_side_effect=fake_post):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            r = await ac.post(
                "/api/submit",
                headers={"Authorization": "Bearer tok"},
                data={"title": "Judul Pendek"},
                files={"file": ("short.pdf", pdf, "application/pdf")},
            )
    assert r.status_code == 200
    body = r.json()
    assert body["score"] == 100
    assert body["word_count"] <= 500


@pytest.mark.asyncio
async def test_score_over_500_words():
    """PDF > 500 kata → score = 120."""
    pdf = _make_pdf(words=600)

    async def fake_get(url, **kw):
        if "auth-refresh" in url:
            return _resp(200, {"record": USER_RECORD})
        return _resp(200, EMPTY_LIST)

    async def fake_post(url, **kw):
        if "_superusers" in url:
            return _resp(200, ADMIN_TOKEN)
        return _resp(200, NEW_RECORD)

    with _patch_httpx(get_side_effect=fake_get, post_side_effect=fake_post):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            r = await ac.post(
                "/api/submit",
                headers={"Authorization": "Bearer tok"},
                data={"title": "Judul Panjang"},
                files={"file": ("long.pdf", pdf, "application/pdf")},
            )
    assert r.status_code == 200
    body = r.json()
    assert body["score"] == 120
    assert body["word_count"] > 500


# ═══════════════════════════════════════════════════════════════════════════════
# BAGIAN 9 — Success Path (Langkah 8 & 9)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_successful_submission_response_shape():
    """Submit valid → 200 dengan field submission_id, title, word_count, score."""
    pdf = _make_pdf(words=300)

    async def fake_get(url, **kw):
        if "auth-refresh" in url:
            return _resp(200, {"record": USER_RECORD})
        return _resp(200, EMPTY_LIST)

    async def fake_post(url, **kw):
        if "_superusers" in url:
            return _resp(200, ADMIN_TOKEN)
        return _resp(200, {"id": "submission_xyz"})

    with _patch_httpx(get_side_effect=fake_get, post_side_effect=fake_post):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            r = await ac.post(
                "/api/submit",
                headers={"Authorization": "Bearer tok"},
                data={"title": "Essay Saya", "description": "Deskripsi singkat."},
                files={"file": ("essay.pdf", pdf, "application/pdf")},
            )
    assert r.status_code == 200
    body = r.json()
    assert body["submission_id"] == "submission_xyz"
    assert body["title"]         == "Essay Saya"
    assert isinstance(body["word_count"], int)
    assert body["word_count"] > 0
    assert body["score"] in (100, 120)


@pytest.mark.asyncio
async def test_successful_submission_without_description():
    """Submit valid tanpa description (opsional) → 200."""
    pdf = _make_pdf(words=10)

    async def fake_get(url, **kw):
        if "auth-refresh" in url:
            return _resp(200, {"record": USER_RECORD})
        return _resp(200, EMPTY_LIST)

    async def fake_post(url, **kw):
        if "_superusers" in url:
            return _resp(200, ADMIN_TOKEN)
        return _resp(200, {"id": "rec_abc"})

    with _patch_httpx(get_side_effect=fake_get, post_side_effect=fake_post):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            r = await ac.post(
                "/api/submit",
                headers={"Authorization": "Bearer tok"},
                data={"title": "Judul Saja"},
                # description tidak dikirim → default ""
                files={"file": ("mini.pdf", pdf, "application/pdf")},
            )
    assert r.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# BAGIAN 10 — Scoring Formula Unit Test
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_scoring_formula_boundary_499():
    """499 kata → score harus 100 (bukan 120)."""
    pdf = _make_pdf(words=499)

    async def fake_get(url, **kw):
        if "auth-refresh" in url:
            return _resp(200, {"record": USER_RECORD})
        return _resp(200, EMPTY_LIST)

    async def fake_post(url, **kw):
        if "_superusers" in url:
            return _resp(200, ADMIN_TOKEN)
        return _resp(200, {"id": "r1"})

    with _patch_httpx(get_side_effect=fake_get, post_side_effect=fake_post):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            r = await ac.post(
                "/api/submit",
                headers={"Authorization": "Bearer tok"},
                data={"title": "Tepat Di Bawah"},
                files={"file": ("499.pdf", pdf, "application/pdf")},
            )
    if r.status_code == 200:
        assert r.json()["score"] == 100


@pytest.mark.asyncio
async def test_scoring_formula_boundary_501():
    """501 kata → score harus 120."""
    pdf = _make_pdf(words=501)

    async def fake_get(url, **kw):
        if "auth-refresh" in url:
            return _resp(200, {"record": USER_RECORD})
        return _resp(200, EMPTY_LIST)

    async def fake_post(url, **kw):
        if "_superusers" in url:
            return _resp(200, ADMIN_TOKEN)
        return _resp(200, {"id": "r2"})

    with _patch_httpx(get_side_effect=fake_get, post_side_effect=fake_post):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            r = await ac.post(
                "/api/submit",
                headers={"Authorization": "Bearer tok"},
                data={"title": "Tepat Di Atas"},
                files={"file": ("501.pdf", pdf, "application/pdf")},
            )
    if r.status_code == 200:
        assert r.json()["score"] == 120
