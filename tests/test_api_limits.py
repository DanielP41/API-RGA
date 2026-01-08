
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from app.main import app
import pytest

client = TestClient(app)

def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_upload_invalid_extension():
    # Test uploading a file with an invalid extension
    files = {'file': ('test.exe', b"content", 'application/octet-stream')}
    response = client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 400
    assert "Formato no soportado" in response.json()['detail']

def test_query_validation_empty():
    # Test empty query
    response = client.post("/api/v1/query", json={"question": "", "max_results": 3})
    assert response.status_code == 422 # Pydantic validation error or custom 400 from validator?
    # The Pydantic model has min_length=3, so it might be 422. 
    # But routes.py also calls validate_query_text inside. 
    # Let's check what happens. Pydantic runs first.
    # If I send "   ", Pydantic might accept it (min_length=3 if it counts spaces), 
    # but validate_question validator in schema checks strip().
    
    # Update: Schema has @field_validator('question') which raises ValueError "La pregunta no puede estar vacía..."
    # Pydantic validation errors result in 422.
    assert response.status_code == 422

def test_query_validation_short():
    # Test short query
    response = client.post("/api/v1/query", json={"question": "ab", "max_results": 3})
    assert response.status_code == 422

@patch("app.api.routes.validate_upload_file")
def test_upload_too_large(mock_validate):
    # Mock validation to raise 413 (simulating large file without sending 35MB)
    mock_validate.side_effect = HTTPException(status_code=413, detail="Archivo muy grande")
    
    files = {'file': ('large.pdf', b"dummy content", 'application/pdf')}
    response = client.post("/api/v1/documents/upload", files=files)
    
    assert response.status_code == 413
    assert "Archivo muy grande" in response.json()['detail']

