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
