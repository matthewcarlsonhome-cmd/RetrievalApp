#!/usr/bin/env python3
"""
Vector Store Module - Chunking, Embedding, and Persistence

This module handles:
1. Document chunking with configurable strategies
2. Vector embedding generation
3. Vector persistence to disk
4. Similarity search with chunked documents

Optimal Chunk Size Analysis for Healthcare Resume Data:
- Resume size: 1,500-5,000 chars (400-1,200 tokens)
- Job size: 2,300-2,500 chars (~600 tokens)
- Model limit (all-MiniLM-L6-v2): 256 tokens

RECOMMENDATION:
- Chunk size: 200 tokens (~800 chars)
- Overlap: 50 tokens (~200 chars)
- Strategy: Semantic chunking by resume section
"""

import json
import hashlib
import pickle
import logging
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, Literal
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

class ChunkStrategy(Enum):
    """Available chunking strategies."""
    FIXED = "fixed"           # Fixed character count chunks
    SEMANTIC = "semantic"     # Chunk by document sections
    SENTENCE = "sentence"     # Chunk by sentence boundaries
    HYBRID = "hybrid"         # Semantic sections with size limits


@dataclass
class ChunkConfig:
    """Configuration for chunking."""
    strategy: ChunkStrategy = ChunkStrategy.SEMANTIC
    max_chunk_chars: int = 800       # ~200 tokens
    overlap_chars: int = 200         # ~50 tokens overlap
    min_chunk_chars: int = 100       # Don't create tiny chunks


@dataclass
class Chunk:
    """A chunk of a document."""
    id: str
    document_id: str
    document_type: Literal["resume", "job"]
    content: str
    section: str              # e.g., "summary", "experience_0", "skills"
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "document_id": self.document_id,
            "document_type": self.document_type,
            "content": self.content,
            "section": self.section,
            "metadata": self.metadata,
            # Don't include embedding in dict - stored separately
        }


@dataclass
class SearchResult:
    """Result from vector search."""
    chunk: Chunk
    score: float
    document_id: str


# =============================================================================
# DOCUMENT CHUNKER
# =============================================================================

