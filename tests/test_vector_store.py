"""
Tests for the vector store and chunking system.
"""

import pytest
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.vector_store import (
    DocumentChunker,
    ChunkConfig,
    ChunkStrategy,
    Chunk,
)

# Conditionally import VectorStore tests
try:
    from sentence_transformers import SentenceTransformer
    NEURAL_AVAILABLE = True
except ImportError:
    NEURAL_AVAILABLE = False


class TestDocumentChunker:
    """Tests for document chunking."""

    def test_chunker_creates_chunks(self, sample_resume):
        """Test that chunker creates multiple chunks from a resume."""
        chunker = DocumentChunker()
        chunks = chunker.chunk_resume(sample_resume)

        assert len(chunks) > 0
        assert all(isinstance(c, Chunk) for c in chunks)

    def test_chunker_creates_expected_sections(self, sample_resume):
        """Test that chunker creates expected sections."""
        chunker = DocumentChunker()
        chunks = chunker.chunk_resume(sample_resume)

        sections = {c.section for c in chunks}

        # Should have these sections
        assert "summary" in sections or any("summary" in s for s in sections)
        assert any("experience" in s for s in sections)
        assert "skills" in sections

    def test_chunk_content_not_empty(self, sample_resume):
        """Test that chunks have content."""
        chunker = DocumentChunker()
        chunks = chunker.chunk_resume(sample_resume)

        for chunk in chunks:
            assert len(chunk.content) > 0, f"Chunk {chunk.id} has empty content"

    def test_chunk_ids_unique(self, sample_resume):
        """Test that chunk IDs are unique."""
        chunker = DocumentChunker()
        chunks = chunker.chunk_resume(sample_resume)

        ids = [c.id for c in chunks]
        assert len(ids) == len(set(ids)), "Chunk IDs should be unique"

    def test_chunk_metadata_preserved(self, sample_resume):
        """Test that metadata is preserved in chunks."""
        chunker = DocumentChunker()
        chunks = chunker.chunk_resume(sample_resume)

        for chunk in chunks:
            assert chunk.document_id == sample_resume["id"]
            assert chunk.document_type == "resume"
            assert "name" in chunk.metadata

    def test_job_chunking(self, sample_job):
        """Test chunking of job descriptions."""
        chunker = DocumentChunker()
        chunks = chunker.chunk_job(sample_job)

        assert len(chunks) > 0
        sections = {c.section for c in chunks}
        assert "description" in sections

    def test_chunk_size_limits(self):
        """Test that chunks respect size limits."""
        config = ChunkConfig(max_chunk_chars=200)
        chunker = DocumentChunker(config)

        # Create a resume with very long content
        long_resume = {
            "id": "long_resume",
            "personal_info": {"name": "Test"},
            "summary": "A" * 500,  # Very long summary
            "skills": ["skill1", "skill2"]
        }

        chunks = chunker.chunk_resume(long_resume)

        # Long content should be split
        for chunk in chunks:
            assert len(chunk.content) <= config.max_chunk_chars + 50, \
                f"Chunk {chunk.id} exceeds max size"

    def test_chunk_to_dict(self, sample_resume):
        """Test chunk serialization."""
        chunker = DocumentChunker()
        chunks = chunker.chunk_resume(sample_resume)

        for chunk in chunks:
            d = chunk.to_dict()
            assert "id" in d
            assert "content" in d
            assert "section" in d
            assert "document_id" in d


