from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form
from typing import Optional, List
from openai import OpenAIError
from app.models.schemas import DocumentUploadResponse, QueryRequest, QueryResponse, SourceDocument
from app.services.document_processor import DocumentProcessor
from app.services.vector_store import VectorStoreService
from app.services.llm_service import LLMService
from app.core.config import get_settings
from app.utils.validators import (
    validate_upload_file, 
    validate_query_text,
    get_file_info,
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE_MB
)
from datetime import datetime
import os
import shutil
import logging


logger = logging.getLogger(__name__)

router = APIRouter()
settings = get_settings()

# Inicializar servicios
doc_processor = DocumentProcessor(settings.chunk_size, settings.chunk_overlap)
vector_store = VectorStoreService(
    settings.chroma_persist_dir,
    settings.collection_name,
    settings.embedding_provider,
    openai_api_key=settings.openai_api_key,
    embedding_model=settings.embedding_model,
    local_model_name=settings.local_embedding_model
)

# Determinar API Key para el LLM según el proveedor
llm_api_key = settings.openai_api_key
if settings.llm_provider == "anthropic":
    llm_api_key = settings.anthropic_api_key
elif settings.llm_provider == "deepseek":
    llm_api_key = settings.deepseek_api_key

llm_service = LLMService(
    settings.llm_provider,
    settings.model_name,
    settings.temperature,
    settings.max_tokens,
    llm_api_key
)

@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    tags: Optional[str] = Form(None),
    description: Optional[str] = Form(None)
):
    """Sube y procesa un documento con validación completa"""
    try:
        # VALIDACIÓN MEJORADA EN BACKEND
        safe_filename = validate_upload_file(file)
        
        # Log de información del archivo
        file_info = get_file_info(file)
        logger.info(f"Procesando archivo: {file_info}")
        
        # Guardar archivo temporalmente
        upload_dir = "./data/uploads"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, safe_filename)
        
        # Guardar con manejo de errores mejorado
        try:
            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
        except Exception as e:
            logger.error(f"Error al guardar archivo: {str(e)}")
            raise HTTPException(status_code=500, detail="Error al guardar el archivo")
        
        # Procesar documento
        try:
            # Parsear tags
            tags_list = []
            if tags:
                tags_list = [tag.strip() for tag in tags.split(',') if tag.strip()]

            doc_id, chunks = doc_processor.process_document(
                file_path, 
                safe_filename,
                tags=tags_list,
                description=description
            )
        except ValueError as e:
            # Error de formato no soportado desde el procesador
            logger.error(f"Error de formato: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Error al procesar documento: {str(e)}")
            raise HTTPException(status_code=500, detail="Error al procesar el documento")
        
        # Agregar a vector store
        try:
            num_chunks = vector_store.add_documents(chunks)
        except Exception as e:
            logger.error(f"Error al agregar a vector store: {str(e)}")
            raise HTTPException(status_code=500, detail="Error al almacenar el documento")
        
        # Limpiar archivo temporal
        try:
            os.remove(file_path)
        except Exception as e:
            logger.warning(f"No se pudo eliminar archivo temporal: {str(e)}")
        
        logger.info(f"Documento procesado exitosamente: {safe_filename} ({num_chunks} chunks)")
        
        return DocumentUploadResponse(
            document_id=doc_id,
            filename=safe_filename,
            chunks_created=num_chunks,
            status="success",
            uploaded_at=datetime.now()
        )
    
    except HTTPException:
        raise
    except FileNotFoundError as e:
        logger.error(f"Archivo no encontrado: {str(e)}")
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    except Exception as e:
        logger.error(f"Error inesperado al subir documento: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error inesperado: {str(e)}")