class DocumentChunker:
    """Chunks documents using various strategies."""

    def __init__(self, config: ChunkConfig = None):
        self.config = config or ChunkConfig()

    def chunk_resume(self, resume: Dict) -> List[Chunk]:
        """Chunk a resume into searchable sections."""
        chunks = []
        doc_id = resume.get("id", "unknown")
        base_metadata = {
            "name": resume.get("personal_info", {}).get("name", "Unknown"),
            "primary_ehr": resume.get("primary_ehr_system", ""),
            "years_exp": resume.get("years_experience", 0)
        }

        # Summary chunk
        if summary := resume.get("summary"):
            chunks.append(Chunk(
                id=f"{doc_id}_summary",
                document_id=doc_id,
                document_type="resume",
                content=summary,
                section="summary",
                metadata={**base_metadata, "section_type": "summary"}
            ))

        # Experience chunks - one per position
        for i, exp in enumerate(resume.get("experience", [])):
            exp_text = self._experience_to_text(exp)
            if exp_text:
                chunks.append(Chunk(
                    id=f"{doc_id}_exp_{i}",
                    document_id=doc_id,
                    document_type="resume",
                    content=exp_text,
                    section=f"experience_{i}",
                    metadata={
                        **base_metadata,
                        "section_type": "experience",
                        "employer": exp.get("employer", ""),
                        "title": exp.get("title", ""),
                        "ehr_systems": exp.get("ehr_systems", []),
                        "modules": exp.get("modules", [])
                    }
                ))

        # Education chunk
        edu_texts = []
        for edu in resume.get("education", []):
            edu_texts.append(f"{edu.get('degree', '')} from {edu.get('institution', '')}")
        if edu_texts:
            chunks.append(Chunk(
                id=f"{doc_id}_education",
                document_id=doc_id,
                document_type="resume",
                content=" | ".join(edu_texts),
                section="education",
                metadata={**base_metadata, "section_type": "education"}
            ))

        # Certifications chunk
        if certs := resume.get("certifications", []):
            chunks.append(Chunk(
                id=f"{doc_id}_certifications",
                document_id=doc_id,
                document_type="resume",
                content="Certifications: " + ", ".join(certs),
                section="certifications",
                metadata={**base_metadata, "section_type": "certifications"}
            ))

        # Skills chunk
        if skills := resume.get("skills", []):
            chunks.append(Chunk(
                id=f"{doc_id}_skills",
                document_id=doc_id,
                document_type="resume",
                content="Skills: " + ", ".join(skills),
                section="skills",
                metadata={**base_metadata, "section_type": "skills"}
            ))

        # Apply size limits if needed
        chunks = self._apply_size_limits(chunks)

        logger.debug(f"Chunked resume {doc_id} into {len(chunks)} chunks")
        return chunks

    def chunk_job(self, job: Dict) -> List[Chunk]:
        """Chunk a job description."""
        chunks = []
        doc_id = job.get("id", "unknown")
        base_metadata = {
            "title": job.get("title", ""),
            "employer": job.get("employer", ""),
            "primary_ehr": job.get("primary_ehr_system", "")
        }

        # Main description chunk
        desc_parts = [
            job.get("title", ""),
            job.get("description", ""),
            f"EHR System: {job.get('primary_ehr_system', '')}"
        ]
        if modules := job.get("modules", []):
            desc_parts.append(f"Modules: {', '.join(modules)}")

        chunks.append(Chunk(
            id=f"{doc_id}_description",
            document_id=doc_id,
            document_type="job",
            content=" ".join(desc_parts),
            section="description",
            metadata={**base_metadata, "section_type": "description"}
        ))

        # Requirements chunk
        req = job.get("required_qualifications", {})
        pref = job.get("preferred_qualifications", {})
        req_parts = []

        if skills := req.get("skills", []):
            req_parts.append(f"Required skills: {', '.join(skills)}")
        if certs := req.get("certifications", []):
            req_parts.append(f"Required certifications: {', '.join(certs)}")
        if skills := pref.get("skills", []):
            req_parts.append(f"Preferred skills: {', '.join(skills)}")
        if certs := pref.get("certifications", []):
            req_parts.append(f"Preferred certifications: {', '.join(certs)}")

        if req_parts:
            chunks.append(Chunk(
                id=f"{doc_id}_requirements",
                document_id=doc_id,
                document_type="job",
                content=" | ".join(req_parts),
                section="requirements",
                metadata={**base_metadata, "section_type": "requirements"}
            ))

        # Responsibilities chunk
        if responsibilities := job.get("responsibilities", []):
            chunks.append(Chunk(
                id=f"{doc_id}_responsibilities",
                document_id=doc_id,
                document_type="job",
                content="Responsibilities: " + "; ".join(responsibilities),
                section="responsibilities",
                metadata={**base_metadata, "section_type": "responsibilities"}
            ))

        logger.debug(f"Chunked job {doc_id} into {len(chunks)} chunks")
        return chunks

    def _experience_to_text(self, exp: Dict) -> str:
        """Convert experience entry to searchable text."""
        parts = []
        if title := exp.get("title"):
            parts.append(title)
        if employer := exp.get("employer"):
            parts.append(f"at {employer}")
        if ehr_systems := exp.get("ehr_systems", []):
            parts.append(f"EHR: {', '.join(ehr_systems)}")
        if modules := exp.get("modules", []):
            parts.append(f"Modules: {', '.join(modules)}")
        if achievements := exp.get("achievements", []):
            parts.append("Achievements: " + "; ".join(achievements[:3]))
        return " | ".join(parts)

    def _apply_size_limits(self, chunks: List[Chunk]) -> List[Chunk]:
        """Split chunks that exceed size limits."""
        result = []
        for chunk in chunks:
            if len(chunk.content) <= self.config.max_chunk_chars:
                result.append(chunk)
            else:
                # Split large chunks
                sub_chunks = self._split_chunk(chunk)
                result.extend(sub_chunks)
        return result

    def _split_chunk(self, chunk: Chunk) -> List[Chunk]:
        """Split a chunk that's too large."""
        content = chunk.content
        max_size = self.config.max_chunk_chars
        overlap = self.config.overlap_chars
        sub_chunks = []
        start = 0
        part_num = 0

        while start < len(content):
            end = start + max_size
            # Try to break at sentence boundary
            if end < len(content):
                # Look for sentence end
                for sep in ['. ', '| ', '; ', ', ']:
                    last_sep = content[start:end].rfind(sep)
                    if last_sep > max_size // 2:
                        end = start + last_sep + len(sep)
                        break

            sub_content = content[start:end].strip()
            if len(sub_content) >= self.config.min_chunk_chars:
                sub_chunks.append(Chunk(
                    id=f"{chunk.id}_part{part_num}",
                    document_id=chunk.document_id,
                    document_type=chunk.document_type,
                    content=sub_content,
                    section=f"{chunk.section}_part{part_num}",
                    metadata={**chunk.metadata, "is_split": True, "part": part_num}
                ))
                part_num += 1

            start = end - overlap

        return sub_chunks if sub_chunks else [chunk]


