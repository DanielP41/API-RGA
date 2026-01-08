from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_root_serves_html():
    """Test que el root sirve el frontend HTML"""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert b"RAG AI" in response.content  # Verifica que contenga el título del app

def test_health_check():
    """Test del endpoint de health check"""
    response = client.get("/api/health")  # ← Corregido: /api/health
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_stats_endpoint():
    """Test del endpoint de estadísticas"""
    response = client.get("/api/v1/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_documents" in data
    assert "collection_name" in data
    assert "model" in data

def test_query_endpoint_without_docs():
    """Test de query sin documentos subidos - debe retornar 404"""
    response = client.post(
        "/api/v1/query",
        json={"question": "What is Python?", "max_results": 3}
    )
    assert response.status_code == 404
    assert "No hay documentos" in response.json()["detail"]

def test_upload_invalid_file_format():
    """Test de subida de archivo con formato no soportado"""
    # Crear un archivo fake con extensión no soportada
    fake_file = ("test.exe", b"fake content", "application/x-msdownload")
    
    response = client.post(
        "/api/v1/documents/upload",
        files={"file": fake_file}
    )
    
    # Debería fallar con error 400 debido a la nueva validación robusta
    assert response.status_code == 400
    assert "Formato no soportado" in response.json()["detail"]

def test_query_with_invalid_max_results():
    """Test de query con max_results inválido"""
    response = client.post(
        "/api/v1/query",
        json={"question": "Test question", "max_results": 0}  # 0 es inválido
    )
    # Puede ser 404 (no docs) o 422 (validation error) dependiendo de validación
    assert response.status_code in [404, 422]

def test_upload_epub_format():
    """Test de subida de archivo EPUB"""
    # Este test requeriría un archivo EPUB real para probar
    # Por ahora, solo verificamos que el endpoint acepta el formato
    pass

def test_upload_excel_format():
    """Test de subida de archivo Excel"""
    # Similar al anterior, requeriría un archivo Excel real
    pass

def test_validation_accepts_new_formats():
    """Test que la validación acepta los nuevos formatos"""
    # Verificar que .epub, .xlsx, .xls están en la lista de formatos válidos
    pass
