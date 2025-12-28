from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from openai import OpenAIError
from app.models.schemas import DocumentUploadResponse, QueryRequest, QueryResponse, SourceDocument
from app.services.document_processor import DocumentProcessor
from app.services.vector_store import VectorStoreService
from app.services.llm_service import LLMService
from app.core.config import get_settings
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
    settings.embedding_model,
    settings.openai_api_key
)
llm_service = LLMService(
    settings.model_name,
    settings.temperature,
    settings.max_tokens,
    settings.openai_api_key
)

@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """Sube y procesa un documento"""
    try:
        # Guardar archivo temporalmente
        upload_dir = "./data/uploads"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, file.filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Procesar documento
        doc_id, chunks = doc_processor.process_document(file_path, file.filename)
        
        # Agregar a vector store
        num_chunks = vector_store.add_documents(chunks)
        
        return DocumentUploadResponse(
            document_id=doc_id,
            filename=file.filename,
            chunks_created=num_chunks,
            status="success",
            uploaded_at=datetime.now()
        )
    
    except FileNotFoundError as e:
        logger.error(f"Archivo no encontrado: {str(e)}")
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    except Exception as e:
        logger.error(f"Error inesperado al subir documento: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    """Consulta los documentos usando RAG"""
    try:
        # Buscar documentos relevantes
        retrieved_docs = vector_store.similarity_search(
            request.question,
            k=request.max_results
        )
        
        if not retrieved_docs:
            raise HTTPException(
                status_code=404,
                detail="No se encontraron documentos relevantes"
            )
        
        # Generar respuesta
        answer, latency = llm_service.generate_answer(
            request.question,
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
    """Retorna estadísticas del sistema"""
    try:
        count = vector_store.vector_store._collection.count()
        return {
            "total_documents": count,
            "collection_name": settings.collection_name,
            "model": settings.model_name
        }
    except Exception as e:
        logger.error(f"Error al obtener estadísticas: {str(e)}")
        raise HTTPException(status_code=500, detail="Error al acceder a la base de datos de vectores")

@router.delete("/documents/reset")
async def reset_database():
    """Elimina todos los documentos (útil para desarrollo)"""
    try:
        vector_store.delete_collection()
        return {"message": "Base de datos reiniciada correctamente"}
    except Exception as e:
        logger.error(f"Error al reiniciar la base de datos: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
