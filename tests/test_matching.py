"""
Tests for the resume matching system.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.match_resumes import (
    TFIDFResumeMatcher,
    MatchingMode,
    create_matcher,
    is_neural_available,
    load_json_files,
    MatchResult,
    JobMatchResults,
)


class TestTFIDFMatcher:
    """Tests for TF-IDF matching."""

    def test_index_resumes(self, sample_resumes):
        """Test that resumes can be indexed."""
        matcher = TFIDFResumeMatcher()
        matcher.index_resumes(sample_resumes, quiet=True)

        assert len(matcher.resumes) == 3
        assert len(matcher.resume_vectors) == 3
        assert len(matcher.vocab) > 0

    def test_match_returns_results(self, sample_resumes, sample_job):
        """Test that matching returns results."""
        matcher = TFIDFResumeMatcher()
        matcher.index_resumes(sample_resumes, quiet=True)

        results = matcher.match_job(sample_job, top_k=3)

        assert isinstance(results, JobMatchResults)
        assert len(results.matches) == 3
        assert results.job_id == "test_job_001"
        assert results.matching_mode == "TF-IDF + Keywords"

    def test_match_scores_correct_candidate_higher(self, sample_resumes, sample_job):
        """Test that Epic jobs rank Epic candidates higher than Cerner candidates."""
        matcher = TFIDFResumeMatcher()
        matcher.index_resumes(sample_resumes, quiet=True)

        results = matcher.match_job(sample_job, top_k=3)

        # Find scores for Epic vs Cerner candidates
        epic_scores = [m.score for m in results.matches if "Epic" in str(m.breakdown)]
        cerner_candidates = [m for m in results.matches if m.resume_id == "test_resume_002"]

        # Epic candidates should rank higher
        if cerner_candidates:
            cerner_score = cerner_candidates[0].score
            # At least one Epic candidate should score higher
            assert any(s > cerner_score for s in epic_scores), \
                "Epic candidates should score higher than Cerner for Epic job"

    def test_match_result_structure(self, sample_resumes, sample_job):
        """Test that match results have correct structure."""
        matcher = TFIDFResumeMatcher()
        matcher.index_resumes(sample_resumes, quiet=True)

        results = matcher.match_job(sample_job, top_k=1)
        match = results.matches[0]

        assert isinstance(match, MatchResult)
        assert match.resume_id is not None
        assert match.candidate_name is not None
        assert 0 <= match.score <= 1
        assert "tfidf_similarity" in match.breakdown
        assert "keyword_match" in match.breakdown
        assert isinstance(match.highlights, list)

    def test_processing_time_recorded(self, sample_resumes, sample_job):
        """Test that processing time is recorded."""
        matcher = TFIDFResumeMatcher()
        matcher.index_resumes(sample_resumes, quiet=True)

        results = matcher.match_job(sample_job, top_k=3)

        assert results.processing_time_ms > 0

    def test_top_k_limits_results(self, sample_resumes, sample_job):
        """Test that top_k limits the number of results."""
        matcher = TFIDFResumeMatcher()
        matcher.index_resumes(sample_resumes, quiet=True)

        results_1 = matcher.match_job(sample_job, top_k=1)
        results_2 = matcher.match_job(sample_job, top_k=2)

        assert len(results_1.matches) == 1
        assert len(results_2.matches) == 2

    def test_empty_resumes_raises_no_error(self, sample_job):
        """Test that empty resume list doesn't crash."""
        matcher = TFIDFResumeMatcher()
        matcher.index_resumes([], quiet=True)

        # Should return empty results, not crash
        results = matcher.match_job(sample_job, top_k=3)
        assert len(results.matches) == 0

    def test_tokenization(self):
        """Test tokenization produces expected tokens."""
        matcher = TFIDFResumeMatcher()
        tokens = matcher._tokenize("Epic Healthcare IT, EpicCare Ambulatory")

        assert "epic" in tokens
        assert "healthcare" in tokens
        assert "epiccare" in tokens
        assert "ambulatory" in tokens

    def test_tfidf_vectors_not_empty(self, sample_resumes):
        """Test that TF-IDF vectors are computed."""
        matcher = TFIDFResumeMatcher()
        matcher.index_resumes(sample_resumes, quiet=True)

        for vec in matcher.resume_vectors:
            assert len(vec) > 0, "Resume vector should not be empty"


class TestMatcherFactory:
    """Tests for matcher factory function."""

    def test_create_tfidf_matcher(self):
        """Test creating TF-IDF matcher."""
        matcher = create_matcher(MatchingMode.TFIDF)
        assert isinstance(matcher, TFIDFResumeMatcher)

    def test_is_neural_available_returns_bool(self):
        """Test neural availability check."""
        result = is_neural_available()
        assert isinstance(result, bool)


