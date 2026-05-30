"""CORS middleware tests — preflight handling for client → backend integration (#70)."""

from fastapi.testclient import TestClient

from app.main import _parse_cors_origins, app

client = TestClient(app)


# ── _parse_cors_origins ──────────────────────────────────────────────────────


def test_parse_origins_returns_dev_defaults_when_unset(monkeypatch) -> None:
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)

    origins = _parse_cors_origins()

    assert "http://localhost:3000" in origins
    assert "http://127.0.0.1:3000" in origins


def test_parse_origins_reads_comma_separated_env(monkeypatch) -> None:
    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS",
        "https://app.example.com,https://staging.example.com",
    )

    assert _parse_cors_origins() == [
        "https://app.example.com",
        "https://staging.example.com",
    ]


def test_parse_origins_trims_whitespace_and_drops_empty(monkeypatch) -> None:
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", " , https://a.com ,, https://b.com  ")

    assert _parse_cors_origins() == ["https://a.com", "https://b.com"]


# ── Preflight (OPTIONS) ──────────────────────────────────────────────────────


def test_preflight_signup_allowed_origin_returns_cors_headers() -> None:
    response = client.options(
        "/auth/signup",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert "POST" in response.headers.get("access-control-allow-methods", "")


def test_preflight_login_allowed_origin_returns_cors_headers() -> None:
    response = client.options(
        "/auth/login",
        headers={
            "Origin": "http://127.0.0.1:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:3000"


def test_preflight_disallowed_origin_omits_allow_origin_header() -> None:
    response = client.options(
        "/auth/signup",
        headers={
            "Origin": "http://evil.example.com",
            "Access-Control-Request-Method": "POST",
        },
    )

    # Starlette's CORSMiddleware still responds (HTTP 400 for a disallowed origin
    # on a preflight) but MUST NOT echo Access-Control-Allow-Origin.
    assert "access-control-allow-origin" not in response.headers
