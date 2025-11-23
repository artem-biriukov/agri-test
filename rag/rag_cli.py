#!/usr/bin/env python3
"""
RAG Knowledge Base Management CLI
Loads PDFs into ChromaDB for agricultural knowledge base
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from typing import List, Optional
import chromadb
from llama_index.core import Document, StorageContext, VectorStoreIndex
from llama_index.embeddings.vertex import VertexTextEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.readers.file import SimpleDirectoryReader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

CHROMADB_HOST = os.environ.get("CHROMADB_HOST", "localhost")
CHROMADB_PORT = int(os.environ.get("CHROMADB_PORT", "8000"))
GCP_PROJECT = os.environ.get("GCP_PROJECT", "agriguard-ac215")
GCP_LOCATION = os.environ.get("GCP_LOCATION", "us-central1")
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "text-embedding-004")
EMBEDDING_DIMENSION = int(os.environ.get("EMBEDDING_DIMENSION", "768"))


# ============================================================================
# FUNCTIONS
# ============================================================================

def connect_chromadb(host: str = CHROMADB_HOST, port: int = CHROMADB_PORT):
    """Connect to ChromaDB instance"""
    try:
        logger.info(f"Connecting to ChromaDB at {host}:{port}")
        client = chromadb.HttpClient(host=host, port=port)
        # Test connection
        collections = client.list_collections()
        logger.info(f"✓ Connected successfully. Found {len(collections)} collections")
        return client
    except Exception as e:
        logger.error(f"✗ Failed to connect to ChromaDB: {e}")
        sys.exit(1)


def load_pdfs(pdf_dir: str, collection_name: str, chunk_size: int = 1000, chunk_overlap: int = 100):
    """
    Load PDFs from directory into ChromaDB collection
    
    Args:
        pdf_dir: Directory containing PDF files
        collection_name: Name of ChromaDB collection to create/update
        chunk_size: Size of text chunks
        chunk_overlap: Overlap between chunks
    """
    
    pdf_path = Path(pdf_dir)
    
    # Validate directory
    if not pdf_path.exists():
        logger.error(f"✗ PDF directory not found: {pdf_dir}")
        sys.exit(1)
    
    if not pdf_path.is_dir():
        logger.error(f"✗ Not a directory: {pdf_dir}")
        sys.exit(1)
    
    # Find PDFs
    pdfs = list(pdf_path.glob("*.pdf"))
    if not pdfs:
        logger.warning(f"⚠ No PDF files found in {pdf_dir}")
        return
    
    logger.info(f"Found {len(pdfs)} PDF files:")
    for pdf in pdfs:
        logger.info(f"  - {pdf.name}")
    
    # Connect to ChromaDB
    client = connect_chromadb()
    
    # Get or create collection
    logger.info(f"Creating/updating collection: {collection_name}")
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"}
    )
    
    # Initialize embedding model
    logger.info(f"Initializing embedding model: {EMBEDDING_MODEL}")
    try:
        embed_model = VertexTextEmbedding(
            model_name=EMBEDDING_MODEL,
            project=GCP_PROJECT,
            location=GCP_LOCATION,
            embed_batch_size=1
        )
    except Exception as e:
        logger.error(f"✗ Failed to initialize embedding model: {e}")
        logger.info("Make sure GOOGLE_APPLICATION_CREDENTIALS is set")
        sys.exit(1)
    
    # Load documents
    logger.info("Loading PDF documents...")
    try:
        documents = SimpleDirectoryReader(
            input_dir=str(pdf_path),
            file_extractor={".pdf": None},  # Use default PDF extractor
            recursive=True
        ).load_data()
        logger.info(f"✓ Loaded {len(documents)} documents")
    except Exception as e:
        logger.error(f"✗ Failed to load documents: {e}")
        sys.exit(1)
    
    # Create storage context
    vector_store = ChromaVectorStore(chroma_collection=collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    
    # Create index and embed documents
    logger.info(f"Creating index with chunk_size={chunk_size}, overlap={chunk_overlap}...")
    try:
        index = VectorStoreIndex.from_documents(
            documents,
            storage_context=storage_context,
            embed_model=embed_model,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            show_progress=True
        )
        logger.info("✓ Index created successfully")
    except Exception as e:
        logger.error(f"✗ Failed to create index: {e}")
        sys.exit(1)
    
    # Verify chunks were added
    count = collection.count()
    logger.info(f"✓ Successfully loaded {count} text chunks into collection")
    
    return count


def list_collections(host: str = CHROMADB_HOST, port: int = CHROMADB_PORT):
    """List all ChromaDB collections"""
    client = connect_chromadb(host, port)
    
    collections = client.list_collections()
    
    if not collections:
        logger.info("No collections found")
        return
    
    logger.info(f"\nFound {len(collections)} collection(s):")
    for collection in collections:
        count = collection.count()
        logger.info(f"  📚 {collection.name}")
        logger.info(f"     Chunks: {count}")
        logger.info(f"     Metadata: {collection.metadata}")
        logger.info("")


def get_collection_info(collection_name: str, host: str = CHROMADB_HOST, port: int = CHROMADB_PORT):
    """Get information about a specific collection"""
    client = connect_chromadb(host, port)
    
    try:
        collection = client.get_collection(name=collection_name)
    except Exception as e:
        logger.error(f"✗ Collection not found: {collection_name}")
        logger.info(f"Available collections: {[c.name for c in client.list_collections()]}")
        return
    
    count = collection.count()
    
    logger.info(f"\nCollection: {collection_name}")
    logger.info(f"  Chunks: {count}")
    logger.info(f"  Metadata: {collection.metadata}")
    
    # Try to get sample chunks
    try:
        results = collection.get(limit=3)
        if results['documents']:
            logger.info(f"\n  Sample chunks ({len(results['documents'])} shown):")
            for i, doc in enumerate(results['documents'], 1):
                preview = doc[:100] + "..." if len(doc) > 100 else doc
                logger.info(f"    {i}. {preview}")
    except Exception as e:
        logger.debug(f"Could not retrieve sample chunks: {e}")


def delete_collection(collection_name: str, host: str = CHROMADB_HOST, port: int = CHROMADB_PORT):
    """Delete a ChromaDB collection"""
    client = connect_chromadb(host, port)
    
    try:
        client.delete_collection(name=collection_name)
        logger.info(f"✓ Collection deleted: {collection_name}")
    except Exception as e:
        logger.error(f"✗ Failed to delete collection: {e}")
        sys.exit(1)


def clear_collection(collection_name: str, host: str = CHROMADB_HOST, port: int = CHROMADB_PORT):
    """Clear all documents from a collection"""
    client = connect_chromadb(host, port)
    
    try:
        collection = client.get_collection(name=collection_name)
        # Get all IDs and delete them
        results = collection.get()
        if results['ids']:
            collection.delete(ids=results['ids'])
            logger.info(f"✓ Cleared {len(results['ids'])} chunks from {collection_name}")
        else:
            logger.info(f"Collection {collection_name} is already empty")
    except Exception as e:
        logger.error(f"✗ Failed to clear collection: {e}")
        sys.exit(1)


def test_retrieval(query: str, collection_name: str, top_k: int = 5):
    """Test retrieval for a query"""
    client = connect_chromadb()
    
    try:
        collection = client.get_collection(name=collection_name)
    except Exception as e:
        logger.error(f"✗ Collection not found: {collection_name}")
        sys.exit(1)
    
    logger.info(f"\nTesting retrieval for: '{query}'")
    logger.info(f"Top-K: {top_k}\n")
    
    try:
        results = collection.query(query_texts=[query], n_results=top_k)
        
        if not results['documents'] or not results['documents'][0]:
            logger.info("⚠ No results found")
            return
        
        for i, (doc, dist) in enumerate(zip(results['documents'][0], results['distances'][0]), 1):
            score = 1 - dist  # Convert distance to similarity
            logger.info(f"{i}. [Score: {score:.3f}]")
            logger.info(f"   {doc[:200]}...")
            logger.info("")
    
    except Exception as e:
        logger.error(f"✗ Retrieval failed: {e}")
        sys.exit(1)


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="RAG Knowledge Base Management Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Load PDFs into knowledge base
  python rag_cli.py load --pdf-dir ./knowledge_base/pdfs --collection corn-stress-knowledge
  
  # List all collections
  python rag_cli.py list
  
  # Get collection info
  python rag_cli.py info --collection corn-stress-knowledge
  
  # Test retrieval
  python rag_cli.py test --query "water stress" --collection corn-stress-knowledge
  
  # Clear collection
  python rag_cli.py clear --collection corn-stress-knowledge
  
  # Delete collection
  python rag_cli.py delete --collection corn-stress-knowledge
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Load command
    load_parser = subparsers.add_parser('load', help='Load PDFs into ChromaDB')
    load_parser.add_argument('--pdf-dir', required=True, help='Directory containing PDF files')
    load_parser.add_argument('--collection', default='corn-stress-knowledge', help='Collection name')
    load_parser.add_argument('--chunk-size', type=int, default=1000, help='Chunk size (characters)')
    load_parser.add_argument('--chunk-overlap', type=int, default=100, help='Chunk overlap (characters)')
    load_parser.add_argument('--host', default=CHROMADB_HOST, help='ChromaDB host')
    load_parser.add_argument('--port', type=int, default=CHROMADB_PORT, help='ChromaDB port')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List all collections')
    list_parser.add_argument('--host', default=CHROMADB_HOST, help='ChromaDB host')
    list_parser.add_argument('--port', type=int, default=CHROMADB_PORT, help='ChromaDB port')
    
    # Info command
    info_parser = subparsers.add_parser('info', help='Get collection information')
    info_parser.add_argument('--collection', required=True, help='Collection name')
    info_parser.add_argument('--host', default=CHROMADB_HOST, help='ChromaDB host')
    info_parser.add_argument('--port', type=int, default=CHROMADB_PORT, help='ChromaDB port')
    
    # Test command
    test_parser = subparsers.add_parser('test', help='Test retrieval')
    test_parser.add_argument('--query', required=True, help='Query to test')
    test_parser.add_argument('--collection', default='corn-stress-knowledge', help='Collection name')
    test_parser.add_argument('--top-k', type=int, default=5, help='Number of results')
    
    # Clear command
    clear_parser = subparsers.add_parser('clear', help='Clear collection')
    clear_parser.add_argument('--collection', required=True, help='Collection name')
    clear_parser.add_argument('--host', default=CHROMADB_HOST, help='ChromaDB host')
    clear_parser.add_argument('--port', type=int, default=CHROMADB_PORT, help='ChromaDB port')
    
    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Delete collection')
    delete_parser.add_argument('--collection', required=True, help='Collection name')
    delete_parser.add_argument('--host', default=CHROMADB_HOST, help='ChromaDB host')
    delete_parser.add_argument('--port', type=int, default=CHROMADB_PORT, help='ChromaDB port')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Execute commands
    if args.command == 'load':
        load_pdfs(args.pdf_dir, args.collection, args.chunk_size, args.chunk_overlap)
    
    elif args.command == 'list':
        list_collections(args.host, args.port)
    
    elif args.command == 'info':
        get_collection_info(args.collection, args.host, args.port)
    
    elif args.command == 'test':
        test_retrieval(args.query, args.collection, args.top_k)
    
    elif args.command == 'clear':
        clear_collection(args.collection, args.host, args.port)
    
    elif args.command == 'delete':
        delete_collection(args.collection, args.host, args.port)


if __name__ == '__main__':
    main()
