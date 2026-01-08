from fastapi import APIRouter, HTTPException, Depends, Body, Query
from typing import List, Optional
from app.models.schemas import (
    DocumentListResponse, DocumentInfo, DocumentDeleteResponse,
    DocumentUpdateRequest, DocumentUpdateResponse, DocumentSearchRequest,
    DocumentSummaryResponse, QueryResponse
)
# Importar servicios desde routes.py para compartir instancias (Singleton-ish)
# Esto asume que main.py inicializa todo correctamente o que routes.py se carga
from app.api.routes import vector_store, llm_service
from app.utils.validators import ALLOWED_EXTENSIONS
import logging
from datetime import datetime

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/documents", response_model=DocumentListResponse)
async def list_documents():
    """Lista todos los documentos disponibles en el sistema"""
    try:
        docs = vector_store.get_all_documents()
        
        # Convertir a modelos Pydantic
        doc_infos = []
        for d in docs:
            # Asegurar que los campos existen
            doc_infos.append(DocumentInfo(
                document_id=d.get('document_id'),
                filename=d.get('filename'),
                uploaded_at=d.get('uploaded_at'),
                file_size_bytes=d.get('file_size'),
                chunk_count=d.get('chunk_count', 0),
                tags=d.get('tags', []),
                description=d.get('description'),
                file_type=d.get('file_type')
            ))
            
        return DocumentListResponse(
            documents=doc_infos,
            total_count=len(doc_infos)
        )
    except Exception as e:
        logger.error(f"Error al listar documentos: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents/stats/advanced")
async def get_advanced_stats():
    """Obtiene estadísticas detalladas del sistema"""
    try:
        docs = vector_store.get_all_documents()
        total_docs = len(docs)
        total_chunks = sum(d.get('chunk_count', 0) for d in docs)
        
        # Calcular estadísticas
        file_types = {}
        all_tags = []
        largest_docs = sorted(docs, key=lambda x: x.get('file_size', 0) or 0, reverse=True)[:5]
        
        for d in docs:
            ft = d.get('file_type', 'unknown')
            file_types[ft] = file_types.get(ft, 0) + 1
            if d.get('tags'):
                all_tags.extend(d.get('tags'))
                
        # Contar tags
        from collections import Counter
        tag_counts = Counter(all_tags).most_common(10)
        
        return {
            "total_documents": total_docs,
            "total_chunks": total_chunks,
            "avg_chunks_per_doc": round(total_chunks / total_docs, 2) if total_docs > 0 else 0,
            "file_type_distribution": file_types,
            "top_tags": [{"tag": t, "count": c} for t, c in tag_counts],
            "largest_documents": [
                {"filename": d.get('filename'), "size_mb": round((d.get('file_size', 0) or 0) / (1024*1024), 2)} 
                for d in largest_docs
            ]
        }
    except Exception as e:
        logger.error(f"Error al obtener estadísticas avanzadas: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents/{doc_id}", response_model=DocumentInfo)
