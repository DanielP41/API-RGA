from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_query_endpoint_without_docs():
    # This should return 404 since no documents are uploaded yet
    response = client.post(
        "/api/v1/query",
        json={"question": "What is Python?", "max_results": 3}
    )
    assert response.status_code == 404
