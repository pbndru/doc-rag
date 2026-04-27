# API Specification

## Base URLs
| Service | URL |
|---------|-----|
| Orchestrator | `http://localhost:8000` |
| Document Processor | `http://localhost:8001` |
| Weaviate (Vector DB) | `http://localhost:8080` |
| Chat UI | `http://localhost:3000` |

---

## 1. Orchestrator Endpoints (Main API for UI)

### `POST /upload`
Upload a document for processing and indexing.

**Request** – `multipart/form-data`
```
file: <PDF/DOCX/TXT file>
```

**Response** (200 OK)
```json
{
  "status": "uploaded",
  "detail": {
    "status": "processed",
    "chunks": 42
  }
}
```

---

### `POST /query`
Ask a natural‑language question; returns answer with citations.

**Request** (JSON)
```json
{
  "query": "What are the penalties for late filing?"
}
```

**Response** (200 OK)
```json
{
  "answer": "According to the document, penalties include a fine of up to £1000...",
  "citations": [
    {
      "filename": "tax-guide.pdf",
      "snippet": "Penalties for late filing include a fixed penalty of £100..."
    }
  ]
}
```

---

## 2. Document Processor Endpoints (Internal)

### `POST /ingest`
Process an uploaded document, generate embeddings, and store in Weaviate.

**Request** – `multipart/form-data`
```
file: <PDF/DOCX/TXT file>
```

**Response** (200 OK)
```json
{
  "status": "processed",
  "chunks": 42,
  "pages": 15
}
```

---

## 3. Weaviate Vector DB (Internal)

### GraphQL Query Endpoint
`POST http://localhost:8080/v1/graphql`

**Example query** (semantic search)
```graphql
{
  Get {
    Document(
      nearText: { concepts: ["penalties for late filing"] }
      limit: 5
    ) {
      title
      content
      _additional {
        distance
      }
    }
  }
}
```

**Response**
```json
{
  "data": {
    "Get": {
      "Document": [
        {
          "title": "tax-guide.pdf",
          "content": "Penalties for late filing include...",
          "_additional": { "distance": 0.123 }
        }
      ]
    }
  }
}
```

### REST – Add Object
`POST http://localhost:8080/v1/objects`
```json
{
  "class": "Document",
  "properties": {
    "title": "tax-guide.pdf",
    "content": "Full text chunk...",
    "chunkIndex": 3
  }
}
```

---

## Error Codes
| Code | Meaning |
|------|---------|
| 400  | Bad request (missing parameters) |
| 500  | Internal server error |
| 502  | Bad gateway (upstream service unreachable) |

## Authentication
All services currently run with anonymous access (`AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED: "true"` in Weaviate). For production, add API keys or mTLS.
