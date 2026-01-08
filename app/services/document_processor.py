from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader, UnstructuredExcelLoader
import os
import uuid
import logging
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
from typing import List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class DocumentProcessor:
    def __init__(self, chunk_size: int, chunk_overlap: int):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
        )
    
    def _extract_epub_text(self, file_path: str) -> str:
        """Extrae texto de un archivo EPUB"""
        try:
            book = epub.read_epub(file_path)
            chapters = []
            
            for item in book.get_items():
                if item.get_type() == ebooklib.ITEM_DOCUMENT:
                    try:
                        # Parsear HTML del capítulo
                        soup = BeautifulSoup(item.get_content(), 'html.parser')
                        text = soup.get_text()
                        if text.strip():
                            chapters.append(text.strip())
                    except Exception as e:
                        logger.warning(f"Error al extraer texto de capítulo en EPUB: {str(e)}")
            
            if not chapters:
                raise ValueError("No se pudo extraer texto legible del EPUB")
                
            return '\n\n'.join(chapters)
        except Exception as e:
            logger.error(f"Error al procesar EPUB {file_path}: {str(e)}", exc_info=True)
            raise ValueError(f"Error al procesar el archivo EPUB. El archivo podría estar corrupto o no ser válido. Detalles: {str(e)}")
    
    def load_document(self, file_path: str, filename: str):
        """Carga un documento según su extensión"""
        ext = os.path.splitext(filename)[1].lower()
        
        logger.info(f"Cargando documento: {filename}")
        
        try:
            if ext == '.pdf':
                loader = PyPDFLoader(file_path)
                return loader.load()
                
            elif ext in ['.txt', '.md']:
                loader = TextLoader(file_path, encoding='utf-8')
                return loader.load()
                
            elif ext == '.epub':
                # Procesar EPUB
                text = self._extract_epub_text(file_path)
                from langchain.docstore.document import Document
                return [Document(page_content=text, metadata={"source": filename})]
                
            elif ext in ['.xlsx', '.xls']:
                loader = UnstructuredExcelLoader(file_path, mode="elements")
                return loader.load()
                
            else:
                logger.error(f"Formato no soportado: {ext}")
                raise ValueError(f"Formato no soportado: {ext}. Formatos válidos: PDF, TXT, MD, EPUB, XLSX, XLS")
        except Exception as e:
            logger.error(f"Error fatal al cargar {filename}: {str(e)}", exc_info=True)
            if isinstance(e, ValueError):
                raise
            raise ValueError(f"No se pudo leer el archivo '{filename}'. Asegúrese de que el formato sea correcto y el archivo no esté protegido. Error: {str(e)}")
    
    def process_document(self, file_path: str, filename: str, tags: List[str] = None, description: str = None):
        """Procesa un documento y lo divide en chunks con metadata enriquecida"""
        logger.info(f"Iniciando procesamiento de {filename}")
        
        # Cargar documento
        documents = self.load_document(file_path, filename)
        
        # Obtener tamaño del archivo
        file_size = os.path.getsize(file_path)
        file_type = os.path.splitext(filename)[1].lower()
        
        # Generar ID único para el documento
        doc_id = str(uuid.uuid4())
        uploaded_at = datetime.now().isoformat()
        
        # Dividir en chunks
        chunks = self.text_splitter.split_documents(documents)
        total_chunks = len(chunks)
        
        # Agregar metadata a cada chunk
        for i, chunk in enumerate(chunks):
            chunk.metadata['document_id'] = doc_id
            chunk.metadata['filename'] = filename
            chunk.metadata['chunk_index'] = i
            chunk.metadata['total_chunks'] = total_chunks
            chunk.metadata['uploaded_at'] = uploaded_at
            chunk.metadata['file_size'] = file_size
            chunk.metadata['file_type'] = file_type
            
            if tags:
                # ChromaDB prefiere tipos simples en metadata
                chunk.metadata['tags'] = ",".join(tags)
            
            if description:
                chunk.metadata['description'] = description
        
        # Validar que se generaron chunks
        if not chunks:
            logger.error(f"No se generó contenido para el documento: {filename}")
            raise ValueError(f"El documento '{filename}' no produjo ningún texto procesable.")
            
        logger.info(f"Documento procesado: {len(chunks)} chunks creados con ID {doc_id}")
        
        return doc_id, chunks
