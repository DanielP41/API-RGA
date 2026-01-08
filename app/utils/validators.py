"""
Utilidades de validación para la aplicación RAG
"""
import os
import re
from typing import Set
from fastapi import HTTPException, UploadFile
import logging

logger = logging.getLogger(__name__)

# Configuración de validación
ALLOWED_EXTENSIONS: Set[str] = {'.pdf', '.txt', '.md', '.epub', '.xlsx', '.xls'}
MAX_FILE_SIZE_MB: int = 35
MAX_FILE_SIZE_BYTES: int = MAX_FILE_SIZE_MB * 1024 * 1024
MIN_FILE_SIZE_BYTES: int = 10  # Mínimo 10 bytes

# Caracteres peligrosos en nombres de archivo
DANGEROUS_FILENAME_CHARS = r'[<>:"|?*\x00-\x1f]'


def sanitize_filename(filename: str) -> str:
    """
    Sanitiza el nombre de archivo removiendo caracteres peligrosos
    
    Args:
        filename: Nombre de archivo original
        
    Returns:
        Nombre de archivo sanitizado
    """
    # Remover caracteres peligrosos
    safe_name = re.sub(DANGEROUS_FILENAME_CHARS, '_', filename)
    
    # Remover espacios múltiples
    safe_name = re.sub(r'\s+', '_', safe_name)
    
    # Limitar longitud del nombre
    name, ext = os.path.splitext(safe_name)
    if len(name) > 200:
        name = name[:200]
    
    return f"{name}{ext}"


def validate_file_extension(filename: str) -> str:
    """
    Valida que la extensión del archivo sea permitida
    
    Args:
        filename: Nombre del archivo
        
    Returns:
        Extensión del archivo (lowercase)
        
    Raises:
        HTTPException: Si la extensión no es válida
    """
    filename_lower = filename.lower()
    file_ext = os.path.splitext(filename_lower)[1]
    
    if not file_ext:
        raise HTTPException(
            status_code=400,
            detail="El archivo debe tener una extensión válida"
        )
    
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Formato no soportado: {file_ext}. Formatos válidos: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )
    
    return file_ext


def validate_file_size(file: UploadFile) -> None:
    """
    Valida que el tamaño del archivo esté dentro de los límites
    
    Args:
        file: Archivo subido
        
    Raises:
        HTTPException: Si el tamaño no es válido
    """
    if not hasattr(file, 'size') or file.size is None:
        logger.warning(f"No se pudo verificar el tamaño del archivo: {file.filename}")
        return
    
    # Validar archivo vacío
    if file.size < MIN_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"El archivo está vacío o es demasiado pequeño (mínimo: {MIN_FILE_SIZE_BYTES} bytes)"
        )
    
    # Validar tamaño máximo
    if file.size > MAX_FILE_SIZE_BYTES:
        size_mb = file.size / (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"Archivo muy grande ({size_mb:.2f} MB). Máximo permitido: {MAX_FILE_SIZE_MB} MB"
        )


def validate_filename(filename: str) -> str:
    """
    Valida y sanitiza el nombre del archivo
    
    Args:
        filename: Nombre del archivo original
        
    Returns:
        Nombre de archivo válido y sanitizado
        
    Raises:
        HTTPException: Si el nombre del archivo no es válido
    """
    if not filename or not filename.strip():
        raise HTTPException(
            status_code=400,
            detail="El nombre del archivo no puede estar vacío"
        )
    
    # Sanitizar nombre
    safe_filename = sanitize_filename(filename)
    
    # Validar que después de sanitizar no esté vacío
    if not safe_filename or safe_filename == '.':
        raise HTTPException(
            status_code=400,
            detail="El nombre del archivo no es válido"
        )
    
    return safe_filename


def validate_upload_file(file: UploadFile) -> str:
    """
    Validación completa de archivo subido
    
    Args:
        file: Archivo subido por el usuario
        
    Returns:
        Nombre de archivo sanitizado y validado
        
    Raises:
        HTTPException: Si cualquier validación falla
    """
    # Validar que el archivo existe
    if not file:
        raise HTTPException(
            status_code=400,
            detail="No se proporcionó ningún archivo"
        )
    
    # Validar y sanitizar nombre
    safe_filename = validate_filename(file.filename)
    
    # Validar extensión
    validate_file_extension(safe_filename)
    
    # Validar tamaño
    validate_file_size(file)
    
    logger.info(f"Archivo validado correctamente: {safe_filename}")
    
    return safe_filename


def validate_query_text(query: str, min_length: int = 3, max_length: int = 1000) -> str:
    """
    Valida el texto de una consulta
    
    Args:
        query: Texto de la consulta
        min_length: Longitud mínima permitida
        max_length: Longitud máxima permitida
        
    Returns:
        Texto de consulta sanitizado
        
    Raises:
        ValueError: Si la consulta no es válida
    """
    if not query:
        raise ValueError("La consulta no puede estar vacía")
    
    query_stripped = query.strip()
    
    if len(query_stripped) < min_length:
        raise ValueError(f"La consulta es muy corta (mínimo: {min_length} caracteres)")
    
    if len(query_stripped) > max_length:
        raise ValueError(f"La consulta es muy larga (máximo: {max_length} caracteres)")
    
    return query_stripped


def get_file_info(file: UploadFile) -> dict:
    """
    Obtiene información detallada del archivo para logging
    
    Args:
        file: Archivo subido
        
    Returns:
        Diccionario con información del archivo
    """
    info = {
        "filename": file.filename,
        "content_type": file.content_type,
        "size_bytes": getattr(file, 'size', None),
    }
    
    if info["size_bytes"]:
        info["size_mb"] = round(info["size_bytes"] / (1024 * 1024), 2)
    
    _, ext = os.path.splitext(file.filename.lower())
    info["extension"] = ext
    
    return info
