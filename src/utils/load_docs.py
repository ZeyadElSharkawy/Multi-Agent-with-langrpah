# File: src/utils/load_docs.py
# Purpose: Convert files in the Database/ folder (PDF, DOCX, TXT/MD) into plain text files
# and write per-document metadata. Output lives in processed_docs/<Department>/
#
# Usage:
#   pip install -r requirements.txt
#   python src/utils/load_docs.py
#
# Output:
#   processed_docs/
#     <Department>/
#       my_file.txt
#       my_file.json   # metadata for the extracted text
#   processed_docs/metadata.csv  # master manifest
#
# NOTE: If PDFs are scanned images (no selectable text), you will need OCR (optional helper provided below).

import json
import uuid
import re
import csv
import datetime
from pathlib import Path
from typing import Dict, Optional

# third-party libs
try:
    import fitz  # PyMuPDF
except Exception as e:
    raise ImportError("PyMuPDF (fitz) is required. Install via: pip install PyMuPDF") from e

try:
    from docx import Document as DocxDocument
except Exception:
    DocxDocument = None  # docx optional

try:
    from tqdm import tqdm
except Exception:
    tqdm = lambda x, **k: x  # fallback if tqdm not installed


# Resolve project root relative to this file:
# src/utils/load_docs.py  -> parents[0]=utils, [1]=src, [2]=project_root (if your layout differs adjust)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "Database"
PROCESSED_DIR = PROJECT_ROOT / "processed_docs"
METADATA_CSV = PROCESSED_DIR / "metadata.csv"


def extract_text_from_pdf(path: Path) -> str:
    """Extract text from PDF using PyMuPDF (fitz). Returns concatenated page text."""
    all_text = []
    with fitz.open(path) as doc:
        for page in doc:
            text = page.get_text("text") or ""
            all_text.append(text)
    return "\n".join(all_text)


def extract_text_from_docx(path: Path) -> str:
    """Extract text from DOCX using python-docx (if installed)."""
    if DocxDocument is None:
        raise ImportError("python-docx not installed. Install with: pip install python-docx")
    doc = DocxDocument(path)
    paragraphs = [p.text for p in doc.paragraphs if p.text and p.text.strip()]
    return "\n".join(paragraphs)


def normalize_text(text: str) -> str:
    """Clean up whitespace, unify newlines, remove repeated blank lines."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # collapse more than 2 newlines into 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    # collapse multiple spaces
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def save_processed_text_and_metadata(text: str, original_path: Path, department: str) -> Optional[Dict]:
    """Save text and metadata into processed_docs/<department>/ and return metadata dict."""
    if not text:
        return None

    # create department folder
    out_dir = PROCESSED_DIR / department
    out_dir.mkdir(parents=True, exist_ok=True)

    stem = original_path.stem
    txt_path = out_dir / f"{stem}.txt"
    meta_path = out_dir / f"{stem}.json"

    # write text
    txt_path.write_text(text, encoding="utf-8")

    # helper for safe relative paths
    def rel(p: Path) -> str:
        try:
            return str(p.relative_to(PROJECT_ROOT)).replace("\\", "/")
        except ValueError:
            return str(p)  # fallback if path outside project root

    # metadata
    metadata = {
        "doc_id": str(uuid.uuid4()),
        "title": stem,
        "department": department,
        "original_path": rel(original_path),
        "processed_text_path": rel(txt_path),
        "processed_meta_path": rel(meta_path),
        "processed_at": datetime.datetime.utcnow().isoformat() + "Z",
        "original_size_bytes": original_path.stat().st_size,
        "original_modified": datetime.datetime.fromtimestamp(original_path.stat().st_mtime).isoformat()
    }

    meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata



def process_file(path: Path, department: str) -> Optional[Dict]:
    """Detect type and extract text. Returns metadata if successful."""
    ext = path.suffix.lower()
    try:
        if ext == ".pdf":
            text = extract_text_from_pdf(path)
        elif ext in (".docx", ".doc"):
            text = extract_text_from_docx(path)
        elif ext in (".txt", ".md"):
            text = path.read_text(encoding="utf-8", errors="ignore")
        else:
            # unsupported file type - skip
            print(f"[skip] unsupported file type: {path}")
            return None
    except Exception as e:
        print(f"[error] failed to extract {path}: {e}")
        return None

    text = normalize_text(text)
    if not text:
        print(f"[warning] no text extracted from {path} (may be scanned image PDF)")
        return None

    return save_processed_text_and_metadata(text, path, department)


def discover_and_process(root: Path = RAW_DIR):
    """Walk immediate subfolders (departments) and process files."""
    if not root.exists():
        raise FileNotFoundError(f"Database folder not found at expected location: {root}")

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    all_meta = []

    # iterate departments (assumes subfolders are departments)
    dept_dirs = sorted([p for p in root.iterdir() if p.is_dir()])
    for dept in dept_dirs:
        department_name = dept.name
        files = list(dept.rglob("*.*"))
        if not files:
            print(f"[info] no files in {dept}")
            continue

        for f in tqdm(files, desc=f"Processing {department_name}", unit="file"):
            meta = process_file(f, department_name)
            if meta:
                all_meta.append(meta)

    # write master metadata CSV
    if all_meta:
        with open(METADATA_CSV, "w", newline="", encoding="utf-8") as csvf:
            writer = csv.DictWriter(csvf, fieldnames=[
                "doc_id", "title", "department", "original_path", "processed_text_path",
                "processed_meta_path", "processed_at", "original_size_bytes", "original_modified"
            ])
            writer.writeheader()
            for m in all_meta:
                writer.writerow({k: m.get(k, "") for k in writer.fieldnames})
        print(f"\nProcessed {len(all_meta)} documents. Master manifest: {METADATA_CSV}")
    else:
        print("No documents processed. Check if files are readable and not scanned images.")


if __name__ == "__main__":
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Raw Database dir: {RAW_DIR}")
    print(f"Processed output dir: {PROCESSED_DIR}\n")
    discover_and_process()
