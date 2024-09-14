from fastapi.testclient import TestClient
from app import app  # Adjust this if your FastAPI instance is in a different file

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "active"}

def test_search():
    response = client.get("/search", params={"text": "example"})
    assert response.status_code == 200
    # Add more assertions based on expected output