# =============================================================================
# VECTOR STORE
# =============================================================================

class VectorStore:
    """
    Persistent vector store for document chunks.

    Stores:
    - chunks.json: Chunk metadata (without embeddings)
    - embeddings.npy: Numpy array of embeddings
    - index_meta.json: Index metadata and statistics
    """

    def __init__(
        self,
        store_path: Path,
        model_name: str = "all-MiniLM-L6-v2",
        chunk_config: ChunkConfig = None
    ):
        self.store_path = Path(store_path)
        self.model_name = model_name
        self.chunk_config = chunk_config or ChunkConfig()
        self.chunker = DocumentChunker(self.chunk_config)

        self.chunks: List[Chunk] = []
        self.embeddings = None
        self.model = None

        # Index tracking
        self.document_ids: set = set()
        self.chunk_index: Dict[str, int] = {}  # chunk_id -> index in embeddings

        self._ensure_store_dir()

    def _ensure_store_dir(self):
        """Create store directory if needed."""
        self.store_path.mkdir(parents=True, exist_ok=True)

    def _load_model(self):
        """Lazy load the embedding model."""
        if self.model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info(f"Loading embedding model: {self.model_name}")
                self.model = SentenceTransformer(self.model_name)
                logger.info("Model loaded successfully")
            except ImportError:
                raise ImportError(
                    "VectorStore requires sentence-transformers. "
                    "Install with: pip install sentence-transformers"
                )

    def add_documents(
        self,
        documents: List[Dict],
        doc_type: Literal["resume", "job"],
        show_progress: bool = True
    ) -> int:
        """
        Add documents to the vector store.

        Returns the number of chunks created.
        """
        self._load_model()

        # Chunk documents
        new_chunks = []
        for doc in documents:
            doc_id = doc.get("id", "unknown")
            if doc_id in self.document_ids:
                logger.warning(f"Document {doc_id} already indexed, skipping")
                continue

            if doc_type == "resume":
                chunks = self.chunker.chunk_resume(doc)
            else:
                chunks = self.chunker.chunk_job(doc)

            new_chunks.extend(chunks)
            self.document_ids.add(doc_id)

        if not new_chunks:
            return 0

        # Generate embeddings
        logger.info(f"Generating embeddings for {len(new_chunks)} chunks...")
        start_time = time.time()

        contents = [c.content for c in new_chunks]
        new_embeddings = self.model.encode(
            contents,
            show_progress_bar=show_progress,
            convert_to_numpy=True
        )

        elapsed = time.time() - start_time
        logger.info(f"Generated {len(new_embeddings)} embeddings in {elapsed:.2f}s")

        # Update indices
        import numpy as np
        start_idx = len(self.chunks)
        for i, chunk in enumerate(new_chunks):
            self.chunk_index[chunk.id] = start_idx + i

        # Add to store
        self.chunks.extend(new_chunks)

        if self.embeddings is None:
            self.embeddings = new_embeddings
        else:
            self.embeddings = np.vstack([self.embeddings, new_embeddings])

        return len(new_chunks)

    def search(
        self,
        query: str,
        top_k: int = 10,
        doc_type: Optional[str] = None,
        document_ids: Optional[List[str]] = None
    ) -> List[SearchResult]:
        """
        Search for similar chunks.

        Args:
            query: Search query text
            top_k: Number of results to return
            doc_type: Filter by document type ("resume" or "job")
            document_ids: Filter to specific document IDs

        Returns:
            List of SearchResult objects
        """
        if not self.chunks:
            return []

        self._load_model()

        # Encode query
        query_embedding = self.model.encode([query], convert_to_numpy=True)[0]

        # Compute similarities
        import numpy as np
        similarities = np.dot(self.embeddings, query_embedding) / (
            np.linalg.norm(self.embeddings, axis=1) * np.linalg.norm(query_embedding)
        )

        # Apply filters and build results
        results = []
        for idx, (chunk, score) in enumerate(zip(self.chunks, similarities)):
            # Filter by doc_type
            if doc_type and chunk.document_type != doc_type:
                continue
            # Filter by document_ids
            if document_ids and chunk.document_id not in document_ids:
                continue

            results.append(SearchResult(
                chunk=chunk,
                score=float(score),
                document_id=chunk.document_id
            ))

        # Sort by score and limit
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]

    def search_for_document(
        self,
        query_doc: Dict,
        doc_type: Literal["resume", "job"],
        target_type: Literal["resume", "job"],
        top_k: int = 10
    ) -> Dict[str, float]:
        """
        Search using a document as query.
        Returns document-level scores (aggregated from chunk scores).
        """
        # Chunk the query document
        if doc_type == "resume":
            query_chunks = self.chunker.chunk_resume(query_doc)
        else:
            query_chunks = self.chunker.chunk_job(query_doc)

        # Search with each chunk and aggregate
        doc_scores: Dict[str, List[float]] = {}

        for chunk in query_chunks:
            results = self.search(
                query=chunk.content,
                top_k=top_k * 3,  # Get more to aggregate
                doc_type=target_type
            )

            for result in results:
                if result.document_id not in doc_scores:
                    doc_scores[result.document_id] = []
                doc_scores[result.document_id].append(result.score)

        # Aggregate scores (max or mean)
        aggregated = {
            doc_id: max(scores)  # Use max score across chunks
            for doc_id, scores in doc_scores.items()
        }

        # Sort and limit
        sorted_docs = sorted(aggregated.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_docs[:top_k])

    def save(self):
        """Save the vector store to disk."""
        import numpy as np

        # Save chunks (without embeddings)
        chunks_path = self.store_path / "chunks.json"
        with open(chunks_path, "w") as f:
            json.dump([c.to_dict() for c in self.chunks], f, indent=2)

        # Save embeddings
        embeddings_path = self.store_path / "embeddings.npy"
        if self.embeddings is not None:
            np.save(embeddings_path, self.embeddings)

        # Save metadata
        meta_path = self.store_path / "index_meta.json"
        with open(meta_path, "w") as f:
            json.dump({
                "model_name": self.model_name,
                "num_chunks": len(self.chunks),
                "num_documents": len(self.document_ids),
                "document_ids": list(self.document_ids),
                "chunk_config": {
                    "strategy": self.chunk_config.strategy.value,
                    "max_chunk_chars": self.chunk_config.max_chunk_chars,
                    "overlap_chars": self.chunk_config.overlap_chars
                },
                "saved_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }, f, indent=2)

        logger.info(f"Saved {len(self.chunks)} chunks to {self.store_path}")

    def load(self) -> bool:
        """
        Load the vector store from disk.

        Returns True if loaded successfully.
        """
        import numpy as np

        chunks_path = self.store_path / "chunks.json"
        embeddings_path = self.store_path / "embeddings.npy"
        meta_path = self.store_path / "index_meta.json"

        if not all(p.exists() for p in [chunks_path, embeddings_path, meta_path]):
            logger.info("No existing vector store found")
            return False

        try:
            # Load metadata
            with open(meta_path) as f:
                meta = json.load(f)

            # Check model compatibility
            if meta.get("model_name") != self.model_name:
                logger.warning(
                    f"Model mismatch: stored={meta.get('model_name')}, "
                    f"current={self.model_name}. Re-indexing required."
                )
                return False

            # Load chunks
            with open(chunks_path) as f:
                chunk_dicts = json.load(f)

            self.chunks = [
                Chunk(
                    id=c["id"],
                    document_id=c["document_id"],
                    document_type=c["document_type"],
                    content=c["content"],
                    section=c["section"],
                    metadata=c.get("metadata", {})
                )
                for c in chunk_dicts
            ]

            # Load embeddings
            self.embeddings = np.load(embeddings_path)

            # Rebuild indices
            self.document_ids = set(meta.get("document_ids", []))
            self.chunk_index = {c.id: i for i, c in enumerate(self.chunks)}

            logger.info(
                f"Loaded {len(self.chunks)} chunks from {self.store_path} "
                f"({len(self.document_ids)} documents)"
            )
            return True

        except Exception as e:
            logger.error(f"Error loading vector store: {e}")
            return False

    def clear(self):
        """Clear all data from the store."""
        self.chunks = []
        self.embeddings = None
        self.document_ids = set()
        self.chunk_index = {}

        # Remove files
        for f in ["chunks.json", "embeddings.npy", "index_meta.json"]:
            path = self.store_path / f
            if path.exists():
                path.unlink()

        logger.info("Vector store cleared")

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector store."""
        stats = {
            "num_chunks": len(self.chunks),
            "num_documents": len(self.document_ids),
            "model_name": self.model_name,
            "store_path": str(self.store_path),
            "embeddings_shape": self.embeddings.shape if self.embeddings is not None else None,
            "chunk_config": {
                "strategy": self.chunk_config.strategy.value,
                "max_chunk_chars": self.chunk_config.max_chunk_chars,
                "overlap_chars": self.chunk_config.overlap_chars
            }
        }

        if self.chunks:
            chunk_sizes = [len(c.content) for c in self.chunks]
            stats["chunk_size_stats"] = {
                "min": min(chunk_sizes),
                "max": max(chunk_sizes),
                "avg": sum(chunk_sizes) // len(chunk_sizes)
            }

            # Chunks by type
            resume_chunks = [c for c in self.chunks if c.document_type == "resume"]
            job_chunks = [c for c in self.chunks if c.document_type == "job"]
            stats["chunks_by_type"] = {
                "resume": len(resume_chunks),
                "job": len(job_chunks)
            }

        return stats


# =============================================================================
# INTEGRATED MATCHER WITH VECTOR STORE
# =============================================================================

class ChunkedNeuralMatcher:
    """
    Neural matcher using proper chunking and vector storage.

    This addresses the truncation issue by:
    1. Chunking resumes into sections that fit model limits
    2. Storing vectors persistently
    3. Aggregating chunk-level scores to document-level
    """

    def __init__(
        self,
        store_path: Path = None,
        model_name: str = "all-MiniLM-L6-v2",
        chunk_config: ChunkConfig = None
    ):
        if store_path is None:
            store_path = Path(__file__).parent.parent / "vector_store"

        self.vector_store = VectorStore(
            store_path=store_path,
            model_name=model_name,
            chunk_config=chunk_config
        )
        self.resumes: Dict[str, Dict] = {}  # id -> resume

    def index_resumes(self, resumes: List[Dict], quiet: bool = False):
        """Index resumes with chunking."""
        # Store full resumes for later access
        for r in resumes:
            self.resumes[r.get("id", "unknown")] = r

        # Try to load existing index
        if self.vector_store.load():
            # Check if we have all resumes
            existing_ids = self.vector_store.document_ids
            new_resumes = [r for r in resumes if r.get("id") not in existing_ids]
            if not new_resumes:
                if not quiet:
                    logger.info("All resumes already indexed")
                return
            resumes = new_resumes

        # Add new resumes
        num_chunks = self.vector_store.add_documents(
            resumes,
            doc_type="resume",
            show_progress=not quiet
        )

        if not quiet:
            logger.info(f"Indexed {len(resumes)} resumes into {num_chunks} chunks")

        # Save to disk
        self.vector_store.save()

    def match_job(self, job: Dict, top_k: int = 10):
        """Match a job to resumes using chunked search."""
        from scripts.match_resumes import JobMatchResults, MatchResult

        start_time = time.time()

        # Get document-level scores from vector search
        vector_scores = self.vector_store.search_for_document(
            query_doc=job,
            doc_type="job",
            target_type="resume",
            top_k=top_k * 2  # Get more for filtering
        )

        # Build results with keyword matching
        matches = []
        for resume_id, vector_score in vector_scores.items():
            if resume_id not in self.resumes:
                continue

            resume = self.resumes[resume_id]

            # Compute keyword match (same as before)
            keyword_score, highlights = self._compute_keyword_match(resume, job)

            # Combined score
            combined = (0.7 * vector_score) + (0.3 * keyword_score)

            matches.append({
                "resume": resume,
                "score": combined,
                "vector_score": vector_score,
                "keyword_score": keyword_score,
                "highlights": highlights
            })

        # Sort and limit
        matches.sort(key=lambda x: x["score"], reverse=True)
        matches = matches[:top_k]

        # Build result objects
        results = []
        for item in matches:
            resume = item["resume"]
            results.append(MatchResult(
                resume_id=resume.get("id", "unknown"),
                candidate_name=resume.get("personal_info", {}).get("name", "Unknown"),
                score=round(item["score"], 4),
                breakdown={
                    "chunked_neural_similarity": round(item["vector_score"], 4),
                    "keyword_match": round(item["keyword_score"], 4)
                },
                highlights=item["highlights"]
            ))

        processing_time = (time.time() - start_time) * 1000

        return JobMatchResults(
            job_id=job.get("id", "unknown"),
            job_title=job.get("title", "Unknown"),
            employer=job.get("employer", "Unknown"),
            matches=results,
            processing_time_ms=round(processing_time, 2),
            matching_mode="Chunked Neural (sentence-transformers)"
        )

    def _compute_keyword_match(self, resume: Dict, job: Dict) -> Tuple[float, List[str]]:
        """Compute keyword matching score."""
        # Import from existing matcher
        from scripts.match_resumes import TFIDFResumeMatcher
        matcher = TFIDFResumeMatcher()
        return matcher._compute_keyword_match(resume, job)


# =============================================================================
# CLI FOR TESTING
# =============================================================================

def main():
    """Test the vector store."""
    import argparse

    parser = argparse.ArgumentParser(description="Vector Store CLI")
    parser.add_argument("--action", choices=["index", "search", "stats", "clear"],
                        default="stats", help="Action to perform")
    parser.add_argument("--query", type=str, help="Search query")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    base_dir = Path(__file__).parent.parent
    store_path = base_dir / "vector_store"

    store = VectorStore(store_path=store_path)

    if args.action == "index":
        from scripts.match_resumes import load_json_files

        resumes_dir = base_dir / "test_data" / "resumes"
        jobs_dir = base_dir / "test_data" / "job_descriptions"

        if resumes_dir.exists():
            resumes = load_json_files(resumes_dir)
            num_chunks = store.add_documents(resumes, doc_type="resume")
            print(f"Indexed {len(resumes)} resumes into {num_chunks} chunks")

        if jobs_dir.exists():
            jobs = load_json_files(jobs_dir)
            num_chunks = store.add_documents(jobs, doc_type="job")
            print(f"Indexed {len(jobs)} jobs into {num_chunks} chunks")

        store.save()

    elif args.action == "search":
        if not store.load():
            print("No index found. Run with --action index first.")
            return

        if not args.query:
            print("Please provide --query")
            return

        results = store.search(args.query, top_k=args.top_k)
        print(f"\nTop {len(results)} results for: {args.query}\n")
        for i, r in enumerate(results, 1):
            print(f"{i}. [{r.score:.3f}] {r.chunk.section} ({r.document_id})")
            print(f"   {r.chunk.content[:100]}...")
            print()

    elif args.action == "stats":
        if not store.load():
            print("No index found. Run with --action index first.")
            return

        stats = store.get_stats()
        print("\nVector Store Statistics:")
        print(json.dumps(stats, indent=2))

    elif args.action == "clear":
        store.clear()
        print("Vector store cleared")


if __name__ == "__main__":
    main()
