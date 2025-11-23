#!/usr/bin/env python3
"""
ChromaDB Connectivity Diagnostic
"""
import sys

print("=" * 70)
print("ChromaDB Diagnostics")
print("=" * 70)
print()

# Test 1: Check ChromaDB HTTP connection
print("1. Testing ChromaDB HTTP connection...")
try:
    import requests
    response = requests.get("http://chromadb:8000/api/v2/heartbeat", timeout=5)
    print(f"   ✓ HTTP connection successful: {response.status_code}")
    print(f"   Response: {response.json()}")
except Exception as e:
    print(f"   ✗ HTTP connection failed: {e}")

print()

# Test 2: Check ChromaDB Python client
print("2. Testing ChromaDB Python client...")
try:
    import chromadb
    print(f"   ✓ chromadb imported: {chromadb.__version__}")
    
    client = chromadb.HttpClient(host="chromadb", port=8000)
    print(f"   ✓ HttpClient created")
    
    # Try to get settings
    settings = client.get_settings()
    print(f"   ✓ Got settings: {settings}")
    
except Exception as e:
    print(f"   ✗ Failed: {e}")
    import traceback
    traceback.print_exc()

print()

# Test 3: Try to create a collection
print("3. Testing collection creation...")
try:
    import chromadb
    
    client = chromadb.HttpClient(host="chromadb", port=8000)
    
    collection = client.get_or_create_collection(
        name="test-collection",
        metadata={"hnsw:space": "cosine"}
    )
    print(f"   ✓ Collection created/retrieved: {collection.name}")
    print(f"   Collection count: {collection.count()}")
    
except Exception as e:
    print(f"   ✗ Failed: {e}")
    import traceback
    traceback.print_exc()

print()
print("Diagnostic complete")
