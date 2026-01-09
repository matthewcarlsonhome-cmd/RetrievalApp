"""
Query Processor Module.

Handles query rewriting and decomposition for better retrieval.
"""

from dataclasses import dataclass
from typing import Optional
import re


@dataclass
class ProcessedQuery:
    """Result of query processing."""
    original_query: str
    rewritten_query: str
    sub_queries: list[str]
    extracted_filters: dict
    query_type: str


class QueryProcessor:
    """
    Processes queries to improve retrieval quality.

    Techniques:
    - Query rewriting for better semantic matching
    - Query decomposition for complex questions
    - Filter extraction from natural language
    - Typo correction and normalization
    """

    def __init__(
        self,
        enable_rewriting: bool = True,
        enable_decomposition: bool = True,
        llm_rewriter: Optional[callable] = None
    ):
        self.enable_rewriting = enable_rewriting
        self.enable_decomposition = enable_decomposition
        self.llm_rewriter = llm_rewriter

        self._filter_patterns = {
            "date": [
                r"(from|after|since) (\d{4})",
                r"(before|until) (\d{4})",
                r"in (\d{4})",
                r"(last|past) (\d+) (days?|weeks?|months?|years?)",
            ],
            "category": [
                r"(about|regarding|on) ([\w\s]+)",
                r"(in|under) category ([\w\s]+)",
            ],
            "author": [
                r"by ([\w\s]+)",
                r"(written|authored|created) by ([\w\s]+)",
            ],
        }

    def process(self, query: str) -> ProcessedQuery:
        """
        Process a query for optimal retrieval.

        Args:
            query: The original user query

        Returns:
            ProcessedQuery with rewritten query and metadata
        """
        normalized = self._normalize(query)
        filters = self._extract_filters(normalized)
        cleaned = self._remove_filter_phrases(normalized, filters)

        if self.enable_rewriting:
            rewritten = self._rewrite_query(cleaned)
        else:
            rewritten = cleaned

        if self.enable_decomposition:
            sub_queries = self._decompose_query(rewritten)
        else:
            sub_queries = [rewritten]

        query_type = self._classify_query_type(query)

        return ProcessedQuery(
            original_query=query,
            rewritten_query=rewritten,
            sub_queries=sub_queries,
            extracted_filters=filters,
            query_type=query_type
        )

    def _normalize(self, query: str) -> str:
        """Normalize query text."""
        query = query.strip()
        query = re.sub(r'\s+', ' ', query)
        query = query.rstrip('?').strip()

        return query

    def _extract_filters(self, query: str) -> dict:
        """Extract metadata filters from query."""
        filters = {}

        for filter_type, patterns in self._filter_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, query, re.IGNORECASE)
                if match:
                    if filter_type == "date":
                        filters["date"] = match.group(0)
                    elif filter_type == "category":
                        filters["category"] = match.group(2).strip()
                    elif filter_type == "author":
                        author = match.group(2) if match.lastindex >= 2 else match.group(1)
                        filters["author"] = author.strip()
                    break

        return filters

    def _remove_filter_phrases(self, query: str, filters: dict) -> str:
        """Remove filter phrases from query for cleaner retrieval."""
        result = query

        for filter_type, patterns in self._filter_patterns.items():
            if filter_type in filters:
                for pattern in patterns:
                    result = re.sub(pattern, '', result, flags=re.IGNORECASE)

        result = re.sub(r'\s+', ' ', result).strip()
        return result

    def _rewrite_query(self, query: str) -> str:
        """Rewrite query for better retrieval."""
        if self.llm_rewriter:
            return self.llm_rewriter(query)

        expansions = {
            "ML": "machine learning ML",
            "AI": "artificial intelligence AI",
            "NLP": "natural language processing NLP",
            "API": "application programming interface API",
            "DB": "database DB",
            "UI": "user interface UI",
            "UX": "user experience UX",
        }

        result = query
        for abbrev, expansion in expansions.items():
            pattern = r'\b' + abbrev + r'\b'
            if re.search(pattern, result):
                result = re.sub(pattern, expansion, result)

        return result

    def _decompose_query(self, query: str) -> list[str]:
        """Decompose complex queries into simpler sub-queries."""
        sub_queries = []

        if " and " in query.lower():
            parts = re.split(r'\s+and\s+', query, flags=re.IGNORECASE)
            if len(parts) > 1 and all(len(p.split()) >= 2 for p in parts):
                sub_queries.extend(parts)

        if re.search(r'(compare|difference|vs\.?|versus)', query, re.IGNORECASE):
            match = re.search(
                r'(compare|difference between)?\s*([\w\s]+?)\s+(and|vs\.?|versus)\s+([\w\s]+)',
                query,
                re.IGNORECASE
            )
            if match:
                item1 = match.group(2).strip()
                item2 = match.group(4).strip()
                sub_queries.append(f"What is {item1}")
                sub_queries.append(f"What is {item2}")

        if not sub_queries:
            sub_queries = [query]

        return sub_queries

    def _classify_query_type(self, query: str) -> str:
        """Classify the type of query."""
        query_lower = query.lower()

        if any(w in query_lower for w in ["how to", "how do", "steps", "process"]):
            return "procedural"
        elif any(w in query_lower for w in ["why", "reason", "cause"]):
            return "explanatory"
        elif any(w in query_lower for w in ["what is", "define", "meaning"]):
            return "definitional"
        elif any(w in query_lower for w in ["list", "examples", "types of"]):
            return "enumerative"
        elif any(w in query_lower for w in ["compare", "difference", "vs"]):
            return "comparative"
        else:
            return "factual"

    def expand_with_synonyms(self, query: str) -> list[str]:
        """Generate query variants with synonyms."""
        variants = [query]

        synonym_map = {
            "error": ["issue", "problem", "bug", "exception"],
            "fix": ["resolve", "solve", "repair", "address"],
            "create": ["make", "build", "generate", "produce"],
            "delete": ["remove", "erase", "drop", "clear"],
            "update": ["modify", "change", "edit", "revise"],
            "get": ["retrieve", "fetch", "obtain", "acquire"],
        }

        query_lower = query.lower()
        for word, synonyms in synonym_map.items():
            if word in query_lower:
                for synonym in synonyms[:2]:
                    variant = re.sub(
                        r'\b' + word + r'\b',
                        synonym,
                        query,
                        flags=re.IGNORECASE
                    )
                    if variant != query:
                        variants.append(variant)

        return variants
