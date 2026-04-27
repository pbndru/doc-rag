# Document Search with Semantic RAG (On‑Premises)

A privacy‑first document search application for accountants and solicitors.  
Users can upload documents (PDF, DOCX, TXT), ask natural‑language questions via a chat UI, and receive relevant excerpts with highlighted source text.

## Key Features
- **Semantic search** using open‑source vector embeddings (Sentence‑Transformers)
- **On‑premises deployment** – no data leaves the server
- **Weaviate** as the local vector database
- **Chat interface** with document preview and text highlighting
- **Modular architecture** – separate services for processing, orchestration, and UI

## Technology Stack
| Layer | Technology |
|-------|------------|
| Embeddings | Sentence‑Transformers (`all‑MiniLM‑L6‑v2`) |
| Vector DB | Weaviate (Docker) |
| Document parsing | pdfplumber, python‑docx |
| Backend | FastAPI, Uvicorn |
| Frontend | React |
| Orchestration | Docker Compose |

## Quick Start
```bash
# Clone repository
git clone <repo>
cd doc-rag

# Start all services
docker-compose up --build -d

# Access the UI
open http://localhost:3000
```

See [SETUP.md](SETUP.md) for detailed installation steps and [API.md](API.md) for endpoint documentation.
