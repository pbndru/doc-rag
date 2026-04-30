import os
import httpx
from fastapi import FastAPI, UploadFile, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

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
        schema = {
            "classes": [
                {
                    "class": "Document",
                    "properties": [
                        {"name": "title", "dataType": ["string"]},
                        {"name": "content", "dataType": ["text"]},
                        {"name": "chunkIndex", "dataType": ["int"]}
                    ]
                }
            ]
        }
        try:
            resp = await client.post(f"{VECTOR_DB_URL}/v1/schema", json=schema)
            resp.raise_for_status()
        except Exception:
            # Schema may already exist; ignore
            pass

# -------------------------------------------------------------------
# On startup, ingest all files present in the ``documents`` folder.
# This replaces the manual ``/upload`` endpoint – files added to ``/documents``
# on the host are automatically processed when the service starts.
# -------------------------------------------------------------------
@app.on_event("startup")
async def ingest_documents_on_startup():
    import os
    async with httpx.AsyncClient() as client:
        docs_path = os.path.abspath("documents")
        if not os.path.isdir(docs_path):
            return
        for filename in os.listdir(docs_path):
            file_path = os.path.join(docs_path, filename)
            if os.path.isfile(file_path):
                try:
                    # Open file in binary mode for upload
                    with open(file_path, "rb") as f:
                        files = {"file": (filename, f, "application/octet-stream")}
                        resp = await client.post(f"{DOC_PROCESSOR_URL}/ingest", files=files)
                        resp.raise_for_status()
                except Exception as e:
                    # Log the error; do not stop the startup process
                    print(f"Failed to ingest {filename}: {e}")

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
            graphql_query = f'''
            {{
              Get {{
                Document(nearText:{{concepts:["{user_query}"]}} limit:5) {{
                  title
                  content
                  chunkIndex
                  _additional {{
                    distance
                  }}
                }}
              }}
            '''
            resp = await client.post(
                f"{VECTOR_DB_URL}/v1/graphql",
                json={"query": graphql_query}
            )
            resp.raise_for_status()
            data = resp.json()
            hits = data.get("data", {}).get("Get", {}).get("Document", [])
            answer = " ".join([hit.get("content", "") for hit in hits][:3])
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
            from PyPDF2 import PdfReader
            reader = PdfReader(filepath)
            text = "".join(page.extract_text() or "" for page in reader.pages)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"PDF parsing error: {e}")
        return {"filename": filename, "content": text, "highlight": highlight, "type": "pdf"}
    else:
        return {"filename": filename, "highlight": highlight, "type": "unknown"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
