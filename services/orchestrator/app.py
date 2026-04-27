import os
import httpx
from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.responses import JSONResponse

app = FastAPI()

DOC_PROCESSOR_URL = os.getenv("DOC_PROCESSOR_URL", "http://document-processor:8001")
VECTOR_DB_URL = os.getenv("VECTOR_DB_URL", "http://vector-db:8080")

# -------------------------------------------------------------------
# Document ingestion – forward file to the document‑processor service
# -------------------------------------------------------------------
@app.post("/upload")
async def upload_document(file: UploadFile):
    async with httpx.AsyncClient() as client:
        try:
            # Stream file to document‑processor
            files = {"file": (file.filename, await file.read(), file.content_type)}
            resp = await client.post(f"{DOC_PROCESSOR_URL}/ingest", files=files)
            resp.raise_for_status()
            result = resp.json()
            # Assume document‑processor returns text chunks – we now add them to Weaviate
            # For simplicity, we just forward the raw chunks; a real app would embed them here.
            return JSONResponse(content={"status": "uploaded", "detail": result})
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=str(e))

# -------------------------------------------------------------------
# Query – embed the user query and search the vector store (Weaviate)
# -------------------------------------------------------------------
@app.post("/query")
async def query_documents(query: dict):
    user_query = query.get("query")
    if not user_query:
        raise HTTPException(status_code=400, detail="Query string missing")
    async with httpx.AsyncClient() as client:
        try:
            # Forward query to the vector‑db (Weaviate) – we let Weaviate handle embedding via its "none" vectorizer
            resp = await client.get(
                f"{VECTOR_DB_URL}/v1/graphql",
                params={
                    "query": f"{{ Get {"Document"}(nearText:{{concepts:[\"{user_query}\"]}} limit:5) {{ title content _additional{{ distance }} }} }}"
                },
            )
            resp.raise_for_status()
            data = resp.json()
            # Simplify response for the UI
            hits = data.get("data", {}).get("Get", {}).get("Document", [])
            answer = " ".join([hit.get("content", "") for hit in hits][:3])
            citations = [
                {"filename": hit.get("title", "unknown"), "snippet": hit.get("content", "")[:200]}
                for hit in hits
            ]
            return {"answer": answer, "citations": citations}
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
