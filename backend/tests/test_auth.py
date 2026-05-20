import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.models import token as _token_models  # noqa: F401
from app.routers.auth import router

SQLITE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLITE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    from fastapi import FastAPI

    test_app = FastAPI()
    test_app.include_router(router)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    test_app.dependency_overrides[get_db] = override_get_db

    with TestClient(test_app) as c:
        yield c


# ── helpers ──────────────────────────────────────────────────────────────────

def _signup(client: TestClient, email: str = "test@example.com", password: str = "Password1") -> dict:
    res = client.post("/auth/signup", json={"email": email, "password": password})
    assert res.status_code == 201
    return res.json()


def _login(client: TestClient, email: str = "test@example.com", password: str = "Password1") -> dict:
    res = client.post("/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200
    return res.json()


# ── signup ────────────────────────────────────────────────────────────────────

def test_signup_success(client: TestClient) -> None:
    body = _signup(client)
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"


def test_signup_duplicate_email(client: TestClient) -> None:
    _signup(client)
    res = client.post("/auth/signup", json={"email": "test@example.com", "password": "Password1"})
    assert res.status_code == 409


def test_signup_invalid_email(client: TestClient) -> None:
    res = client.post("/auth/signup", json={"email": "not-an-email", "password": "Password1"})
    assert res.status_code == 422


def test_signup_weak_password_too_short(client: TestClient) -> None:
    res = client.post("/auth/signup", json={"email": "test@example.com", "password": "abc"})
    assert res.status_code == 422


def test_signup_weak_password_no_digit(client: TestClient) -> None:
    res = client.post("/auth/signup", json={"email": "test@example.com", "password": "onlyletters"})
    assert res.status_code == 422


def test_signup_weak_password_no_letter(client: TestClient) -> None:
    res = client.post("/auth/signup", json={"email": "test@example.com", "password": "12345678"})
    assert res.status_code == 422


def test_bcrypt_cost(client: TestClient) -> None:
    """bcrypt hash가 cost 12 prefix($2b$12$)로 저장되는지 확인."""
    from app.models.user import User

    _signup(client)

    db = TestingSessionLocal()
    user = db.query(User).filter(User.email == "test@example.com").first()
    db.close()

    assert user is not None
    assert user.hashed_password.startswith("$2b$12$")


# ── login ─────────────────────────────────────────────────────────────────────

def test_login_success(client: TestClient) -> None:
    _signup(client)
    body = _login(client)
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"


def test_login_wrong_password(client: TestClient) -> None:
    _signup(client)
    res = client.post("/auth/login", json={"email": "test@example.com", "password": "WrongPass1"})
    assert res.status_code == 401


def test_login_nonexistent_email(client: TestClient) -> None:
    res = client.post("/auth/login", json={"email": "nobody@example.com", "password": "Password1"})
    assert res.status_code == 401


def test_login_wrong_and_right_same_message(client: TestClient) -> None:
    """이메일 미존재와 비밀번호 불일치가 동일한 에러 메시지를 반환해야 한다."""
    _signup(client)
    res_wrong_pw = client.post("/auth/login", json={"email": "test@example.com", "password": "Wrong123"})
    res_no_user = client.post("/auth/login", json={"email": "ghost@example.com", "password": "Password1"})
    assert res_wrong_pw.json()["detail"] == res_no_user.json()["detail"]


# ── refresh ───────────────────────────────────────────────────────────────────

def test_refresh_success(client: TestClient) -> None:
    tokens = _signup(client)
    res = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert res.status_code == 200
    body = res.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_refresh_token_is_rotated(client: TestClient) -> None:
    """refresh 후 기존 refresh token은 재사용 불가해야 한다."""
    tokens = _signup(client)
    client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    res = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert res.status_code == 401


def test_refresh_invalid_token(client: TestClient) -> None:
    res = client.post("/auth/refresh", json={"refresh_token": "totally-invalid-token"})
    assert res.status_code == 401


# ── logout ────────────────────────────────────────────────────────────────────

def test_logout_success(client: TestClient) -> None:
    tokens = _signup(client)
    res = client.post(
        "/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert res.status_code == 204


def test_logout_invalidates_refresh_token(client: TestClient) -> None:
    tokens = _signup(client)
    client.post(
        "/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    res = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert res.status_code == 401


def test_logout_without_token(client: TestClient) -> None:
    tokens = _signup(client)
    res = client.post("/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    assert res.status_code == 403
