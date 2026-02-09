"""
Hybrid search combining semantic and keyword-based retrieval.
"""

import logging
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from .vector_store import get_vector_store
from ..ingestion.embedder import EmbeddingGenerator
from ..models import Database

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """A single search result."""
    chunk_id: str
    content: str
    score: float
    document_id: str
    document_title: str
    section_title: Optional[str] = None
    source_type: str = "semantic"  # semantic, keyword, direct_qa

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "content": self.content,
            "score": self.score,
            "document_id": self.document_id,
            "document_title": self.document_title,
            "section_title": self.section_title,
            "source_type": self.source_type
        }


class HybridSearch:
    """
    Hybrid search combining:
    1. Semantic search (embeddings)
    2. Keyword search (BM25-like)
    3. Direct Q&A matching
    """

    def __init__(self):
        self.vector_store = get_vector_store()
        self.embedder = EmbeddingGenerator()
        self.db = Database()

    def search(
        self,
        query: str,
        n_results: int = 5,
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.2,
        qa_weight: float = 0.1,
        document_filter: str = None
    ) -> List[SearchResult]:
        """
        Perform hybrid search.

        Args:
            query: Search query string
            n_results: Number of results to return
            semantic_weight: Weight for semantic search (0-1)
            keyword_weight: Weight for keyword search (0-1)
            qa_weight: Weight for direct Q&A matching (0-1)
            document_filter: Optional document ID to filter by

        Returns:
            List of SearchResult objects, ranked by combined score
        """
        results = []

        # 1. Semantic search
        if semantic_weight > 0:
            semantic_results = self._semantic_search(
                query,
                n_results=n_results * 2,
                document_filter=document_filter
            )
            for r in semantic_results:
                r.score *= semantic_weight
            results.extend(semantic_results)

        # 2. Keyword search
        if keyword_weight > 0:
            keyword_results = self._keyword_search(
                query,
                n_results=n_results * 2,
                document_filter=document_filter
            )
            for r in keyword_results:
                r.score *= keyword_weight
            results.extend(keyword_results)

        # 3. Direct Q&A search
        if qa_weight > 0:
            qa_results = self._qa_search(query, n_results=n_results)
            for r in qa_results:
                r.score *= qa_weight
            results.extend(qa_results)

        # Combine and deduplicate
        combined = self._combine_results(results, n_results)

        return combined

    def _semantic_search(
        self,
        query: str,
        n_results: int,
        document_filter: str = None
    ) -> List[SearchResult]:
        """Perform semantic search using embeddings."""
        try:
            # Generate query embedding
            query_embedding = self.embedder.embed_query(query)

            # Build filter
            where = None
            if document_filter:
                where = {"document_id": document_filter}

            # Search vector store
            results = self.vector_store.search(
                query_embedding=query_embedding,
                n_results=n_results,
                where=where
            )

            search_results = []
            for i, chunk_id in enumerate(results["ids"]):
                # Convert distance to similarity score (cosine distance -> similarity)
                distance = results["distances"][i]
                score = 1 - distance  # Cosine similarity

                metadata = results["metadatas"][i] if results["metadatas"] else {}

                search_results.append(SearchResult(
                    chunk_id=chunk_id,
                    content=results["documents"][i],
                    score=max(0, score),  # Ensure non-negative
                    document_id=metadata.get("document_id", ""),
                    document_title=metadata.get("document_title", "Unknown"),
                    section_title=metadata.get("section_title"),
                    source_type="semantic"
                ))

            return search_results

        except Exception as e:
            logger.error(f"Semantic search error: {e}")
            return []

    def _keyword_search(
        self,
        query: str,
        n_results: int,
        document_filter: str = None
    ) -> List[SearchResult]:
        """
        Perform keyword-based search.
        Uses ChromaDB's where_document filter for simple keyword matching.
        """
        try:
            # Extract keywords from query
            keywords = self._extract_keywords(query)

            if not keywords:
                return []

            # Search for documents containing keywords
            search_results = []

            for keyword in keywords[:5]:  # Limit to top 5 keywords
                # Use ChromaDB's document filter
                where = None
                if document_filter:
                    where = {"document_id": document_filter}

                try:
                    results = self.vector_store.collection.get(
                        where=where,
                        where_document={"$contains": keyword.lower()},
                        include=["documents", "metadatas"],
                        limit=n_results
                    )

                    for i, chunk_id in enumerate(results["ids"]):
                        content = results["documents"][i] if results["documents"] else ""
                        metadata = results["metadatas"][i] if results["metadatas"] else {}

                        # Score based on keyword frequency
                        score = content.lower().count(keyword.lower()) / 10
                        score = min(score, 1.0)  # Cap at 1.0

                        search_results.append(SearchResult(
                            chunk_id=chunk_id,
                            content=content,
                            score=score,
                            document_id=metadata.get("document_id", ""),
                            document_title=metadata.get("document_title", "Unknown"),
                            section_title=metadata.get("section_title"),
                            source_type="keyword"
                        ))
                except Exception as e:
                    logger.debug(f"Keyword search for '{keyword}' failed: {e}")
                    continue

            return search_results

        except Exception as e:
            logger.error(f"Keyword search error: {e}")
            return []

    def _qa_search(self, query: str, n_results: int) -> List[SearchResult]:
        """Search direct Q&A pairs."""
        try:
            # Get all Q&A pairs
            qa_pairs = self.db.get_all_direct_qa()

            if not qa_pairs:
                return []

            # Score each Q&A by similarity to query
            query_lower = query.lower()
            query_words = set(self._extract_keywords(query))

            scored_qa = []
            for qa in qa_pairs:
                question_lower = qa.question.lower()
                question_words = set(self._extract_keywords(qa.question))

                # Calculate simple overlap score
                if query_words and question_words:
                    overlap = len(query_words & question_words)
                    score = overlap / max(len(query_words), len(question_words))
                else:
                    score = 0

                # Boost if exact match
                if query_lower in question_lower or question_lower in query_lower:
                    score = max(score, 0.8)

                if score > 0.1:  # Minimum threshold
                    scored_qa.append((qa, score))

            # Sort by score and take top results
            scored_qa.sort(key=lambda x: x[1], reverse=True)

            results = []
            for qa, score in scored_qa[:n_results]:
                results.append(SearchResult(
                    chunk_id=f"qa_{qa.id}",
                    content=f"Q: {qa.question}\nA: {qa.answer}",
                    score=score,
                    document_id="direct_qa",
                    document_title="Direct Q&A",
                    section_title=qa.category,
                    source_type="direct_qa"
                ))

            return results

        except Exception as e:
            logger.error(f"Q&A search error: {e}")
            return []

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text."""
        # Remove punctuation and split
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())

        # Remove common stop words
        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
            "for", "of", "with", "by", "from", "as", "is", "was", "are",
            "were", "been", "be", "have", "has", "had", "do", "does", "did",
            "will", "would", "could", "should", "may", "might", "can",
            "this", "that", "these", "those", "what", "which", "who",
            "how", "when", "where", "why", "all", "any", "some", "no",
            "not", "only", "just", "also", "very", "too", "more", "most"
        }

        keywords = [w for w in words if w not in stop_words]

        return keywords

    def _combine_results(
        self,
        results: List[SearchResult],
        n_results: int
    ) -> List[SearchResult]:
        """
        Combine and deduplicate results from different sources.

        Uses chunk_id for deduplication, keeping highest score.
        """
        # Group by chunk_id
        by_id = {}
        for r in results:
            if r.chunk_id in by_id:
                # Keep higher score, combine sources
                existing = by_id[r.chunk_id]
                if r.score > existing.score:
                    r.source_type = f"{existing.source_type}+{r.source_type}"
                    by_id[r.chunk_id] = r
                else:
                    existing.source_type = f"{existing.source_type}+{r.source_type}"
                    existing.score = max(existing.score, r.score)
            else:
                by_id[r.chunk_id] = r

        # Sort by score
        combined = sorted(by_id.values(), key=lambda x: x.score, reverse=True)

        return combined[:n_results]

    def get_context_for_query(
        self,
        query: str,
        max_tokens: int = 2000
    ) -> List[SearchResult]:
        """
        Get context chunks for LLM generation.

        Retrieves relevant chunks up to max_tokens.
        """
        # Get more results than needed, then trim by tokens
        results = self.search(query, n_results=10)

        selected = []
        total_tokens = 0

        for r in results:
            # Estimate tokens (rough: 4 chars per token)
            chunk_tokens = len(r.content) // 4

            if total_tokens + chunk_tokens > max_tokens:
                break

            selected.append(r)
            total_tokens += chunk_tokens

        return selected
