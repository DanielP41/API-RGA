"""
Tests para el módulo de validadores
"""
import pytest
from fastapi import HTTPException, UploadFile
from app.utils.validators import (
    sanitize_filename,
    validate_file_extension,
    validate_filename,
    validate_query_text,
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE_MB,
    MAX_FILE_SIZE_BYTES
)
from io import BytesIO


class TestSanitizeFilename:
    """Tests para sanitize_filename"""
    
    def test_remove_dangerous_chars(self):
        """Debe remover caracteres peligrosos"""
        assert sanitize_filename("file<>.txt") == "file__.txt"
        assert sanitize_filename('file:name|?.pdf') == "file_name__.pdf"
    
    def test_remove_multiple_spaces(self):
        """Debe convertir espacios múltiples en guiones bajos"""
        assert sanitize_filename("my    file.txt") == "my_file.txt"
        assert sanitize_filename("test  document.pdf") == "test_document.pdf"
    
    def test_limit_name_length(self):
        """Debe limitar la longitud del nombre"""
        long_name = "a" * 300 + ".txt"
        result = sanitize_filename(long_name)
        assert len(result) <= 205  # 200 chars + ".txt"
    
    def test_preserve_valid_names(self):
        """Debe preservar nombres válidos"""
        assert sanitize_filename("document.pdf") == "document.pdf"
        assert sanitize_filename("my_file_123.txt") == "my_file_123.txt"


class TestValidateFileExtension:
    """Tests para validate_file_extension"""
    
    def test_valid_extensions(self):
        """Debe aceptar extensiones válidas"""
        for ext in ALLOWED_EXTENSIONS:
            filename = f"test{ext}"
            assert validate_file_extension(filename) == ext
    
    def test_case_insensitive(self):
        """Debe ser case-insensitive"""
        assert validate_file_extension("TEST.PDF") == ".pdf"
        assert validate_file_extension("document.TXT") == ".txt"
    
    def test_invalid_extension(self):
        """Debe rechazar extensiones no válidas"""
        with pytest.raises(HTTPException) as exc_info:
            validate_file_extension("test.exe")
        assert exc_info.value.status_code == 400
        assert "Formato no soportado" in exc_info.value.detail
    
    def test_no_extension(self):
        """Debe rechazar archivos sin extensión"""
        with pytest.raises(HTTPException) as exc_info:
            validate_file_extension("noextension")
        assert exc_info.value.status_code == 400


class TestValidateFilename:
    """Tests para validate_filename"""
    
    def test_valid_filename(self):
        """Debe aceptar nombres válidos"""
        result = validate_filename("document.pdf")
        assert result == "document.pdf"
    
    def test_empty_filename(self):
        """Debe rechazar nombres vacíos"""
        with pytest.raises(HTTPException) as exc_info:
            validate_filename("")
        assert exc_info.value.status_code == 400
        
        with pytest.raises(HTTPException) as exc_info:
            validate_filename("   ")
        assert exc_info.value.status_code == 400
    
    def test_sanitize_dangerous_chars(self):
        """Debe sanitizar caracteres peligrosos"""
        result = validate_filename("dan<ger>ous.pdf")
        assert "<" not in result
        assert ">" not in result


class TestValidateQueryText:
    """Tests para validate_query_text"""
    
    def test_valid_query(self):
        """Debe aceptar consultas válidas"""
        result = validate_query_text("¿Qué es Python?")
        assert result == "¿Qué es Python?"
    
    def test_empty_query(self):
        """Debe rechazar consultas vacías"""
        with pytest.raises(ValueError) as exc_info:
            validate_query_text("")
        assert "vacía" in str(exc_info.value)
    
    def test_too_short_query(self):
        """Debe rechazar consultas muy cortas"""
        with pytest.raises(ValueError) as exc_info:
            validate_query_text("ab")
        assert "muy corta" in str(exc_info.value)
    
    def test_too_long_query(self):
        """Debe rechazar consultas muy largas"""
        long_query = "a" * 1001
        with pytest.raises(ValueError) as exc_info:
            validate_query_text(long_query)
        assert "muy larga" in str(exc_info.value)
    
    def test_strip_whitespace(self):
        """Debe eliminar espacios al inicio y final"""
        result = validate_query_text("   test query   ")
        assert result == "test query"


class TestConstants:
    """Tests para constantes de configuración"""
    
    def test_allowed_extensions(self):
        """Debe tener las extensiones esperadas"""
        expected = {'.pdf', '.txt', '.md', '.epub', '.xlsx', '.xls'}
        assert ALLOWED_EXTENSIONS == expected
    
    def test_max_file_size(self):
        """Debe tener el tamaño máximo correcto"""
        assert MAX_FILE_SIZE_MB == 35
        assert MAX_FILE_SIZE_BYTES == 35 * 1024 * 1024
