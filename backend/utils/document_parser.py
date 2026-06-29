# utils/document_parser.py
import os
import re
from typing import Dict, List, Any
from pathlib import Path

try:
    from docx import Document
except ImportError:
    Document = None

try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None


def extract_text(file_path: str, filename: str) -> str:
    """Extract text from various document formats"""
    ext = Path(filename).suffix.lower()
    
    if ext == ".txt":
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    
    elif ext in [".docx", ".doc"]:
        if Document is None:
            raise ImportError("python-docx library is required for .docx files. Install with: pip install python-docx")
        doc = Document(file_path)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        return text
    
    elif ext == ".pdf":
        if PdfReader is None:
            raise ImportError("PyPDF2 library is required for .pdf files. Install with: pip install PyPDF2")
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    
    else:
        raise ValueError(f"Unsupported file type: {ext}")

def parse_document_structure(text: str) -> Dict[str, Any]:
    """Parse document structure to extract ONLY requirements"""
    
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    
    if not lines:
        raise ValueError("Document is empty")
    
    # Extract requirements
    requirements: List[Dict[str, Any]] = []
    req_start_index = -1
    
    for i, line in enumerate(lines):
        if re.match(r"^(system\s+requirements?|requirements?)\b", line, re.IGNORECASE):
            req_start_index = i
            break
    
    if req_start_index != -1:
        req_lines = lines[req_start_index + 1:]
        id_counter = 1
        
        for line in req_lines:
            # Numbered requirement
            num_match = re.match(r"^\s*(\d+)[\.\)\-]\s*(.+)", line)
            if num_match:
                req_id = int(num_match.group(1))
                req_text = num_match.group(2).strip()
                requirements.append({"id": req_id, "text": req_text})
                id_counter = max(id_counter, req_id + 1)
                continue
            
            # Bulleted requirement
            bullet_match = re.match(r"^(\*|\-|\•)\s+(.+)", line)
            if bullet_match:
                requirements.append({"id": id_counter, "text": bullet_match.group(2).strip()})
                id_counter += 1
                continue
            
            # Plain line
            if re.match(r"^[A-Za-z0-9]", line):
                requirements.append({"id": id_counter, "text": line.strip()})
                id_counter += 1
    
    if len(requirements) < 1:
        raise ValueError("No requirements found in the document")
    
    requirements = [
        {
            "id": r["id"], 
            "req_id": f"REQ-{r['id']}",
            "text": r["text"], 
            "origin": "extracted",
            "parent_req_id": None,
            "parent_text": None
        } 
        for r in requirements
    ]
    return {
        "title": None,      # always from UI
        "summary": None,    # always from UI
        "requirements": requirements,
    }