class TestChunkConfig:
    """Tests for chunk configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ChunkConfig()

        assert config.strategy == ChunkStrategy.SEMANTIC
        assert config.max_chunk_chars == 800
        assert config.overlap_chars == 200

    def test_custom_config(self):
        """Test custom configuration."""
        config = ChunkConfig(
            strategy=ChunkStrategy.FIXED,
            max_chunk_chars=500,
            overlap_chars=100
        )

        assert config.strategy == ChunkStrategy.FIXED
        assert config.max_chunk_chars == 500


class TestChunkingEdgeCases:
    """Tests for edge cases in chunking."""

    def test_empty_resume(self):
        """Test chunking empty resume."""
        chunker = DocumentChunker()
        empty_resume = {"id": "empty"}

        chunks = chunker.chunk_resume(empty_resume)
        # Should handle gracefully, might return empty or minimal chunks
        assert isinstance(chunks, list)

    def test_minimal_resume(self):
        """Test chunking minimal resume."""
        chunker = DocumentChunker()
        minimal = {
            "id": "minimal",
            "personal_info": {"name": "Test"},
            "summary": "Short summary"
        }

        chunks = chunker.chunk_resume(minimal)
        assert len(chunks) >= 1

    def test_resume_with_many_experiences(self):
        """Test resume with many experience entries."""
        chunker = DocumentChunker()
        resume = {
            "id": "many_exp",
            "personal_info": {"name": "Test"},
            "experience": [
                {"title": f"Job {i}", "employer": f"Company {i}"}
                for i in range(10)
            ]
        }

        chunks = chunker.chunk_resume(resume)
        exp_chunks = [c for c in chunks if "experience" in c.section]
        assert len(exp_chunks) == 10

    def test_unicode_in_resume(self):
        """Test handling of unicode characters."""
        chunker = DocumentChunker()
        unicode_resume = {
            "id": "unicode",
            "personal_info": {"name": "José García"},
            "summary": "Experiência em implementação de sistemas de saúde",
            "skills": ["développement", "システム"]
        }

        chunks = chunker.chunk_resume(unicode_resume)
        assert len(chunks) > 0
        # Content should be preserved
        assert any("José" in c.content for c in chunks)


@pytest.mark.skipif(not NEURAL_AVAILABLE, reason="sentence-transformers not installed")
class TestVectorStore:
    """Tests for vector store (requires sentence-transformers)."""

    def test_vector_store_creation(self, tmp_path):
        """Test creating a vector store."""
        from scripts.vector_store import VectorStore

        store = VectorStore(store_path=tmp_path / "test_store")
        assert store.store_path.exists()

    def test_add_documents(self, tmp_path, sample_resumes):
        """Test adding documents to vector store."""
        from scripts.vector_store import VectorStore

        store = VectorStore(store_path=tmp_path / "test_store")
        num_chunks = store.add_documents(sample_resumes, doc_type="resume")

        assert num_chunks > 0
        assert len(store.chunks) == num_chunks
        assert store.embeddings is not None

    def test_search(self, tmp_path, sample_resumes):
        """Test searching the vector store."""
        from scripts.vector_store import VectorStore

        store = VectorStore(store_path=tmp_path / "test_store")
        store.add_documents(sample_resumes, doc_type="resume")

        results = store.search("Epic implementation consultant", top_k=3)

        assert len(results) > 0
        assert all(r.score > 0 for r in results)

    def test_save_and_load(self, tmp_path, sample_resumes):
        """Test saving and loading vector store."""
        from scripts.vector_store import VectorStore
        import numpy as np

        store_path = tmp_path / "test_store"

        # Create and save
        store1 = VectorStore(store_path=store_path)
        store1.add_documents(sample_resumes, doc_type="resume")
        original_chunks = len(store1.chunks)
        original_embeddings = store1.embeddings.copy()
        store1.save()

        # Load in new instance
        store2 = VectorStore(store_path=store_path)
        loaded = store2.load()

        assert loaded is True
        assert len(store2.chunks) == original_chunks
        assert np.allclose(store2.embeddings, original_embeddings)

    def test_search_with_filter(self, tmp_path, sample_resumes, sample_job):
        """Test filtering search results."""
        from scripts.vector_store import VectorStore

        store = VectorStore(store_path=tmp_path / "test_store")
        store.add_documents(sample_resumes, doc_type="resume")
        store.add_documents([sample_job], doc_type="job")

        # Search only resumes
        results = store.search("Epic", top_k=10, doc_type="resume")
        assert all(r.chunk.document_type == "resume" for r in results)

        # Search only jobs
        results = store.search("Epic", top_k=10, doc_type="job")
        assert all(r.chunk.document_type == "job" for r in results)

    def test_get_stats(self, tmp_path, sample_resumes):
        """Test getting vector store statistics."""
        from scripts.vector_store import VectorStore

        store = VectorStore(store_path=tmp_path / "test_store")
        store.add_documents(sample_resumes, doc_type="resume")

        stats = store.get_stats()

        assert "num_chunks" in stats
        assert "num_documents" in stats
        assert stats["num_documents"] == len(sample_resumes)

    def test_clear(self, tmp_path, sample_resumes):
        """Test clearing vector store."""
        from scripts.vector_store import VectorStore

        store = VectorStore(store_path=tmp_path / "test_store")
        store.add_documents(sample_resumes, doc_type="resume")
        store.save()

        store.clear()

        assert len(store.chunks) == 0
        assert store.embeddings is None


@pytest.mark.skipif(not NEURAL_AVAILABLE, reason="sentence-transformers not installed")
class TestChunkedNeuralMatcher:
    """Tests for the chunked neural matcher."""

    def test_index_and_match(self, tmp_path, sample_resumes, sample_job):
        """Test full indexing and matching flow."""
        from scripts.vector_store import ChunkedNeuralMatcher

        matcher = ChunkedNeuralMatcher(store_path=tmp_path / "test_store")
        matcher.index_resumes(sample_resumes, quiet=True)

        results = matcher.match_job(sample_job, top_k=3)

        assert len(results.matches) == 3
        assert "Chunked Neural" in results.matching_mode

    def test_scores_in_valid_range(self, tmp_path, sample_resumes, sample_job):
        """Test that scores are in valid range."""
        from scripts.vector_store import ChunkedNeuralMatcher

        matcher = ChunkedNeuralMatcher(store_path=tmp_path / "test_store")
        matcher.index_resumes(sample_resumes, quiet=True)

        results = matcher.match_job(sample_job, top_k=3)

        for match in results.matches:
            assert 0 <= match.score <= 1, f"Score {match.score} out of range"
