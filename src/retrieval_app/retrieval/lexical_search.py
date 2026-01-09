"""
Lexical Search Module.

Implements BM25-based sparse retrieval for keyword matching.
Complements semantic search for better recall on exact terms.
"""

import re
from typing import Optional
from dataclasses import dataclass

from retrieval_app.data_prep.chunker import Chunk
from retrieval_app.retrieval.vector_store import SearchResult


@dataclass
class TokenizedChunk:
    """Chunk with tokenized content for BM25."""
    chunk: Chunk
    tokens: list[str]


class LexicalSearcher:
    """
    BM25-based lexical search.

    Why lexical search matters:
    - Handles exact keyword matches that embeddings might miss
    - Better for rare terms, proper nouns, codes, and IDs
    - Complements semantic search for hybrid retrieval
    """

    def __init__(
        self,
        k1: float = 1.5,
        b: float = 0.75,
        stop_words: Optional[set[str]] = None
    ):
        self.k1 = k1
        self.b = b
        self.stop_words = stop_words or self._default_stop_words()
        self._chunks: list[TokenizedChunk] = []
        self._bm25 = None
        self._corpus: list[list[str]] = []

    def _default_stop_words(self) -> set[str]:
        """Common English stop words."""
        return {
            "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
            "has", "he", "in", "is", "it", "its", "of", "on", "that", "the",
            "to", "was", "were", "will", "with", "the", "this", "but", "they",
            "have", "had", "what", "when", "where", "who", "which", "why", "how"
        }

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize text for BM25."""
        text = text.lower()
        tokens = re.findall(r'\b\w+\b', text)
        tokens = [t for t in tokens if t not in self.stop_words and len(t) > 1]
        return tokens

    def index_chunks(self, chunks: list[Chunk]) -> None:
        """Index chunks for lexical search."""
        self._chunks = []
        self._corpus = []

        for chunk in chunks:
            tokens = self._tokenize(chunk.content)
            self._chunks.append(TokenizedChunk(chunk=chunk, tokens=tokens))
            self._corpus.append(tokens)

        self._build_bm25_index()

    def _build_bm25_index(self) -> None:
        """Build BM25 index from corpus."""
        try:
            from rank_bm25 import BM25Okapi
            self._bm25 = BM25Okapi(self._corpus, k1=self.k1, b=self.b)
        except ImportError:
            self._bm25 = None

    def search(
        self,
        query: str,
        top_k: int = 10,
        metadata_filter: Optional[dict] = None
    ) -> list[SearchResult]:
        """Search using BM25."""
        if not self._chunks:
            return []

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        if self._bm25 is not None:
            scores = self._bm25.get_scores(query_tokens)
        else:
            scores = self._simple_bm25_scores(query_tokens)

        results = []
        for i, score in enumerate(scores):
            if score > 0:
                chunk = self._chunks[i].chunk

                if metadata_filter:
                    if not self._matches_filter(chunk.metadata, metadata_filter):
                        continue

                results.append(SearchResult(
                    chunk=chunk,
                    score=float(score),
                    search_type="lexical"
                ))

        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]

    def _simple_bm25_scores(self, query_tokens: list[str]) -> list[float]:
        """Simple BM25 implementation when rank_bm25 is not available."""
        import math

        N = len(self._corpus)
        if N == 0:
            return []

        avgdl = sum(len(doc) for doc in self._corpus) / N

        df = {}
        for doc in self._corpus:
            seen = set()
            for token in doc:
                if token not in seen:
                    df[token] = df.get(token, 0) + 1
                    seen.add(token)

        scores = []
        for doc in self._corpus:
            score = 0.0
            doc_len = len(doc)
            tf = {}
            for token in doc:
                tf[token] = tf.get(token, 0) + 1

            for token in query_tokens:
                if token in tf:
                    token_df = df.get(token, 0)
                    idf = math.log((N - token_df + 0.5) / (token_df + 0.5) + 1)
                    token_tf = tf[token]
                    tf_component = (
                        token_tf * (self.k1 + 1) /
                        (token_tf + self.k1 * (1 - self.b + self.b * doc_len / avgdl))
                    )
                    score += idf * tf_component

            scores.append(score)

        return scores

    def _matches_filter(self, metadata: dict, filter_dict: dict) -> bool:
        """Check if metadata matches filter criteria."""
        for key, value in filter_dict.items():
            if key not in metadata:
                return False
            if isinstance(value, dict):
                if "$eq" in value and metadata[key] != value["$eq"]:
                    return False
                if "$in" in value and metadata[key] not in value["$in"]:
                    return False
            elif metadata[key] != value:
                return False
        return True

    def get_term_frequencies(self, chunk_id: str) -> dict[str, int]:
        """Get term frequencies for a specific chunk."""
        for tc in self._chunks:
            if tc.chunk.id == chunk_id:
                tf = {}
                for token in tc.tokens:
                    tf[token] = tf.get(token, 0) + 1
                return tf
        return {}
