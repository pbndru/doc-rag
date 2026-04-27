# Architecture Overview

## System Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        User (Browser)                      │
│                   http://localhost:3000                     │
└───────────────────────────┬─────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Chat UI (React)                          │
│                  frontend/chat-ui                            │
│  - ChatInterface.js: chat window + document viewer          │
│  - Sends queries to orchestrator /query endpoint           │
└───────────────────────────┬─────────────────────────────┘
                            │ HTTP (REACT_APP_API_URL)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  Orchestrator (FastAPI)                      │
│                services/orchestrator                        │
│  POST /upload → forwards file to document-processor        │
│  POST /query  → queries Weaviate, returns answer+citations  │
└───────┬───────────────────────────────┬───────────────────┘
        │                              │
        ▼                              ▼
┌───────────────────┐      ┌──────────────────────────────────┐
│ Document Processor│      │   Weaviate Vector DB (port 8080) │
│ (FastAPI + ML)    │      │   - Stores text chunks + vectors │
│ - Extract text    │      │   - Semantic similarity search    │
│ - Generate embeddings│    │   - Persists to ./weaviate-data  │
│ - Send to Weaviate│      └──────────────────────────────────┘
└───────────────────┘
```

## Component Details

### 1. Chat UI (React)
- **Port**: 3000
- **Tech**: React, Axios
- **Role**: User-facing chat interface. Displays conversation, allows file uploads, shows document snippets with clickable citations that open a document viewer with highlighted text.

### 2. Orchestrator (FastAPI)
- **Port**: 8000
- **Tech**: FastAPI, httpx
- **Role**: Central coordinator. Forwards document uploads to the processor, sends user queries to Weaviate, formats responses with citations for the UI.

### 3. Document Processor (FastAPI)
- **Port**: 8001
- **Tech**: FastAPI, Sentence-Transformers, pdfplumber, python-docx
- **Role**: Extracts text from uploaded documents (PDF, DOCX, TXT), chunks the text, generates vector embeddings using `all-MiniLM-L6-v2`, and stores them in Weaviate via its REST API.

### 4. Weaviate Vector Database
- **Port**: 8080
- **Tech**: Weaviate (official Docker image)
- **Role**: Stores document chunks as vectors. Provides semantic search via GraphQL API. Data persists in `./weaviate-data` volume.

## Data Flow

1. **Upload**: User uploads document → UI → Orchestrator → Document Processor → Weaviate
2. **Query**: User asks question → UI → Orchestrator → Weaviate (semantic search) → Orchestrator (format) → UI (display answer + citations)
3. **View**: User clicks citation → UI opens document viewer with relevant text highlighted

## Privacy Guarantee
All components run on-premises. No external API calls are made. Vector embeddings and document text never leave the server.
