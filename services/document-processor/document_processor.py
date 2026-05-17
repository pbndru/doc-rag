import os
import io
import tempfile
from typing import List
import pdfplumber
import docx
from PyPDF2 import PdfReader

def extract_text_from_file(file_content: bytes, filename: str) -> List[str]:
    """
    Extract text chunks from various document formats
    Returns list of text chunks from document
    """
    text = ""

    if filename.lower().endswith('.pdf'):
        with pdfplumber.open(io.BytesIO(file_content)) as pdf:
            for page in pdf.pages:
                extracted_text = page.extract_text()
                if extracted_text:
                    text += extracted_text + "\n"
    elif filename.lower().endswith('.docx'):
        with docx.Document(io.BytesIO(file_content)) as doc:
            text = '\n'.join([p.text for p in doc.paragraphs])
    else:  # Plain text fallback
        text = file_content.decode('utf-8', errors='ignore')

    # Improved chunking: split by paragraphs then group into ~1000 char chunks
    paragraphs = text.split('\n')
    chunks = []
    current_chunk = ""
    
    for para in paragraphs:
        para = para.strip()
        if not para: continue
        
        if len(current_chunk) + len(para) < 1000:
            current_chunk += para + "\n"
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            # If a single paragraph is too long, split it by sentences or characters
            if len(para) > 1000:
                for i in range(0, len(para), 1000):
                    chunks.append(para[i:i+1000])
                current_chunk = ""
            else:
                current_chunk = para + "\n"
    
    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks

