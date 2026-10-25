
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_cors_allows_only_the_deployed_vercel_frontend():
    response = client.options(
        "/repositories/validate",
        headers={
            "Origin": "https://repocheckk.vercel.app",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,x-repocheck-run-id",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://repocheckk.vercel.app"
    assert "access-control-allow-credentials" not in response.headers


def test_cors_does_not_allow_unconfigured_origins():
    response = client.options(
        "/repositories/validate",
        headers={
            "Origin": "https://attacker.example",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert "access-control-allow-origin" not in response.headers
