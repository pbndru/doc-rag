import os
import json
import httpx
import numpy as np
from fastapi import FastAPI, UploadFile, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sentence_transformers import SentenceTransformer, util
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from langchain.memory import ConversationBufferMemory

app = FastAPI()

# Load sentence transformer model (accurate version)
model = SentenceTransformer('all-mpnet-base-v2')

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "llama3")

# Initialize LLM (Ollama via OpenAI-compatible API)
llm = ChatOpenAI(
    base_url=f"{OLLAMA_URL}/v1",
    api_key="ollama", # Placeholder for Ollama
    model=LLM_MODEL,
    temperature=0
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DOC_PROCESSOR_URL = os.getenv("DOC_PROCESSOR_URL", "http://document-processor:8001")
VECTOR_DB_URL = os.getenv("VECTOR_DB_URL", "http://vector-db:8080")

processed_files = set()

async def check_if_file_exists_in_db(filename: str, client: httpx.AsyncClient):
    """Check if a file with the given title already exists in Weaviate."""
    graphql_query = {
        "query": f'{{ Get {{ Document(where: {{ path: ["title"], operator: Equal, valueText: "{filename}" }}) {{ title }} }} }}'
    }
    try:
        resp = await client.post(f"{VECTOR_DB_URL}/v1/graphql", json=graphql_query)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("data", {}).get("Get", {}).get("Document", [])
        return len(results) > 0
    except Exception as e:
        print(f"Error checking DB for {filename}: {e}", flush=True)
        return False

async def ingest_file(filename: str, client: httpx.AsyncClient):
    """Send a file to the document-processor for ingestion."""
    filepath = os.path.join("/app/documents", filename)
    if not os.path.exists(filepath):
        print(f"File {filepath} not found for ingestion.", flush=True)
        return

    try:
        with open(filepath, "rb") as f:
            files = {"file": (filename, f)}
            resp = await client.post(f"{DOC_PROCESSOR_URL}/ingest", files=files, timeout=60.0)
            resp.raise_for_status()
            print(f"Successfully ingested {filename}", flush=True)
            processed_files.add(filename)
    except Exception as e:
        print(f"Error ingesting {filename}: {e}", flush=True)

import asyncio
import sys

# -------------------------------------------------------------------
# Ensure Weaviate schema exists and start watcher
# -------------------------------------------------------------------
@app.on_event("startup")
async def startup_event():
    print("Orchestrator starting up...", flush=True)
    async with httpx.AsyncClient() as client:
        # Define class Document if not present
        class_obj = {
            "class": "Document",
            "vectorizer": "none",
            "properties": [
                {"name": "title", "dataType": ["text"]},
                {"name": "content", "dataType": ["text"]},
                {"name": "chunkIndex", "dataType": ["int"]}
            ]
        }
        try:
            resp = await client.post(f"{VECTOR_DB_URL}/v1/schema", json=class_obj)
            print(f"Schema creation response: {resp.status_code}", flush=True)
        except Exception as e:
            print(f"Schema creation error: {e}", flush=True)

    # Start watcher
    asyncio.create_task(watcher())
    print("Watcher task created", flush=True)

async def watcher():
    print("Watcher started", flush=True)
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Initial population of processed_files from DB
        docs_path = "/app/documents"
        if os.path.isdir(docs_path):
            for filename in os.listdir(docs_path):
                if filename.lower().endswith(('.pdf', '.docx', '.txt')):
                    if await check_if_file_exists_in_db(filename, client):
                        print(f"File {filename} already in DB, skipping.", flush=True)
                        processed_files.add(filename)

    while True:
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                docs_path = "/app/documents" # Explicit path
                if os.path.isdir(docs_path):
                    files = os.listdir(docs_path)
                    for filename in files:
                        if filename.startswith('.'): continue
                        
                        if filename in processed_files:
                            continue
                            
                        if await check_if_file_exists_in_db(filename, client):
                            print(f"File {filename} already in DB, skipping.", flush=True)
                            processed_files.add(filename)
                            continue
                            
                        print(f"Found new file: {filename}. Ingesting...", flush=True)
                        await ingest_file(filename, client)
                else:
                    print(f"Documents directory not found at {docs_path}", flush=True)
        except Exception as e:
            print(f"Watcher error: {e}", flush=True)
        
        await asyncio.sleep(10)

# -------------------------------------------------------------------
# Tools for the Agent
# -------------------------------------------------------------------

@tool
async def search_documents(query: str):
    """Search for relevant document snippets based on a natural language query. 
    Use this for initial discovery and finding specific details.
    """
    async with httpx.AsyncClient() as client:
        # Compute query vector
        embedding = model.encode([query])[0].tolist()
        
        graphql_query = {
            "query": """
            {
              Get {
                Document (
                  hybrid: {
                    query: %s,
                    vector: %s,
                    alpha: 0.5
                  }
                  limit: 5
                ) {
                  title
                  content
                  _additional { score }
                }
              }
            }
            """ % (json.dumps(query), json.dumps(embedding))
        }
        
        resp = await client.post(f"{VECTOR_DB_URL}/v1/graphql", json=graphql_query)
        resp.raise_for_status()
        data = resp.json()
        hits = data.get("data", {}).get("Get", {}).get("Document", [])
        
        if not hits:
            return "No relevant information found."
        
        results = []
        for hit in hits:
            results.append(f"Source: {hit['title']}\nContent: {hit['content']}")
        
        return "\n---\n".join(results)

@tool
async def read_document_content(filename: str):
    """Retrieve the full text content of a specific document by its filename.
    Use this when a search result mentions another document or when you need more context from a known file.
    """
    filepath = os.path.join("documents", filename)
    if not os.path.exists(filepath):
        return f"Error: Document '{filename}' not found."

    if filename.lower().endswith('.txt'):
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    elif filename.lower().endswith('.pdf'):
        try:
            import pdfplumber
            with pdfplumber.open(filepath) as pdf:
                return "".join(page.extract_text() or "" for page in pdf.pages)
        except Exception as e:
            return f"Error reading PDF {filename}: {e}"
    elif filename.lower().endswith('.docx'):
        try:
            import docx
            doc = docx.Document(filepath)
            return "\n".join([para.text for para in doc.paragraphs])
        except Exception as e:
            return f"Error reading DOCX {filename}: {e}"
    else:
        return f"Unsupported file type for {filename}"

tools = [search_documents, read_document_content]

# -------------------------------------------------------------------
# Agent Configuration
# -------------------------------------------------------------------

prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a focused RAG assistant. Answer queries using the search tools.
    
    RULES:
    1. **Search First:** Always use `search_documents` for your initial action.
    2. **Be Direct:** If the answer is in the search results, provide it immediately.
    3. **Relational Leads:** Only use `read_document_content` if a search result explicitly mentions another file or policy needed to answer the query.
    4. **No Citations Header:** Don't write a "References" section; just mention source filenames in your text.
    5. **Concise:** Keep answers brief and factual."""),
    MessagesPlaceholder(variable_name="chat_history"),
    ("user", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

agent = create_openai_functions_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True, return_intermediate_steps=True)

# -------------------------------------------------------------------
# Query – search the vector store (Weaviate)
# -------------------------------------------------------------------
@app.post("/query")
async def query_documents(query: dict):
    user_query = query.get("query")
    if not user_query:
        raise HTTPException(status_code=400, detail="Query string missing")
    
    try:
        # Run the agent
        result = await agent_executor.ainvoke({
            "input": user_query,
            "chat_history": []
        })
        
        answer = result.get("output", "I'm sorry, I couldn't process that request.")
        intermediate_steps = result.get("intermediate_steps", [])
        
        citations = []
        seen_citations = set()

        for action, observation in intermediate_steps:
            if action.tool == "search_documents":
                # Parse the observation which is a string of results separated by ---
                parts = observation.split("\n---\n")
                for part in parts:
                    if "Source: " in part and "Content: " in part:
                        lines = part.split("\n")
                        filename = lines[0].replace("Source: ", "").strip()
                        content = "\n".join(lines[1:]).replace("Content: ", "").strip()
                        
                        # Only add if relevant to the final answer (heuristic: filename appears in answer or it was a search result)
                        # To be safe and helpful, we add it if it hasn't been added yet.
                        citation_key = (filename, content[:100])
                        if citation_key not in seen_citations:
                            citations.append({
                                "filename": filename, 
                                "snippet": content[:300] # Use a reasonable snippet for highlighting
                            })
                            seen_citations.add(citation_key)
            
            elif action.tool == "read_document_content":
                filename = action.tool_input
                if isinstance(filename, dict):
                    filename = filename.get("filename", str(filename))
                
                if filename not in [c["filename"] for c in citations]:
                    citations.append({
                        "filename": filename,
                        "snippet": observation[:300] # Use the start of the document as a fallback snippet
                    })

        return {"answer": answer, "citations": citations}
        
    except Exception as e:
        print(f"Agent execution error: {e}", flush=True)
        raise HTTPException(status_code=500, detail=str(e))

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
