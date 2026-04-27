import faiss
import numpy as np
from fastapi import FastAPI, HTTPException
import os
import pickle

app = FastAPI()
index = None

@app.on_event("startup")
async def startup():
    global index
    index_path = "/app/faiss_index.index"
    if os.path.exists(index_path):
        with open(index_path, "rb") as f:
            index = pickle.load(f)
        print(f"[VECTOR_DB] Loaded index with {len(index)} vectors")
    else:
        # Simple index for 384-dim embeddings
        index = faiss.IndexFlatL2(384)
        print("[VECTOR_DB] Created new empty index")

@app.post("/add")
async def add_vectors(vectors: list):
    global index
    if index is None:
        raise HTTPException(status_code=500, detail="Index not initialized")
    vector_array = np.array(vectors, dtype=np.float32).reshape(len(vectors), -1)
    index.add(vector_array)
    # Persist index to disk
    faiss.write_index(index, path="/app/faiss_index.index")
    return {"status": "vectors added", "count": len(vectors)}

@app.get("/search")
async def search_embeddings(query: list, k: int = 5):
    global index
    if index is None or index.ntotal == 0:
        raise HTTPException(status_code=500, detail="No vectors in index")
    q_arr = np.array(query, dtype=np.float32).reshape(1, -1)
    D, I = index.search(q_arr, k)
    results = []
    for idx, score in zip(I[0], D[0]):
        results.append({"id": int(idx), "score": float(score)})
    return {"results": results}