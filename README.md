# RAG Document API 🚀

A high-performance RESTful API built with FastAPI and LangChain for querying technical documents. This system implements Retrieval-Augmented Generation (RAG) to provide context-aware answers from your own files.

## 🌟 Key Features

- **Multi-Provider Support**: Choose your "brain" (OpenAI, Anthropic Claude, DeepSeek, or Ollama).
- **Local Embeddings**: Option to use local HuggingFace models for 100% privacy and zero cost.
- **Multiple File Formats**: PDF, TXT, Markdown, EPUB (eBooks), and Excel (XLSX/XLS).
- **Modern Interface**: Dark-themed "Glassmorphism" UI with real-time statistics.
- **Asynchronous Processing**: Efficient document chunking and vector storage (ChromaDB).
- **Full Dockerization**: Simple deployment with a single command.

## 🎨 Modern Frontend

The project includes a sleek, responsive dashboard where you can:
- Upload files (PDF, TXT, MD, EPUB, XLSX, XLS) via drag-and-drop.
- Chat with your documents using context-aware AI.
- Monitor system stats like processed documents and active models.

## 🛠️ Project Structure

- `app/api/`: API routes and logic.
- `app/services/`: Core logic (LLM, Document Processing, Vector Store).
- `app/static/`: Frontend (HTML, CSS, JS).
- `app/core/`: Configuration via environment variables.

## 🚀 Quick Start

### 1. Prerequisites
- Docker and Docker Compose.
- (Optional) API Keys for OpenAI, Anthropic, or DeepSeek.

### 2. Configuration (`.env`)
Create a `.env` file based on `.env.example`:

```env
LLM_PROVIDER=openai
EMBEDDING_PROVIDER=local
OPENAI_API_KEY=sk-...
```

### 3. Deployment
```bash
docker-compose up -d --build
```
Access the UI at: **http://localhost:8000**

## 🔧 Supported Providers

| Provider | Type | Variable |
| :--- | :--- | :--- |
| **OpenAI** | LLM/Embed | `OPENAI_API_KEY` |
| **Anthropic** | LLM | `ANTHROPIC_API_KEY` |
| **DeepSeek** | LLM | `DEEPSEEK_API_KEY` |
| **Ollama** | LLM (Local) | N/A (Server running) |
| **Local** | Embed | N/A (Downloaded automatically) |

## 🛣️ Endpoints Principales

- `GET /api/health`: Estado de salud de la API.
- `GET /api/v1/stats`: Estadísticas del sistema (documentos y modelo activo).
- `POST /api/v1/documents/upload`: Sube y procesa un documento.
- `POST /api/v1/query`: Consulta RAG sobre los documentos.
- `DELETE /api/v1/documents/reset`: Reinicia la base de datos vectorial.

## 🧪 Pruebas (Testing)

El proyecto incluye una suite de pruebas para verificar la integridad de la API. Para ejecutarlas localmente:

```bash
pytest tests/test_api.py
```

*Nota: Asegúrate de tener las dependencias instaladas (`pip install -r requirements.txt`).*

## 🛠️ Technical Stack

- **API**: FastAPI
- **LLM/RAG**: LangChain
- **Vector DB**: ChromaDB
- **Models**: OpenAI GPT, Claude 3.5, DeepSeek-V3, HuggingFace
- **Testing**: PyTest
