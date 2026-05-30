from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_hello_world() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}
