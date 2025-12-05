#!/usr/bin/env python3
"""
RAG Knowledge Base Seeder - Fixed for ChromaDB 0.4.24
Loads PDFs into ChromaDB with proper tenant handling
"""

import os
import sys
import logging
from pathlib import Path
from typing import List
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

CHROMADB_HOST = os.environ.get("CHROMADB_HOST", "localhost")
CHROMADB_PORT = int(os.environ.get("CHROMADB_PORT", "8000"))
RAG_COLLECTION_NAME = os.environ.get("RAG_COLLECTION_NAME", "corn-stress-knowledge")
KNOWLEDGE_BASE_DIR = os.environ.get("KNOWLEDGE_BASE_DIR", "./knowledge_base/pdfs")

# ============================================================================
# FUNCTIONS
# ============================================================================


def connect_chromadb(host: str = CHROMADB_HOST, port: int = CHROMADB_PORT):
    """Connect to ChromaDB instance with retry logic"""
    import chromadb
    import time

    max_retries = 5
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            logger.info(f"Connecting to ChromaDB at {host}:{port} (attempt {attempt + 1}/{max_retries})...")

            # Create client
            client = chromadb.HttpClient(host=host, port=port)

            # Try to get heartbeat
            heartbeat = client.get_settings()
            logger.info(f"✓ Connected to ChromaDB successfully")
            return client

        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Connection failed: {e}")
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.error(f"✗ Failed to connect after {max_retries} attempts: {e}")
                sys.exit(1)


def extract_text_from_pdf(pdf_path: Path) -> List[str]:
    """Extract text from PDF file"""
    try:
        from PyPDF2 import PdfReader

        reader = PdfReader(pdf_path)
        texts = []

        for page_num, page in enumerate(reader.pages):
            text = page.extract_text()
            if text.strip():
                # Include source info in each chunk
                texts.append(f"[Source: {pdf_path.name}, Page {page_num + 1}]\n{text}")

        logger.info(f"  ✓ Extracted {len(texts)} pages from {pdf_path.name}")
        return texts
    except Exception as e:
        logger.error(f"  ✗ Failed to extract text from {pdf_path.name}: {e}")
        return []


def split_text_into_chunks(text: str, chunk_size: int = 1000, chunk_overlap: int = 100) -> List[str]:
    """Split text into overlapping chunks"""
    chunks = []
    for i in range(0, len(text), chunk_size - chunk_overlap):
        chunk = text[i : i + chunk_size]
        # Only keep substantial chunks
        if len(chunk.strip()) > 100:
            chunks.append(chunk)
    return chunks


def seed_knowledge_base(pdf_dir: str = KNOWLEDGE_BASE_DIR, chunk_size: int = 1000):
    """Load PDFs into ChromaDB collection"""

    pdf_path = Path(pdf_dir)

    # Validate directory
    if not pdf_path.exists():
        logger.error(f"✗ PDF directory not found: {pdf_dir}")
        sys.exit(1)

    # Find PDFs
    pdfs = list(pdf_path.glob("*.pdf"))
    if not pdfs:
        logger.warning(f"⚠  No PDF files found in {pdf_dir}")
        return

    logger.info(f"\n📚 Found {len(pdfs)} PDF file(s):")
    for pdf in pdfs:
        logger.info(f"  - {pdf.name}")

    # Connect to ChromaDB
    client = connect_chromadb()

    # Get or create collection
    logger.info(f"\n📖 Getting/creating collection: {RAG_COLLECTION_NAME}")
    try:
        collection = client.get_or_create_collection(name=RAG_COLLECTION_NAME, metadata={"hnsw:space": "cosine"})
        logger.info(f"✓ Collection ready: {RAG_COLLECTION_NAME}")
    except Exception as e:
        logger.error(f"✗ Failed to create collection: {e}")
        sys.exit(1)

    # Load and process PDFs
    logger.info("\n📄 Processing PDFs...")
    all_chunks = []
    ids = []
    metadatas = []

    for pdf in pdfs:
        logger.info(f"\nProcessing: {pdf.name}")

        # Extract text from PDF
        texts = extract_text_from_pdf(pdf)

        # Split into chunks
        for text in texts:
            chunks = split_text_into_chunks(text, chunk_size=chunk_size)
            for chunk in chunks:
                chunk_id = str(uuid.uuid4())
                all_chunks.append(chunk)
                ids.append(chunk_id)
                metadatas.append({"source": pdf.name, "type": "agricultural_knowledge"})

    if not all_chunks:
        logger.warning("⚠  No text chunks extracted from PDFs")
        return

    # Add to collection in batches (to avoid timeout)
    logger.info(f"\n💾 Adding {len(all_chunks)} chunks to ChromaDB (in batches)...")
    batch_size = 100

    try:
        for i in range(0, len(all_chunks), batch_size):
            batch_ids = ids[i : i + batch_size]
            batch_docs = all_chunks[i : i + batch_size]
            batch_meta = metadatas[i : i + batch_size]

            logger.info(f"  Adding batch {i // batch_size + 1}/{(len(all_chunks) + batch_size - 1) // batch_size}...")

            collection.add(ids=batch_ids, documents=batch_docs, metadatas=batch_meta)

        final_count = collection.count()
        logger.info(f"✓ Successfully added {final_count} documents to collection")

    except Exception as e:
        logger.error(f"✗ Failed to add chunks to collection: {e}")
        sys.exit(1)

    logger.info("\n✓ Knowledge base seeding complete!")
    return len(all_chunks)


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    logger.info("=" * 70)
    logger.info("RAG Knowledge Base Seeder (Fixed for ChromaDB 0.4.24)")
    logger.info("=" * 70)

    try:
        from PyPDF2 import PdfReader
    except ImportError:
        logger.error("✗ PyPDF2 not installed")
        sys.exit(1)

    try:
        import chromadb
    except ImportError:
        logger.error("✗ chromadb not installed")
        sys.exit(1)

    count = seed_knowledge_base()

    if count:
        logger.info("\n" + "=" * 70)
        logger.info("✓ RAG service is now ready to answer questions!")
        logger.info("=" * 70)
