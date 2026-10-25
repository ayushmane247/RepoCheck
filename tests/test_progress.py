from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.progress import publish_stage


client = TestClient(app)


def test_progress_endpoint_returns_only_server_published_stages():
    run_id = uuid4()
    assert client.get(f"/repositories/progress/{run_id}").status_code == 404

    publish_stage(run_id, "Running detected tests in the restricted Docker runner")
    response = client.get(f"/repositories/progress/{run_id}")

    assert response.status_code == 200
    assert response.json() == {
        "stage": "Running detected tests in the restricted Docker runner"
    }


def test_progress_endpoint_requires_a_valid_run_id():
    response = client.get("/repositories/progress/not-a-uuid")

    assert response.status_code == 422
