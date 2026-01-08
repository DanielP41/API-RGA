
import hashlib
import json
import os
from typing import Optional, List
from langchain_core.embeddings import Embeddings

class EmbeddingCache:
    def __init__(self, cache_dir: str = "./data/embedding_cache"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
    
    def get_cache_key(self, text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()
    
    def get(self, text: str) -> Optional[List[float]]:
        key = self.get_cache_key(text)
        cache_file = os.path.join(self.cache_dir, f"{key}.json")
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                return json.load(f)
        return None
    
    def set(self, text: str, embedding: List[float]):
        key = self.get_cache_key(text)
        cache_file = os.path.join(self.cache_dir, f"{key}.json")
        with open(cache_file, 'w') as f:
            json.dump(embedding, f)

class CachedEmbeddings(Embeddings):
    """Wrapper to add caching to an embedding model"""
    def __init__(self, embedding_model: Embeddings, cache: EmbeddingCache):
        self.embedding_model = embedding_model
        self.cache = cache

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        embeddings = [None] * len(texts)
        texts_to_embed = []
        indices_to_embed = []

        # Check cache first
        for i, text in enumerate(texts):
            cached_embedding = self.cache.get(text)
            if cached_embedding:
                embeddings[i] = cached_embedding
            else:
                texts_to_embed.append(text)
                indices_to_embed.append(i)
        
        # Embed missing texts
        if texts_to_embed:
            new_embeddings = self.embedding_model.embed_documents(texts_to_embed)
            for i, embedding in zip(indices_to_embed, new_embeddings):
                embeddings[i] = embedding
                self.cache.set(texts[i], embedding)
        
        return embeddings

    def embed_query(self, text: str) -> List[float]:
        # Check cache
        cached_embedding = self.cache.get(text)
        if cached_embedding:
            return cached_embedding
        
        # Compute and cache
        embedding = self.embedding_model.embed_query(text)
        self.cache.set(text, embedding)
        return embedding
