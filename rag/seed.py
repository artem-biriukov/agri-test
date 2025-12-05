from pypdf import PdfReader
import os
import chromadb

CHROMADB_HOST = os.getenv("CHROMADB_HOST", "localhost")
CHROMADB_PORT = int(os.getenv("CHROMADB_PORT", 8000))


def extract_text_from_pdf(pdf_path):
    """Extract text from PDF file"""
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return ""


def chunk_text(text, chunk_size=500):
    """Split text into chunks"""
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
    return chunks


def seed_knowledge_base():
    """Seed ChromaDB with agricultural documents"""
    try:
        client = chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)

        try:
            client.delete_collection("corn-stress-knowledge")
        except Exception:
            pass

        collection = client.create_collection("corn-stress-knowledge")

        knowledge_dir = "knowledge_base"
        if not os.path.exists(knowledge_dir):
            print("No knowledge_base directory found")
            return

        for filename in os.listdir(knowledge_dir):
            if filename.endswith(".pdf"):
                pdf_path = os.path.join(knowledge_dir, filename)
                text = extract_text_from_pdf(pdf_path)
                chunks = chunk_text(text)

                collection.add(
                    documents=chunks,
                    ids=[f"{filename}_{i}" for i in range(len(chunks))],
                    metadatas=[{"source": filename} for _ in range(len(chunks))],
                )
                print(f"Seeded: {filename}")

        print("Knowledge base seeded successfully")
    except Exception as e:
        print(f"Error seeding knowledge base: {e}")


if __name__ == "__main__":
    seed_knowledge_base()
