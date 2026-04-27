# Setup Guide (On‑Premises)

## Prerequisites
- Docker & Docker Compose installed on the server
- (Optional) NVIDIA GPU for faster embedding generation
- At least 4 GB RAM available for Weaviate and embedding models

## Step‑by‑Step Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd doc-rag
```

### 2. Prepare Document Storage
```bash
mkdir -p documents weaviate-data
chmod 777 weaviate-data  # Ensure Weaviate can write to this directory
```

### 3. Build and Start All Services
```bash
docker-compose up --build -d
```
This will start four containers:
- **document‑processor** on port 8001
- **weaviate** (vector‑db) on port 8080
- **orchestrator** on port 8000
- **chat‑ui** on port 3000

### 4. Verify Services Are Running
```bash
docker-compose ps
```
All services should show `Up` status.

### 5. Access the Application
Open a browser and navigate to:
```
http://localhost:3000
```

### 6. Upload Documents
- Use the chat UI's upload feature, or
- Place documents in the `documents/` folder and restart the document‑processor service.

### 7. Test a Query
Type a question in the chat interface, e.g., *"What are the penalties for late filing?"*  
The system will search the uploaded documents semantically and return relevant excerpts.

## Stopping and Restarting
```bash
# Stop all services
docker-compose down

# Restart
docker-compose up -d
```

## Data Persistence
- **Weaviate data**: stored in `./weaviate-data` (survives container restarts)
- **Uploaded documents**: stored in `./documents` (mounted volume)
- **Vector embeddings**: persisted inside Weaviate's data directory

## Troubleshooting
- **Weaviate fails to start**: Check `./weaviate-data` permissions.
- **Out of memory**: Reduce the embedding model size or add swap space.
- **Port conflicts**: Modify port mappings in `docker-compose.yml`.
