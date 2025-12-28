# RAG Document API

A high-performance RESTful API built with FastAPI and LangChain for querying technical documents. This system implements Retrieval-Augmented Generation (RAG) to provide context-aware answers based on uploaded PDF, TXT, or Markdown files.

## Key Features

- Asynchronous document processing and chunking.
- Vector storage using ChromaDB for efficient similarity search.
- Integration with OpenAI GPT-3.5-turbo and text embeddings.
- Automated API documentation via Swagger UI.
- Fully containerized environment with Docker and Docker Compose.

## Project Structure

- `app/api/`: API endpoints and routing logic.
- `app/core/`: Configuration and environment settings.
- `app/models/`: Pydantic schemas for data validation.
- `app/services/`: Core logic for document processing, LLM integration, and vector storage.
- `data/`: Persistent storage for uploaded files and the vector database.

## Installation and Setup

### Prerequisites

- Docker and Docker Compose installed on the host system.
- An OpenAI API Key.

### Environment Configuration

1. Create a `.env` file in the root directory.
2. Define the following variable (refer to `.env.example` for additional settings):
   ```env
   OPENAI_API_KEY=your_api_key_here
   ```

### Running with Docker

Execute the following command to build and start the repository:

```bash
docker-compose up --build -d
```

The API will be accessible at `http://localhost:8000`.

## API Documentation

Once the services are running, interactive documentation is available at:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Principal Endpoints

- `GET /health`: Returns the health status of the API.
- `POST /api/v1/documents/upload`: Uploads and processes a new document.
- `POST /api/v1/query`: Performs a search and generates a response based on the query.
- `DELETE /api/v1/documents/reset`: Clears the vector database collection.

## Technical Stack

- **Framework**: FastAPI
- **Orchestration**: LangChain
- **Vector Database**: ChromaDB
- **LLM**: OpenAI GPT models
- **Environment**: Docker
