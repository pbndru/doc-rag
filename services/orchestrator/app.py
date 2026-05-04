import os
import json
import httpx
import numpy as np
from fastapi import FastAPI, UploadFile, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sentence_transformers import SentenceTransformer, util

app = FastAPI()

# Load sentence transformer model (same as document-processor)
model = SentenceTransformer('all-MiniLM-L6-v2')

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DOC_PROCESSOR_URL = os.getenv("DOC_PROCESSOR_URL", "http://document-processor:8001")
VECTOR_DB_URL = os.getenv("VECTOR_DB_URL", "http://vector-db:8080")

# -------------------------------------------------------------------
# Ensure Weaviate schema exists (create if needed)
# -------------------------------------------------------------------
@app.on_event("startup")
async def startup():
    async with httpx.AsyncClient() as client:
        # Define class Document if not present
        class_obj = {
            "class": "Document",
            "properties": [
                {"name": "title", "dataType": ["text"]},
                {"name": "content", "dataType": ["text"]},
                {"name": "chunkIndex", "dataType": ["int"]}
            ]
        }
        try:
            resp = await client.post(f"{VECTOR_DB_URL}/v1/schema", json=class_obj)
            # 422 means it already exists
            if resp.status_code != 422:
                resp.raise_for_status()
        except Exception as e:
            print(f"Schema creation info: {e}")
            pass

import asyncio

# Global set to track processed files in this session to avoid redundant checks
# In a production app, this would be persisted or checked against the DB
processed_files = set()

async def check_if_file_exists_in_db(filename: str, client: httpx.AsyncClient) -> bool:
    """Query Weaviate to see if this document already has any chunks."""
    graphql_query = {
        "query": f'{{ Get {{ Document(where: {{ path: ["title"], operator: Equal, valueText: "{filename}" }}, limit: 1) {{ title }} }} }}'
    }
    try:
        resp = await client.post(f"{VECTOR_DB_URL}/v1/graphql", json=graphql_query)
        if resp.status_code == 200:
            data = resp.json()
            hits = data.get("data", {}).get("Get", {}).get("Document", [])
            return len(hits) > 0
    except Exception:
        pass
    return False

async def ingest_file(filename: str, client: httpx.AsyncClient):
    """Send a single file to the document-processor."""
    filepath = os.path.join("documents", filename)
    try:
        with open(filepath, "rb") as f:
            files = {"file": (filename, f, "application/octet-stream")}
            resp = await client.post(f"{DOC_PROCESSOR_URL}/ingest", files=files)
            resp.raise_for_status()
            print(f"Successfully ingested {filename}")
            processed_files.add(filename)
    except Exception as e:
        print(f"Failed to ingest {filename}: {e}")

@app.on_event("startup")
async def start_document_watcher():
    """Background task that polls the documents folder."""
    async def watcher():
        while True:
            try:
                async with httpx.AsyncClient() as client:
                    docs_path = os.path.abspath("documents")
                    if os.path.isdir(docs_path):
                        for filename in os.listdir(docs_path):
                            if filename.startswith('.'): continue
                            
                            # Skip if already processed in this session
                            if filename in processed_files:
                                continue
                                
                            # Check DB if not sure
                            if await check_if_file_exists_in_db(filename, client):
                                processed_files.add(filename)
                                continue
                                
                            # New file! Ingest it
                            await ingest_file(filename, client)
            except Exception as e:
                print(f"Watcher error: {e}")
            
            # Check every 10 seconds
            await asyncio.sleep(10)
    
    # Run watcher as a background task
    asyncio.create_task(watcher())

# -------------------------------------------------------------------
# On startup, ingest all files present in the ``documents`` folder.
# This replaces the manual ``/upload`` endpoint – files added to ``/documents``
# on the host are automatically processed when the service starts.
# -------------------------------------------------------------------
# (Removing the old ingest_documents_on_startup as the watcher handles it now)

# -------------------------------------------------------------------
# Query – search the vector store (Weaviate)
# -------------------------------------------------------------------
@app.post("/query")
async def query_documents(query: dict):
    user_query = query.get("query")
    if not user_query:
        raise HTTPException(status_code=400, detail="Query string missing")
    async with httpx.AsyncClient() as client:
        try:
            # Compute query vector with same model used by document-processor
            embedding = model.encode([user_query])[0].tolist()
            vector_str = json.dumps(embedding)
            graphql_query = (
                '{ Get { Document (nearVector: { vector: ' + vector_str + ' } limit: 5) { '
                'title content chunkIndex _additional { distance } } } }'
            )
            resp = await client.post(
                f"{VECTOR_DB_URL}/v1/graphql",
                json={"query": graphql_query}
            )
            resp.raise_for_status()
            data = resp.json()
            if "errors" in data:
                raise HTTPException(status_code=500, detail=str(data["errors"]))
            hits = data.get("data", {}).get("Get", {}).get("Document", [])
            
            if not hits:
                return {"answer": "I couldn't find any relevant information in the documents.", "citations": []}

            # Smart Snippet Extraction:
            # Instead of dumping all chunks, let's find the most relevant sentences.
            all_content = "\n".join([hit.get("content", "") for hit in hits[:3]])
            # Simple sentence splitting
            sentences = [s.strip() for s in all_content.replace('\n', ' ').split('. ') if len(s.strip()) > 10]
            
            if sentences:
                query_embedding = model.encode(user_query, convert_to_tensor=True)
                sentence_embeddings = model.encode(sentences, convert_to_tensor=True)
                cosine_scores = util.cos_sim(query_embedding, sentence_embeddings)[0]
                
                # Get indices of top 3 sentences
                top_results = np.argpartition(-cosine_scores.cpu(), range(min(len(sentences), 3)))[:3]
                relevant_sentences = [sentences[i] for i in top_results if cosine_scores[i] > 0.3]
                
                if relevant_sentences:
                    # Sort them by their original order in the text to maintain some flow
                    relevant_sentences.sort(key=lambda x: sentences.index(x))
                    answer = "\n\n".join(relevant_sentences)
                else:
                    # Fallback to the first chunk if no sentence is highly relevant
                    answer = hits[0].get("content", "")[:500] + "..."
            else:
                answer = hits[0].get("content", "")[:500] + "..."

            citations = [
                {"filename": hit.get("title", "unknown"), "snippet": hit.get("content", "")[:200]}
                for hit in hits
            ]
            return {"answer": answer, "citations": citations}
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=str(e))

# -------------------------------------------------------------------
# Serve static documents and document content with highlighting
# -------------------------------------------------------------------
app.mount("/documents", StaticFiles(directory="documents"), name="documents")

@app.get("/document/{filename}")
async def get_document(filename: str, highlight: str = Query(None)):
    """Return document content with optional highlight snippet."""
    filepath = os.path.join("documents", filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")

    if filename.lower().endswith('.txt'):
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        return {"filename": filename, "content": content, "highlight": highlight, "type": "txt"}
    elif filename.lower().endswith('.pdf'):
        try:
            import pdfplumber
            with pdfplumber.open(filepath) as pdf:
                text = "".join(page.extract_text() or "" for page in pdf.pages)
        except Exception as e:
            print(f"Error retrieving document {filename}: {e}")
            raise HTTPException(status_code=500, detail=f"PDF parsing error: {e}")
        return {"filename": filename, "content": text, "highlight": highlight, "type": "pdf"}
    else:
        return {"filename": filename, "highlight": highlight, "type": "unknown"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
