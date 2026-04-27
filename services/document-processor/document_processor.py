import os
import tempfile
from typing import List
import pdfplumber
import docx
from PyPDF2 import PdfReader

def extract_text_from_file(file_content: bytes, filename: str) -> List[str]:
    """
    Extract text chunks from various document formats
    Returns list of text chunks from document (one chunk per page)
    """
    chunks = []

    if filename.lower().endswith('.pdf'):
        with pdfplumber.open(io.BytesIO(file_content)) as pdf:
            for page in pdf.pages:
                if page.text.strip():
                    chunks.append(page.text[:1000])  # Chunk size limit
    elif filename.lower().endswith('.docx'):
        with docx.Document(io.BytesIO(file_content)) as doc:
            full_text = '\n'.join([p.text for p in doc.paragraphs])
            chunks = [full_text[i:i+1000] for i in range(0, len(full_text), 1000)]
    else:  # Plain text fallback
        text = file_content.decode('utf-8', errors='ignore')
        chunks = [text[i:i+1000] for i in range(0, len(text), 1000)]

    return chunks

