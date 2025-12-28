from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    chunks_created: int
    status: str
    uploaded_at: datetime

class QueryRequest(BaseModel):
    question: str
    max_results: int = 3
    
class SourceDocument(BaseModel):
    content: str
    metadata: dict
    relevance_score: float

class QueryResponse(BaseModel):
    answer: str
    sources: List[SourceDocument]
    model_used: str
    tokens_used: Optional[int]
    latency_ms: float
