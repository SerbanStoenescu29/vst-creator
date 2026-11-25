"""Build the RAG index from rag_data/juce_modules (see rag.py)."""
try:
    import truststore

    truststore.inject_into_ssl()
except ImportError:
    pass
from dotenv import load_dotenv

load_dotenv()
import rag

print("Done:", rag.build_index(), "chunks")
import storage
if storage.enabled():  # keep a copy on S3 as well
    for name in ("chunks.json", "vectors.npy"):
        print("uploaded:", storage.upload_file(rag.INDEX_DIR / name, f"knowledge/index/{name}"))
