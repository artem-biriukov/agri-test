import os, sys, logging, uuid, requests, time
from pathlib import Path
from PyPDF2 import PdfReader

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

URL = "http://chromadb:8000/api/v2"
COLLECTION = "corn-stress-knowledge"

logger.info("=== RAG Seeder ===")

for attempt in range(10):
    try:
        if requests.get(f"{URL}/heartbeat", timeout=5).status_code == 200:
            logger.info("✓ ChromaDB ready")
            break
    except:
        pass
    if attempt < 9:
        logger.info(f"Waiting... ({attempt+1}/10)")
        time.sleep(2)
else:
    logger.error("✗ Timeout")
    sys.exit(1)

pdfs = list(Path("./knowledge_base/pdfs").glob("*.pdf"))
logger.info(f"📚 {len(pdfs)} PDFs")

docs, ids, metas = [], [], []
for pdf in pdfs:
    logger.info(f"  {pdf.name}")
    reader = PdfReader(pdf)
    for page in enumerate(reader.pages):
        text = page[1].extract_text()
        if text.strip():
            for j in range(0, len(text), 900):
                chunk = text[j : j + 1000]
                if len(chunk.strip()) > 100:
                    docs.append(chunk)
                    ids.append(str(uuid.uuid4()))
                    metas.append({"source": pdf.name})
    logger.info(f"    ✓ Added")

if not docs:
    logger.error("No text")
    sys.exit(1)

logger.info(f"💾 {len(docs)} chunks")
try:
    requests.post(f"{URL}/collections", json={"name": COLLECTION, "metadata": {"hnsw:space": "cosine"}}, timeout=10)
except:
    pass

for i in range(0, len(docs), 50):
    logger.info(f"  Batch {i//50 + 1}...")
    requests.post(
        f"{URL}/collections/{COLLECTION}/add",
        json={"ids": ids[i : i + 50], "documents": docs[i : i + 50], "metadatas": metas[i : i + 50]},
        timeout=30,
    )

logger.info("✓ Done!")