class TestKeywordMatching:
    """Tests for keyword matching logic."""

    def test_ehr_system_match(self, sample_resume, sample_job):
        """Test EHR system matching."""
        matcher = TFIDFResumeMatcher()
        score, highlights = matcher._compute_keyword_match(sample_resume, sample_job)

        assert score > 0
        assert any("EHR" in h or "Epic" in h for h in highlights)

    def test_module_match(self, sample_resume, sample_job):
        """Test module matching."""
        matcher = TFIDFResumeMatcher()
        score, highlights = matcher._compute_keyword_match(sample_resume, sample_job)

        assert any("Module" in h for h in highlights)

    def test_experience_match(self, sample_resume, sample_job):
        """Test experience years matching."""
        matcher = TFIDFResumeMatcher()
        score, highlights = matcher._compute_keyword_match(sample_resume, sample_job)

        assert any("Experience" in h or "years" in h for h in highlights)

    def test_certification_match(self, sample_resume, sample_job):
        """Test certification matching."""
        matcher = TFIDFResumeMatcher()
        score, highlights = matcher._compute_keyword_match(sample_resume, sample_job)

        assert any("certification" in h.lower() for h in highlights)


class TestDataLoading:
    """Tests for data loading functions."""

    def test_load_json_files(self, populated_test_data):
        """Test loading JSON files from directory."""
        resumes_dir = populated_test_data / "resumes"
        resumes = load_json_files(resumes_dir)

        assert len(resumes) == 3
        assert all("id" in r for r in resumes)

    def test_load_empty_directory(self, test_data_dir):
        """Test loading from empty directory."""
        empty_dir = test_data_dir / "empty"
        empty_dir.mkdir()

        result = load_json_files(empty_dir)
        assert result == []


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_resume_missing_fields(self, sample_job):
        """Test matching with minimal resume data."""
        minimal_resume = {
            "id": "minimal",
            "personal_info": {"name": "Test User"}
        }

        matcher = TFIDFResumeMatcher()
        matcher.index_resumes([minimal_resume], quiet=True)

        # Should not crash
        results = matcher.match_job(sample_job, top_k=1)
        assert len(results.matches) == 1

    def test_job_missing_fields(self, sample_resumes):
        """Test matching with minimal job data."""
        minimal_job = {
            "id": "minimal_job",
            "title": "Some Job"
        }

        matcher = TFIDFResumeMatcher()
        matcher.index_resumes(sample_resumes, quiet=True)

        # Should not crash
        results = matcher.match_job(minimal_job, top_k=3)
        assert len(results.matches) == 3

    def test_special_characters_in_text(self, sample_job):
        """Test handling of special characters."""
        resume_with_special = {
            "id": "special",
            "personal_info": {"name": "Test O'Brien"},
            "summary": "Experience with C++ and .NET development",
            "skills": ["C++", ".NET", "SQL Server"]
        }

        matcher = TFIDFResumeMatcher()
        matcher.index_resumes([resume_with_special], quiet=True)

        # Should not crash
        results = matcher.match_job(sample_job, top_k=1)
        assert len(results.matches) == 1

    def test_unicode_handling(self, sample_job):
        """Test handling of unicode characters."""
        unicode_resume = {
            "id": "unicode",
            "personal_info": {"name": "José García"},
            "summary": "Experiência em implementação de sistemas"
        }

        matcher = TFIDFResumeMatcher()
        matcher.index_resumes([unicode_resume], quiet=True)

        # Should not crash
        results = matcher.match_job(sample_job, top_k=1)
        assert len(results.matches) == 1


class TestNeuralMatcher:
    """Tests for neural matcher (if available)."""

    @pytest.mark.skipif(not is_neural_available(), reason="sentence-transformers not installed")
    def test_create_neural_matcher(self):
        """Test creating neural matcher."""
        from scripts.match_resumes import NeuralResumeMatcher
        matcher = create_matcher(MatchingMode.NEURAL)
        assert isinstance(matcher, NeuralResumeMatcher)

    @pytest.mark.skipif(not is_neural_available(), reason="sentence-transformers not installed")
    def test_neural_index_resumes(self, sample_resumes):
        """Test neural indexing."""
        from scripts.match_resumes import NeuralResumeMatcher
        matcher = NeuralResumeMatcher()
        matcher.index_resumes(sample_resumes, quiet=True)

        assert matcher.resume_embeddings is not None
        assert len(matcher.resume_embeddings) == 3

    @pytest.mark.skipif(not is_neural_available(), reason="sentence-transformers not installed")
    def test_neural_match_returns_results(self, sample_resumes, sample_job):
        """Test neural matching."""
        from scripts.match_resumes import NeuralResumeMatcher
        matcher = NeuralResumeMatcher()
        matcher.index_resumes(sample_resumes, quiet=True)

        results = matcher.match_job(sample_job, top_k=3)

        assert isinstance(results, JobMatchResults)
        assert len(results.matches) == 3
        assert "Neural" in results.matching_mode
