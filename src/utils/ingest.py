"""
File: src/ingest.py
Purpose:
    Load all processed text documents from processed_docs/,
    generate embeddings, and store them in a vector database (Chroma).

Usage:
    pip install langchain chromadb sentence-transformers tqdm
    python src/ingest.py

Output:
    vector_store/
        chroma.sqlite
        index/
"""

import os
import json
import csv
from pathlib import Path
from tqdm import tqdm

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document


# -------------------------------------------------
# Path setup (relative, repo-safe)
# -------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "processed_docs"
VECTOR_DIR = PROJECT_ROOT / "vector_store"
METADATA_CSV = PROCESSED_DIR / "metadata.csv"


# -------------------------------------------------
# Embedding model
# -------------------------------------------------
def get_embedding_model():
    """
    Return a HuggingFace embedding model.
    You can replace with OpenAIEmbeddings if you have an API key.
    """
    return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")


# -------------------------------------------------
# Load processed docs + metadata
# -------------------------------------------------
def load_processed_documents():
    """
    Loads all processed text and metadata from processed_docs/
    Returns a list of LangChain Documents.
    """
    documents = []

    if not METADATA_CSV.exists():
        raise FileNotFoundError(f"Missing metadata.csv in {PROCESSED_DIR}")

    with open(METADATA_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            text_path = PROJECT_ROOT / row["processed_text_path"]
            meta_path = PROJECT_ROOT / row["processed_meta_path"]

            if not text_path.exists():
                print(f"[skip] Missing text file: {text_path}")
                continue

            try:
                text = text_path.read_text(encoding="utf-8")
                metadata = json.loads(meta_path.read_text(encoding="utf-8"))
                metadata.pop("processed_text_path", None)
                metadata.pop("processed_meta_path", None)

                doc = Document(page_content=text, metadata=metadata)
                documents.append(doc)
            except Exception as e:
                print(f"[error] Failed loading {text_path}: {e}")
                continue

    print(f"Loaded {len(documents)} processed documents.")
    return documents


# -------------------------------------------------
# Split large documents into chunks
# -------------------------------------------------
def chunk_documents(documents, chunk_size=1000, overlap=200):
    """
    Split documents into smaller chunks for embedding.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        separators=["\n\n", "\n", " ", ""],
    )

    split_docs = splitter.split_documents(documents)
    print(f"Split into {len(split_docs)} chunks.")
    return split_docs


# -------------------------------------------------
# Build and persist vector store
# -------------------------------------------------
def build_vector_store(documents):
    """
    Create embeddings and persist them in a local Chroma DB.
    """
    VECTOR_DIR.mkdir(parents=True, exist_ok=True)

    embedding_model = get_embedding_model()
    print("Generating embeddings and creating vector store...")

    vectorstore = Chroma.from_documents(
        documents=documents,
        embedding=embedding_model,
        persist_directory=str(VECTOR_DIR),
    )

    vectorstore.persist()
    print(f"Vector store successfully saved to {VECTOR_DIR}")


# -------------------------------------------------
# Main
# -------------------------------------------------
def main():
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Processed dir: {PROCESSED_DIR}")
    print(f"Vector store dir: {VECTOR_DIR}\n")

    docs = load_processed_documents()
    if not docs:
        print("No documents found. Run load_docs.py first.")
        return

    chunks = chunk_documents(docs)
    build_vector_store(chunks)


if __name__ == "__main__":
    main()
