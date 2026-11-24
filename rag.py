"""Small RAG over the JUCE headers in rag_data/juce_modules.

Build the index once (needs OPENAI_API_KEY, costs a few cents):

    python build_rag_index.py

The index (rag_data/index/) is what the app loads; the headers are only needed to rebuild it.
"""

import json
import os
import re
from pathlib import Path

import resilience
import numpy as np

RAG_DIR = Path(os.getenv("RAG_DIR", Path(__file__).parent / "rag_data"))
SOURCE_DIR = RAG_DIR / "juce_modules"
INDEX_DIR = RAG_DIR / "index"
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")
EMBED_DIMS = 512
MAX_CHUNK_CHARS = 2000

_DOC = re.compile(r"/\*\*.*?\*/", re.S)
_index = None  # (chunks, vectors), loaded on first use


def _clean(text: str) -> str:
    lines = [re.sub(r"^\s*\*+/?\s?", "", ln).rstrip() for ln in text.splitlines()]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def chunk_header(rel: str, text: str) -> list[str]:
    """One chunk per doxygen comment block, followed by the declaration it documents."""
    chunks = []
    for m in _DOC.finditer(text):
        doc = _clean(m.group(0).removeprefix("/**").removesuffix("*/"))
        if len(doc) < 60:
            continue
        decl = []
        for line in text[m.end():].lstrip("\r\n").splitlines()[:6]:
            decl.append(line.rstrip())
            if "{" in line or ";" in line:
                break
        chunk = f"[{rel}]\n{doc}\n{chr(10).join(decl)}".strip()
        chunks.append(chunk[:MAX_CHUNK_CHARS])
    return chunks


def _embed(texts: list[str]) -> np.ndarray:
    response = resilience.post(
        "https://api.openai.com/v1/embeddings",
        headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
        json={"model": EMBED_MODEL, "input": texts, "dimensions": EMBED_DIMS},
        timeout=120,
    )
    vectors = np.array([d["embedding"] for d in response.json()["data"]], dtype=np.float32)
    return vectors / np.linalg.norm(vectors, axis=1, keepdims=True)


def build_index() -> int:
    chunks = []
    for path in sorted(SOURCE_DIR.rglob("*.h")):
        chunks += chunk_header(path.relative_to(SOURCE_DIR).as_posix(), path.read_text(encoding="utf-8", errors="replace"))
    print(f"{len(chunks)} chunks, embedding...")
    parts = []
    for i in range(0, len(chunks), 100):
        parts.append(_embed(chunks[i : i + 100]))
        if (i // 100) % 10 == 0:
            print(f"  {i}/{len(chunks)}")
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    (INDEX_DIR / "chunks.json").write_text(json.dumps(chunks), encoding="utf-8")
    np.save(INDEX_DIR / "vectors.npy", np.vstack(parts).astype(np.float16))
    return len(chunks)


def _load():
    global _index
    if _index is None:
        chunks_file, vectors_file = INDEX_DIR / "chunks.json", INDEX_DIR / "vectors.npy"
        if not (chunks_file.exists() and vectors_file.exists()):
            return None
        _index = (json.loads(chunks_file.read_text(encoding="utf-8")), np.load(vectors_file).astype(np.float32))
    return _index


def search(queries: list[str], per_query: int = 4, max_chars: int = 14000) -> tuple[str, list[dict]]:
    """The best chunks for each query, de-duplicated: (one text block, [{"file", "score"}]).

    Empty results if there is no index. The score is the cosine similarity of the best query (0 to 1).
    """
    index = _load()
    if index is None or not queries:
        return "", []
    chunks, vectors = index
    scores = vectors @ _embed(queries).T  # (chunks, queries)
    picked, seen = [], set()
    for rank in range(per_query):
        for q in range(len(queries)):
            i = int(np.argsort(-scores[:, q])[rank])
            if i not in seen:
                seen.add(i)
                picked.append(i)
    out, sources, size = [], {}, 0
    for i in picked:
        if size + len(chunks[i]) > max_chars:
            break
        out.append(chunks[i])
        size += len(chunks[i])
        file = chunks[i].split("]", 1)[0].lstrip("[")
        sources[file] = max(sources.get(file, 0.0), round(float(scores[i].max()), 3))
    found = [{"file": f, "score": sc} for f, sc in sorted(sources.items(), key=lambda kv: -kv[1])]
    return "\n\n---\n\n".join(out), found


def retrieve(queries: list[str], per_query: int = 4, max_chars: int = 14000) -> str:
    return search(queries, per_query, max_chars)[0]
