from fastapi import FastAPI, UploadFile, HTTPException
import uvicorn
import tempfile
import os
from fastapi import FastAPI, UploadFile, HTTPException
import uvicorn
import tempfile
import os
from sentence_transformers import SentenceTransformer
import faiss
from document_processor import extract_text_from_file

app = FastAPI()

# Load embedding model
model = SentenceTransformer('all-MiniLM-L6-v2')
index = faiss.IndexFlatL2(384)  # 384 is embedding dimension

@app.post("/ingest")
async def ingest_document(file: UploadFile):
    try:
        text = await file.read()
        # Split into chunks (example: by pages)
        chunks = extract_text_from_file(text, file.filename)

        # Generate embeddings for each chunk
en = model.encode(chunks)
        index.add(embeddings=en)

        return {\"status\": \"processed\", \"chunks\": len(chunks)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == \"__main__\":
    uvicorn.run(\"app:app\", host=\"0.0.0.0\", port=8001)


app = FastAPI()

@app.post(/ingest)
async def ingest_document(file: UploadFile):
    try:
        text = await file.read()
        extracted = extract_text_from_file(text, file.filename)
        # Store text or process embedding here
        return {"status": "processed", "pages": len(extracted)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8001)
