from langchain_community.vectorstores import Chroma
from typing import List
import logging

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
        logger.info(f"Agregando {len(chunks)} chunks al vector store")
        self.vector_store.add_documents(chunks)
        return len(chunks)
    
    def similarity_search(self, query: str, k: int = 3):
        """Busca documentos similares"""
        logger.info(f"Buscando documentos similares para: {query}")
        results = self.vector_store.similarity_search_with_score(query, k=k)
        return results
    
    def delete_collection(self):
        """Elimina la colección completa"""
        self.vector_store.delete_collection()
        self._initialize_store() # Re-initialize after deletion
