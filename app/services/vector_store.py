from langchain_community.vectorstores import Chroma
from typing import List, Dict, Optional, Any
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class VectorStoreService:
    def __init__(self, persist_dir: str, collection_name: str, embedding_provider: str, 
                 openai_api_key: str = None, embedding_model: str = None, local_model_name: str = None):
        
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        
        if embedding_provider == "openai":
            from langchain_openai import OpenAIEmbeddings
            self.embeddings = OpenAIEmbeddings(model=embedding_model, openai_api_key=openai_api_key)
        elif embedding_provider == "local":
            from langchain_huggingface import HuggingFaceEmbeddings
            logger.info(f"Usando modelo de embeddings local: {local_model_name}")
            self.embeddings = HuggingFaceEmbeddings(model_name=local_model_name)
        else:
            raise ValueError(f"Proveedor de embeddings no soportado: {embedding_provider}")
            
        self.vector_store = None
        self._initialize_store()
    
    def _initialize_store(self):
        """Inicializa o carga el vector store"""
        logger.info(f"Inicializando Vector Store en {self.persist_dir}")
        self.vector_store = Chroma(
            collection_name=self.collection_name,
            embedding_function=self.embeddings,
            persist_directory=self.persist_dir
        )
    
    def add_documents(self, chunks):
        """Agrega documentos al vector store"""
        try:
            logger.info(f"Agregando {len(chunks)} chunks al vector store")
            self.vector_store.add_documents(chunks)
            return len(chunks)
        except Exception as e:
            logger.error(f"Error crítico al agregar documentos al vector store: {str(e)}", exc_info=True)
            raise RuntimeError(f"Error interno al guardar en la base de datos de vectores. Detalles: {str(e)}")
    
    def similarity_search(self, query: str, k: int = 3, filter: Optional[Dict] = None):
        """Busca documentos similares"""
        try:
            logger.info(f"Buscando documentos similares para: {query}")
            results = self.vector_store.similarity_search_with_score(query, k=k, filter=filter)
            return results
        except Exception as e:
            logger.error(f"Error crítico en búsqueda de similitud: {str(query)} - Error: {str(e)}", exc_info=True)
            raise RuntimeError(f"Error al buscar documentos relevantes. Por favor, intente de nuevo más tarde.")
    
    def delete_collection(self):
        """Elimina la colección completa"""
        self.vector_store.delete_collection()
        self._initialize_store() # Re-initialize after deletion

    def get_all_documents(self) -> List[Dict]:
        """Obtiene una lista de todos los documentos únicos"""
        try:
            collection = self.vector_store._collection
            # Obtener solo metadatas para ser más rápido
            data = collection.get(include=['metadatas'])
            
            unique_docs = {}
            if data and 'metadatas' in data and data['metadatas']:
                for metadata in data['metadatas']:
                    doc_id = metadata.get('document_id')
                    if not doc_id:
                        continue
                        
                    if doc_id not in unique_docs:
                        unique_docs[doc_id] = {
                            "document_id": doc_id,
                            "filename": metadata.get('filename'),
                            "uploaded_at": metadata.get('uploaded_at'),
                            "file_size": metadata.get('file_size'),
                            "file_type": metadata.get('file_type'),
                            "tags": metadata.get('tags', '').split(',') if metadata.get('tags') else [],
                            "description": metadata.get('description'),
                            "chunk_count": 1
                        }
                    else:
                        unique_docs[doc_id]["chunk_count"] += 1
            
            return list(unique_docs.values())
        except Exception as e:
            logger.error(f"Error al listar documentos: {str(e)}")
            return []

    def get_document_by_id(self, doc_id: str) -> Optional[Dict]:
        """Obtiene detalles de un documento específico"""
        try:
            results = self.vector_store._collection.get(
                where={"document_id": doc_id},
                include=['metadatas']
            )
            
            if not results['metadatas']:
                return None
                
            # Tomar metadata del primer chunk
            metadata = results['metadatas'][0]
            
            return {
                "document_id": doc_id,
                "filename": metadata.get('filename'),
                "uploaded_at": metadata.get('uploaded_at'),
                "file_size": metadata.get('file_size'),
                "file_type": metadata.get('file_type'),
                "tags": metadata.get('tags', '').split(',') if metadata.get('tags') else [],
                "description": metadata.get('description'),
                "chunk_count": len(results['metadatas'])
            }
        except Exception as e:
            logger.error(f"Error al obtener documento {doc_id}: {str(e)}")
            return None

    def delete_document_by_id(self, doc_id: str) -> bool:
        """Elimina un documento por su ID"""
        try:
            # En ChromaDB se elimina pasando un filtro 'where'
            self.vector_store._collection.delete(
                where={"document_id": doc_id}
            )
            return True
        except Exception as e:
            logger.error(f"Error al eliminar documento {doc_id}: {str(e)}")
            return False

    def update_document_metadata(self, doc_id: str, updates: Dict[str, Any]) -> bool:
        """Actualiza la metadata de un documento"""
        try:
            # 1. Obtener todos los IDs de los chunks
            results = self.vector_store._collection.get(
                where={"document_id": doc_id},
                include=['metadatas']
            )
            
            if not results['ids']:
                return False
            
            ids = results['ids']
            current_metadatas = results['metadatas']
            
            # 2. Preparar nuevas metadatas combinando existentes con actualizaciones
            new_metadatas = []
            for meta in current_metadatas:
                new_meta = meta.copy()
                # Convertir lista de tags a string si es necesario, Chroma solo guarda tipos simples
                for k, v in updates.items():
                    if k == 'tags' and isinstance(v, list):
                        new_meta[k] = ','.join(v)
                    else:
                        new_meta[k] = v
                new_metadatas.append(new_meta)
            
            # 3. Actualizar
            self.vector_store._collection.update(
                ids=ids,
                metadatas=new_metadatas
            )
            return True
        except Exception as e:
            logger.error(f"Error al actualizar metadata de {doc_id}: {str(e)}")
            return False

    def get_document_content(self, doc_id: str) -> str:
        """Reconstruye el contenido completo de un documento"""
        try:
            results = self.vector_store._collection.get(
                where={"document_id": doc_id},
                include=['documents', 'metadatas']
            )
            
            if not results['documents']:
                return ""
            
            # Unir chunks. Idealmente ordenaríamos por índice si tuviéramos 'chunk_index'
            # Por ahora unimos en el orden que devuelve la DB (que no garantiza orden original)
            # Mejoras futuras: guardar 'chunk_index' en metadata
            
            # Intentar ordenar si existe chunk_index
            chunks = zip(results['documents'], results['metadatas'])
            sorted_chunks = sorted(chunks, key=lambda x: x[1].get('chunk_index', 0) if x[1] else 0)
            
            return "\n\n".join([c[0] for c in sorted_chunks])
        except Exception as e:
            logger.error(f"Error al obtener contenido de {doc_id}: {str(e)}")
            return ""

    def search_documents(self, query: str = None, filters: Dict = None, k: int = 5):
        """Búsqueda avanzada de documentos"""
        try:
            # Construir filtro de Chroma
            where_filter = {}
            if filters:
                formatted_filters = []
                for key, value in filters.items():
                    if value is not None:
                        # Manejo especial para tags (búsqueda parcial no soportada nativamente en 'where' simple)
                        # Chroma 'where' es coincidencia exacta para strings
                        if key == 'tags_contains': 
                            # Esto es complejo en Chroma sin un operador 'contains'. 
                            # Por simplicidad, filtramos post-retrieval o asumimos direct match si fuera un solo tag.
                            # Para esta implementación, usaremos metadata exacta si se provee, o ignoramos.
                            pass
                        elif key == 'file_type':
                            formatted_filters.append({"file_type": value})
                        # Date filter logic would go here (complex in Chroma)
                
                if len(formatted_filters) == 1:
                    where_filter = formatted_filters[0]
                elif len(formatted_filters) > 1:
                    where_filter = {"$and": formatted_filters}

            if query:
                return self.vector_store.similarity_search_with_score(
                    query, 
                    k=k, 
                    filter=where_filter if where_filter else None
                )
            else:
                # Si no hay query, quizás solo devolver metadatos filtrados?
                # Chroma similarity_search requiere query.
                return []
        except Exception as e:
            logger.error(f"Error en búsqueda avanzada: {str(e)}")
            return []