@router.post("/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    """Consulta los documentos usando RAG con manejo de errores mejorado"""
    try:
        # Validar que haya documentos en la colección
        try:
            doc_count = vector_store.vector_store._collection.count()
            if doc_count == 0:
                raise HTTPException(
                    status_code=404,
                    detail="No hay documentos en la base de datos. Por favor, sube al menos un documento primero."
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error al verificar documentos: {str(e)}")
        
        # VALIDACIÓN DE CONSULTA
        try:
            sanitized_query = validate_query_text(request.question)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
            
        # Buscar documentos relevantes
        retrieved_docs = vector_store.similarity_search(
            sanitized_query,
            k=request.max_results
        )
        
        if not retrieved_docs:
            raise HTTPException(
                status_code=404,
                detail="No se encontraron documentos relevantes para tu consulta"
            )
        
        # Generar respuesta
        answer, latency = llm_service.generate_answer(
            sanitized_query,
            retrieved_docs
        )
        
        # Preparar fuentes
        sources = [
            SourceDocument(
                content=doc.page_content[:200] + "...",
                metadata=doc.metadata,
                relevance_score=float(score)
            )
            for doc, score in retrieved_docs
        ]
        
        return QueryResponse(
            answer=answer,
            sources=sources,
            model_used=settings.model_name,
            tokens_used=None,
            latency_ms=latency
        )
    
    except HTTPException:
        raise
    except OpenAIError as e:
        error_msg = str(e)
        user_friendly_msg = "Lo siento, hubo un error con el servicio de Inteligencia Artificial."
        
        if "insufficient_quota" in error_msg:
            user_friendly_msg = (
                "Tu saldo de OpenAI se ha agotado o el periodo de prueba ha expirado. "
                "Por favor, revisa tu factura y límites en https://platform.openai.com/account/billing."
            )
        elif "invalid_api_key" in error_msg:
            user_friendly_msg = (
                "La API Key de OpenAI no es válida. "
                "Por favor, verifica la configuración en tu archivo .env."
            )
        elif "rate_limit_exceeded" in error_msg:
            user_friendly_msg = (
                "Se ha superado el límite de velocidad de OpenAI. "
                "Por favor, espera un momento antes de volver a intentarlo."
            )
        
        logger.error(f"Error del LLM: {error_msg}")
        raise HTTPException(status_code=503, detail=user_friendly_msg)
    except Exception as e:
        logger.error(f"Error inesperado al consultar documentos: {type(e).__name__} - {str(e)}")
        raise HTTPException(status_code=500, detail="Ocurrió un error inesperado en el servidor.")

@router.get("/stats")
async def get_stats():
    """Retorna estadísticas del sistema con información adicional"""
    try:
        count = vector_store.vector_store._collection.count()
        
        # Obtener información adicional
        stats = {
            "total_documents": count,
            "total_chunks": count,  # En ChromaDB, cada documento es un chunk
            "collection_name": settings.collection_name,
            "model": settings.model_name,
            "llm_provider": settings.llm_provider,
            "embedding_provider": settings.embedding_provider,
            "max_file_size_mb": MAX_FILE_SIZE_MB,
            "allowed_formats": list(ALLOWED_EXTENSIONS)
        }
        
        return stats
    except Exception as e:
        logger.error(f"Error al obtener estadísticas: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al acceder a la base de datos de vectores")

@router.delete("/documents/reset")
async def reset_database():
    """Elimina todos los documentos (útil para desarrollo)"""
    try:
        vector_store.delete_collection()
        logger.info("Base de datos reiniciada correctamente")
        return {
            "message": "Base de datos reiniciada correctamente",
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Error al reiniciar la base de datos: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents/list")
async def list_documents():
    """Lista todos los documentos únicos en la base de datos"""
    try:
        # Obtener todos los metadatos
        collection = vector_store.vector_store._collection
        results = collection.get()
        
        # Extraer documentos únicos por filename
        unique_docs = {}
        if results and 'metadatas' in results:
            for metadata in results['metadatas']:
                filename = metadata.get('filename', 'Unknown')
                doc_id = metadata.get('document_id', 'Unknown')
                
                if filename not in unique_docs:
                    unique_docs[filename] = {
                        'filename': filename,
                        'document_id': doc_id,
                        'chunk_count': 1
                    }
                else:
                    unique_docs[filename]['chunk_count'] += 1
        
        return {
            "documents": list(unique_docs.values()),
            "total_unique_documents": len(unique_docs)
        }
    except Exception as e:
        logger.error(f"Error al listar documentos: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al listar documentos")
