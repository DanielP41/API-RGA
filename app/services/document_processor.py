from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader
import os
import uuid
import logging

logger = logging.getLogger(__name__)

class DocumentProcessor:
    def __init__(self, chunk_size: int, chunk_overlap: int):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
        )
    
    def load_document(self, file_path: str, filename: str):
        """Carga un documento según su extensión"""
        ext = os.path.splitext(filename)[1].lower()
        
        logger.info(f"Cargando documento: {filename}")
        if ext == '.pdf':
            loader = PyPDFLoader(file_path)
        elif ext in ['.txt', '.md']:
            loader = TextLoader(file_path)
        else:
            logger.error(f"Formato no soportado: {ext}")
            raise ValueError(f"Formato no soportado: {ext}")
        
        return loader.load()
    
    def process_document(self, file_path: str, filename: str):
        """Procesa un documento y lo divide en chunks"""
        logger.info(f"Iniciando procesamiento de {filename}")
        # Cargar documento
        documents = self.load_document(file_path, filename)
        
        # Generar ID único para el documento
        doc_id = str(uuid.uuid4())
        
        # Agregar metadata
        for doc in documents:
            doc.metadata['document_id'] = doc_id
            doc.metadata['filename'] = filename
        
        # Dividir en chunks
        chunks = self.text_splitter.split_documents(documents)
        logger.info(f"Documento procesado: {len(chunks)} chunks creados con ID {doc_id}")
        
        return doc_id, chunks
