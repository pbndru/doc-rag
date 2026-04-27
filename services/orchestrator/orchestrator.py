"""
Helper functions for the orchestrator service.
Currently a stub – in a real implementation this would coordinate
between the document‑processor, vector‑db, and the UI.
"""

def format_response(weaviate_hits: list) -> dict:
    """Convert Weaviate search results into a UI‑friendly structure."""
    answer_parts = []
    citations = []
    for hit in weaviate_hits:
        answer_parts.append(hit.get("content", ""))
        citations.append({
            "filename": hit.get("title", "unknown"),
            "snippet": hit.get("content", "")[:200]
        })
    return {
        "answer": " ".join(answer_parts[:3]),
        "citations": citations
    }
