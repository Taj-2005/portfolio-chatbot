"""
BM25-based lexical retriever (opt-in).

Docs describe the default system as keyword/intent-based (no embeddings / no vector DB).
This module adds a modern lexical retriever (BM25) that can be enabled internally
without changing any API contracts. It improves recall vs naive keyword search while
remaining explainable and dependency-light.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple

from ..utils.text_processing import tokenize_for_retrieval


@dataclass(frozen=True)
class Chunk:
    source: str
    text: str


class BM25Retriever:
    """
    Tiny BM25 implementation (Okapi) to avoid introducing heavy dependencies.
    Intended for small corpora (resume + a few web snippets).
    """

    def __init__(self, chunks: Sequence[Chunk]):
        self._chunks = list(chunks)
        self._docs_tokens: List[List[str]] = [tokenize_for_retrieval(c.text) for c in self._chunks]
        self._doc_lens = [len(toks) for toks in self._docs_tokens]
        self._avgdl = (sum(self._doc_lens) / len(self._doc_lens)) if self._doc_lens else 0.0

        # term -> document frequency
        self._df = {}
        for toks in self._docs_tokens:
            for term in set(toks):
                self._df[term] = self._df.get(term, 0) + 1

        self._N = len(self._docs_tokens)

    def score(self, query: str, k1: float = 1.2, b: float = 0.75) -> List[float]:
        q_terms = tokenize_for_retrieval(query)
        if not q_terms or self._N == 0:
            return [0.0 for _ in range(self._N)]

        scores = []
        for doc_idx, doc_terms in enumerate(self._docs_tokens):
            dl = self._doc_lens[doc_idx] or 1
            tf = {}
            for t in doc_terms:
                tf[t] = tf.get(t, 0) + 1

            s = 0.0
            for term in q_terms:
                df = self._df.get(term, 0)
                if df == 0:
                    continue
                # IDF with +1 smoothing
                idf = math.log(1.0 + (self._N - df + 0.5) / (df + 0.5))
                freq = tf.get(term, 0)
                if freq == 0:
                    continue
                denom = freq + k1 * (1.0 - b + b * (dl / (self._avgdl or 1.0)))
                s += idf * (freq * (k1 + 1.0) / denom)
            scores.append(s)

        return scores

    def top_k(self, query: str, k: int) -> List[Tuple[Chunk, float]]:
        scores = self.score(query)
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        out: List[Tuple[Chunk, float]] = []
        for idx, s in ranked[: max(0, int(k))]:
            if s <= 0:
                continue
            out.append((self._chunks[idx], s))
        return out


def build_chunks_from_sources(
    sections: dict,
    project_data: dict | None,
    web_content: Iterable[Tuple[str, str]],
    searchapi_content: str | None,
) -> List[Chunk]:
    chunks: List[Chunk] = []

    # Resume sections (highest trust)
    for name, content in (sections or {}).items():
        c = (content or "").strip()
        if c:
            chunks.append(Chunk(source=f"RESUME_{name}", text=c))

    # project.json normalized text
    if project_data:
        if project_data.get("featured_text"):
            chunks.append(Chunk(source="PROJECT_FEATURED", text=str(project_data["featured_text"])))
        if project_data.get("text_for_rag"):
            chunks.append(Chunk(source="PROJECTS_JSON", text=str(project_data["text_for_rag"])))

    # GitHub/web scraped content
    for src, content in list(web_content or []):
        c = (content or "").strip()
        if c:
            chunks.append(Chunk(source=f"WEB_{src}", text=c))

    # Search API snippets (lowest trust)
    if searchapi_content:
        chunks.append(Chunk(source="SEARCHAPI", text=searchapi_content))

    return chunks

