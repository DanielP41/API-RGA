
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app
import pytest

client = TestClient(app)

# Mocking the VectorStoreService and LLMService to avoid actual DB/LLM calls during tests
@pytest.fixture
def mock_vector_store():
    with patch("app.api.routes_documents.vector_store") as mock:
        yield mock

@pytest.fixture
def mock_llm_service():
    with patch("app.api.routes_documents.llm_service") as mock:
        yield mock

def test_list_documents(mock_vector_store):
    # Setup mock return
    mock_vector_store.get_all_documents.return_value = [
        {
            "document_id": "doc1",
            "filename": "test.pdf",
            "uploaded_at": "2024-01-01T12:00:00",
            "file_size": 1024,
            "chunk_count": 5,
            "tags": ["test"],
            "description": "A test doc",
            "file_type": ".pdf"
        }
    ]
    
    response = client.get("/api/v1/documents")
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 1
    assert data["documents"][0]["filename"] == "test.pdf"

def test_get_document_details(mock_vector_store):
    mock_vector_store.get_document_by_id.return_value = {
        "document_id": "doc1",
        "filename": "test.pdf",
        "uploaded_at": "2024-01-01T12:00:00",
        "file_size": 1024,
        "chunk_count": 5,
        "tags": ["test"],
        "description": "A test doc",
        "file_type": ".pdf"
    }
    
    response = client.get("/api/v1/documents/doc1")
    assert response.status_code == 200
    assert response.json()["document_id"] == "doc1"

def test_get_document_not_found(mock_vector_store):
    mock_vector_store.get_document_by_id.return_value = None
    response = client.get("/api/v1/documents/non_existent")
    assert response.status_code == 404

def test_update_document_metadata(mock_vector_store):
    mock_vector_store.update_document_metadata.return_value = True
    
    response = client.patch(
        "/api/v1/documents/doc1",
        json={"tags": ["new_tag"], "description": "Updated desc"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    mock_vector_store.update_document_metadata.assert_called_with(
        "doc1", {"tags": ["new_tag"], "description": "Updated desc"}
    )

def test_delete_document(mock_vector_store):
    mock_vector_store.delete_document_by_id.return_value = True
    
    response = client.delete("/api/v1/documents/doc1")
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_search_documents(mock_vector_store):
    # Mocking search results (list of tuples (doc, score))
    mock_doc = MagicMock()
    mock_doc.metadata = {
        "document_id": "doc1",
        "filename": "test.pdf"
    }
    mock_vector_store.search_documents.return_value = [(mock_doc, 0.9)]
    
    # Also need get_document_by_id for the full info retrieval in the route
    mock_vector_store.get_document_by_id.return_value = {
        "document_id": "doc1",
        "filename": "test.pdf",
        "file_type": ".pdf"
    }

    response = client.post(
        "/api/v1/documents/search",
        json={"query": "something", "file_type": ".pdf"}
    )
    assert response.status_code == 200
    assert len(response.json()["documents"]) == 1

def test_generate_summary(mock_vector_store, mock_llm_service):
    mock_vector_store.get_document_content.return_value = "Content of the document"
    mock_llm_service.generate_answer.return_value = ("Summary text", 100)
    mock_llm_service.llm.model_name = "gpt-4"
    
    response = client.get("/api/v1/documents/doc1/summary")
    assert response.status_code == 200
    assert response.json()["summary"] == "Summary text"

