import os
import httpx
from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from sentence_transformers import SentenceTransformer
from document_processor import extract_text_from_file

app = FastAPI()
VECTOR_DB_URL = os.getenv("VECTOR_DB_URL", "http://vector-db:8080")
model = SentenceTransformer('all-mpnet-base-v2')

@app.post("/ingest")
async def ingest_document(file: UploadFile):
    try:
        content = await file.read()
        chunks = extract_text_from_file(content, file.filename)
        embeddings = model.encode(chunks)
        # Add each chunk to Weaviate
        async with httpx.AsyncClient() as client:
            for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
                payload = {
                    "class": "Document",
                    "properties": {
                        "title": file.filename,
                        "content": chunk,
                        "chunkIndex": i
                    },
                    "vector": emb.tolist()
                }
                resp = await client.post(
                    f"{VECTOR_DB_URL}/v1/objects",
                    json=payload
                )
                resp.raise_for_status()
        return JSONResponse(content={"status": "processed", "chunks": len(chunks)})
    except Exception as e:
        print(f"Error during ingestion: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
