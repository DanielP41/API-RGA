from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    app_name: str = "RAG Document API"
    app_version: str = "1.0.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    
    openai_api_key: str
    model_name: str = "gpt-3.5-turbo"
    embedding_model: str = "text-embedding-3-small"
    max_tokens: int = 1000
    temperature: float = 0.7
    
    chroma_persist_dir: str = "./data/chroma_db"
    collection_name: str = "documents"
    
    chunk_size: int = 1000
    chunk_overlap: int = 200
    
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()
