from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime

# --- Upload & Basic ---

class DocumentUploadResponse(BaseModel):
    """Response model for document upload endpoint"""
    document_id: str = Field(..., description="Unique identifier for the uploaded document")
    filename: str = Field(..., description="Original filename of the uploaded document")
    chunks_created: int = Field(..., ge=0, description="Number of text chunks created from the document")
    status: str = Field(..., description="Upload status (success/error)")
    uploaded_at: datetime = Field(..., description="Timestamp of when the document was uploaded")

# --- Querying ---

class QueryRequest(BaseModel):
    """Request model for querying documents"""
    question: str = Field(
        ..., 
        min_length=3, 
        max_length=1000,
        description="The question to search for in the documents"
    )
    max_results: int = Field(
        default=3, 
        ge=1, 
        le=10,
        description="Maximum number of relevant documents to retrieve"
    )
    
    @field_validator('question')
    @classmethod
    def validate_question(cls, v: str) -> str:
        """Validate that question is not just whitespace"""
        if not v.strip():
            raise ValueError("La pregunta no puede estar vacía o contener solo espacios")
        if not v.strip():
            raise ValueError("La pregunta no puede estar vacía o contener solo espacios")
        return v.strip()

class ConversationMessage(BaseModel):
    role: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)

class ConversationQueryRequest(BaseModel):
    question: str = Field(..., min_length=3, description="La pregunta del usuario")
    conversation_id: Optional[str] = None
    history: List[ConversationMessage] = []
    max_results: int = Field(3, ge=1, le=10)

class SourceDocument(BaseModel):
    """Model for a source document fragment"""
    content: str = Field(..., description="Excerpt from the source document")
    metadata: dict = Field(..., description="Document metadata (filename, page, etc.)")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Relevance score (0-1)")

class QueryResponse(BaseModel):
    """Response model for document query endpoint"""
    answer: str = Field(..., description="Generated answer based on retrieved documents")
    sources: List[SourceDocument] = Field(..., description="List of source documents used")
    model_used: str = Field(..., description="LLM model used to generate the answer")
    tokens_used: Optional[int] = Field(None, ge=0, description="Number of tokens used (if available)")
    latency_ms: float = Field(..., ge=0, description="Response generation latency in milliseconds")

# --- Document Management ---

class DocumentInfo(BaseModel):
    """Detailed information about a document"""
    document_id: str
    filename: str
    uploaded_at: Optional[datetime] = None
    file_size_bytes: Optional[int] = None
    chunk_count: int
    tags: List[str] = []
    description: Optional[str] = None
    file_type: Optional[str] = None

class DocumentListResponse(BaseModel):
    """Response for listing documents"""
    documents: List[DocumentInfo]
    total_count: int

class DocumentDeleteResponse(BaseModel):
    """Response for document deletion"""
    document_id: str
    status: str
    message: str

class DocumentUpdateRequest(BaseModel):
    """Request to update document metadata"""
    tags: Optional[List[str]] = None
    description: Optional[str] = None

class DocumentUpdateResponse(BaseModel):
    """Response after updating document"""
    document_id: str
    status: str
    updated_fields: Dict[str, Any]

class DocumentSearchRequest(BaseModel):
    """Advanced search request"""
    query: Optional[str] = None
    tags: Optional[List[str]] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    file_type: Optional[str] = None

class DocumentSummaryResponse(BaseModel):
    """AI Generated summary of a document"""
    document_id: str
    summary: str
    model_used: str
