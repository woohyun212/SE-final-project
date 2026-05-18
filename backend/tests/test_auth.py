import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
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


def test_signup_success(client: TestClient) -> None:
    res = client.post("/auth/signup", json={"email": "test@example.com", "password": "Password1"})
    assert res.status_code == 201
    body = res.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_signup_duplicate_email(client: TestClient) -> None:
    payload = {"email": "dup@example.com", "password": "Password1"}
    client.post("/auth/signup", json=payload)
    res = client.post("/auth/signup", json=payload)
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

    client.post("/auth/signup", json={"email": "cost@example.com", "password": "Password1"})

    db = TestingSessionLocal()
    user = db.query(User).filter(User.email == "cost@example.com").first()
    db.close()

    assert user is not None
    assert user.hashed_password.startswith("$2b$12$")
