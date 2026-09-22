"""
embed_typology_docs.py — Extract, chunk, and embed typology documents into ChromaDB.

Processes:
  - 7 PDF source documents from sources/
  - TYPOLOGY_MAPPING.md from docs/
Chunks with LangChain's RecursiveCharacterTextSplitter, embeds with
sentence-transformers/all-MiniLM-L6-v2, persists to ./chroma_db/.
"""

import re
import fitz  # PyMuPDF
import chromadb
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter

# ── Paths ────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCES_DIR = PROJECT_ROOT / "sources"
DOCS_DIR = PROJECT_ROOT / "docs"
CHROMA_DIR = PROJECT_ROOT / "chroma_db"
COLLECTION_NAME = "typology_docs"

# ── Pattern mapping from filenames ───────────────────────────────────────────
# Maps source filenames to the IBM AML pattern type(s) they ground.
FILENAME_TO_PATTERN = {
    "FFIEC Appendix L.pdf": "ALL",  # narrative structure, applies to all
    "FIN-2014-A005(for gather-scatter).pdf": "GATHER-SCATTER",
    "GARG-AML paper(for scatter-gather).pdf": "SCATTER-GATHER",
    "July2014_Case7(for fan-in).pdf": "FAN-IN",
    "Money laundering typologies 2000-2001(for cycle).pdf": "CYCLE",
    "Professional-Money-Laundering(for stacks).pdf": "STACK",
    "Trade_Based_ML_APGReport(for bipartite).pdf": "BIPARTITE",
    "TYPOLOGY_MAPPING.md": "ALL",  # bridge doc, applies to all
}


# ── 1. PDF Text Extraction ──────────────────────────────────────────────────
def extract_pdf_text(pdf_path: Path) -> list[dict]:
    """
    Extract text from a PDF file, returning a list of dicts with
    page_number and text content.
    """
    pages = []
    doc = fitz.open(pdf_path)
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")
        if text.strip():
            pages.append({
                "page_number": page_num + 1,
                "text": text.strip(),
                "source_file": pdf_path.name,
            })
    doc.close()
    return pages


def extract_markdown_text(md_path: Path) -> list[dict]:
    """Load a Markdown file as a single-page document."""
    text = md_path.read_text(encoding="utf-8")
    return [{
        "page_number": 1,
        "text": text,
        "source_file": md_path.name,
    }]


# ── 2. Chunking ─────────────────────────────────────────────────────────────
def chunk_documents(
    pages: list[dict],
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> list[dict]:
    """
    Split page texts into overlapping chunks, preserving metadata.
    Returns list of dicts with: text, source_file, page_number, pattern_type, chunk_index.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,
    )

    all_chunks = []
    chunk_idx = 0

    for page in pages:
        source_file = page["source_file"]
        pattern_type = FILENAME_TO_PATTERN.get(source_file, "UNKNOWN")

        texts = splitter.split_text(page["text"])
        for text in texts:
            all_chunks.append({
                "text": text,
                "source_file": source_file,
                "page_number": page["page_number"],
                "pattern_type": pattern_type,
                "chunk_index": chunk_idx,
            })
            chunk_idx += 1

    return all_chunks


# ── 3. ChromaDB Embedding & Storage ──────────────────────────────────────────

# Default model. Override via CLI arg or environment variable.
DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"


def get_embedding_function(model_name: str = DEFAULT_EMBEDDING_MODEL):
    """Create a ChromaDB-compatible embedding function."""
    from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
    return SentenceTransformerEmbeddingFunction(model_name=model_name)


def embed_and_store(
    chunks: list[dict],
    reset: bool = True,
    model_name: str = DEFAULT_EMBEDDING_MODEL,
) -> int:
    """
    Embed chunks and persist to ChromaDB.

    Args:
        chunks: list of chunk dicts from chunk_documents()
        reset: if True, delete existing collection before inserting
        model_name: sentence-transformers model to use for embedding

    Returns:
        Number of chunks embedded.
    """
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    if reset:
        try:
            client.delete_collection(COLLECTION_NAME)
            print(f"  Deleted existing collection '{COLLECTION_NAME}'")
        except Exception:
            pass

    ef = get_embedding_function(model_name)
    print(f"  Using embedding model: {model_name}")

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
        embedding_function=ef,
    )

    # Batch insert
    BATCH_SIZE = 100
    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i : i + BATCH_SIZE]
        collection.add(
            ids=[f"chunk_{c['chunk_index']}" for c in batch],
            documents=[c["text"] for c in batch],
            metadatas=[
                {
                    "source_file": c["source_file"],
                    "page_number": c["page_number"],
                    "pattern_type": c["pattern_type"],
                }
                for c in batch
            ],
        )

    return collection.count()


# ── 4. Main pipeline ─────────────────────────────────────────────────────────
def run_pipeline() -> None:
    """Full extraction → chunking → embedding pipeline."""

    # Extract text from all PDFs
    all_pages = []
    pdf_files = sorted(SOURCES_DIR.glob("*.pdf"))
    print(f"Found {len(pdf_files)} PDF files in sources/")

    for pdf_path in pdf_files:
        pages = extract_pdf_text(pdf_path)
        print(f"  {pdf_path.name}: {len(pages)} pages extracted")
        all_pages.extend(pages)

    # Also load TYPOLOGY_MAPPING.md
    mapping_path = DOCS_DIR / "TYPOLOGY_MAPPING.md"
    if mapping_path.exists():
        md_pages = extract_markdown_text(mapping_path)
        print(f"  {mapping_path.name}: loaded as single document")
        all_pages.extend(md_pages)

    print(f"\nTotal pages/documents: {len(all_pages)}")

    # Chunk
    chunks = chunk_documents(all_pages)
    print(f"Total chunks after splitting: {len(chunks)}")

    # Show distribution by source
    from collections import Counter
    source_counts = Counter(c["source_file"] for c in chunks)
    for source, count in sorted(source_counts.items()):
        print(f"  {source}: {count} chunks")

    # Embed and store
    print("\nEmbedding and storing in ChromaDB...")
    total = embed_and_store(chunks, reset=True)
    print(f"  → {total} chunks stored in {CHROMA_DIR}")

    print("\nDone.")


if __name__ == "__main__":
    run_pipeline()