async def get_document_details(doc_id: str):
    """Obtiene detalles de un documento específico"""
    doc = vector_store.get_document_by_id(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    
    return DocumentInfo(
        document_id=doc.get('document_id'),
        filename=doc.get('filename'),
        uploaded_at=doc.get('uploaded_at'),
        file_size_bytes=doc.get('file_size'),
        chunk_count=doc.get('chunk_count', 0),
        tags=doc.get('tags', []),
        description=doc.get('description'),
        file_type=doc.get('file_type')
    )

@router.delete("/documents/{doc_id}", response_model=DocumentDeleteResponse)
async def delete_document(doc_id: str):
    """Elimina un documento y sus chunks"""
    success = vector_store.delete_document_by_id(doc_id)
    if not success:
        raise HTTPException(status_code=404, detail="Documento no encontrado o no se pudo eliminar")
    
    return DocumentDeleteResponse(
        document_id=doc_id,
        status="success",
        message="Documento eliminado correctamente"
    )

@router.patch("/documents/{doc_id}", response_model=DocumentUpdateResponse)
async def update_document(doc_id: str, request: DocumentUpdateRequest):
    """Actualiza la metadata de un documento"""
    updates = {}
    if request.tags is not None:
        updates['tags'] = request.tags
    if request.description is not None:
        updates['description'] = request.description
        
    if not updates:
        raise HTTPException(status_code=400, detail="No se proporcionaron campos para actualizar")
        
    success = vector_store.update_document_metadata(doc_id, updates)
    if not success:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    
    return DocumentUpdateResponse(
        document_id=doc_id,
        status="success",
        updated_fields=updates
    )

@router.get("/documents/{doc_id}/content")
async def get_document_content_text(doc_id: str):
    """Recupera el contenido de texto del documento"""
    content = vector_store.get_document_content(doc_id)
    if not content:
        raise HTTPException(status_code=404, detail="Contenido no encontrado")
    return {"content": content}

@router.get("/documents/{doc_id}/summary", response_model=DocumentSummaryResponse)
async def generate_document_summary(doc_id: str):
    """Genera un resumen del documento usando IA"""
    content = vector_store.get_document_content(doc_id)
    if not content:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    
    # Limitar contenido para no exceder contexto
    max_chars = 10000
    if len(content) > max_chars:
        content = content[:max_chars] + "... (contenido truncado)"
    
    try:
        # Usar el LLM service para resumir
        # Hack: Usamos generate_answer enviando un prompt de resumen como 'query'
        prompt = "Genera un resumen conciso pero informativo de este documento. Destaca los puntos clave."
        
        # LLMService.generate_answer espera (query, relevant_docs)
        # Forjamos un 'doc' dummy para pasar el contenido
        from langchain.docstore.document import Document
        dummy_docs = [Document(page_content=content, metadata={})]
        
        summary, _ = llm_service.generate_answer(prompt, dummy_docs)
        
        return DocumentSummaryResponse(
            document_id=doc_id,
            summary=summary,
            model_used=llm_service.llm.model_name if hasattr(llm_service.llm, 'model_name') else "unknown"
        )
    except Exception as e:
        logger.error(f"Error generando resumen: {str(e)}")
        raise HTTPException(status_code=500, detail="Error generando resumen con IA")

@router.post("/documents/search", response_model=DocumentListResponse)
async def search_documents_advanced(request: DocumentSearchRequest):
    """Búsqueda avanzada de documentos (metadata + semántica)"""
    filters = {}
    if request.file_type:
        filters['file_type'] = request.file_type
    
    # Búsqueda semántica si hay query
    if request.query:
        results = vector_store.search_documents(request.query, filters=filters, k=10)
        
        # Extraer documentos únicos de los resultados
        unique_docs_map = {}
        for doc, score in results:
            doc_id = doc.metadata.get('document_id')
            if doc_id and doc_id not in unique_docs_map:
                # Recuperar info completa (los resultados de search pueden tener metadata incompleta si chroma recorta)
                full_doc = vector_store.get_document_by_id(doc_id)
                if full_doc:
                    unique_docs_map[doc_id] = DocumentInfo(
                        document_id=full_doc.get('document_id'),
                        filename=full_doc.get('filename'),
                        uploaded_at=full_doc.get('uploaded_at'),
                        file_size_bytes=full_doc.get('file_size'),
                        chunk_count=full_doc.get('chunk_count', 0),
                        tags=full_doc.get('tags', []),
                        description=full_doc.get('description'),
                        file_type=full_doc.get('file_type')
                    )
        
        docs = list(unique_docs_map.values())
    else:
        # Si no hay query, listar todos y filtrar en memoria por ahora (o mejorar vector_store.get_all con filtros)
        all_docs = await list_documents()
        docs = all_docs.documents
        # Aplicar filtros simples
        if request.file_type:
            docs = [d for d in docs if d.file_type == request.file_type]
        # Filtrar por tags (si se pide)
        if request.tags:
            docs = [d for d in docs if any(tag in d.tags for tag in request.tags)]

    return DocumentListResponse(
        documents=docs,
        total_count=len(docs)
    )
