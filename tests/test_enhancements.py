"""
Tests for matching enhancements.
"""

import pytest
import sys
from pathlib import Path
from datetime import date, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.matching_enhancements import (
    MatchingCriteria,
    HEALTHCARE_CRITERIA,
    TECHNOLOGY_CRITERIA,
    GENERAL_CRITERIA,
    parse_location,
    haversine_distance,
    compute_location_score,
    parse_date,
    compute_recency_score,
    MockATSConnector,
    RankingVerifier,
    create_domain_config,
)


class TestMatchingCriteria:
    """Tests for MatchingCriteria configuration."""

    def test_default_criteria_validates(self):
        """Test that default criteria weights sum to 1.0."""
        criteria = MatchingCriteria()
        assert criteria.validate() is True

    def test_healthcare_criteria(self):
        """Test healthcare preset."""
        criteria = HEALTHCARE_CRITERIA
        assert criteria.domain == "healthcare"
        assert criteria.primary_system_field == "primary_ehr_system"

    def test_technology_criteria(self):
        """Test technology preset."""
        criteria = TECHNOLOGY_CRITERIA
        assert criteria.domain == "technology"
        assert criteria.skills_weight > HEALTHCARE_CRITERIA.skills_weight

    def test_criteria_to_dict(self):
        """Test serialization."""
        criteria = MatchingCriteria()
        d = criteria.to_dict()

        assert "weights" in d
        assert "features" in d
        assert "settings" in d
        assert d["settings"]["domain"] == "healthcare"

    def test_invalid_weights_warning(self):
        """Test that invalid weights are detected."""
        criteria = MatchingCriteria(
            primary_system_weight=0.5,
            module_experience_weight=0.5,
            # Other weights default, total will exceed 1.0
        )
        assert criteria.validate() is False


class TestLocationMatching:
    """Tests for location-based matching."""

    def test_parse_location_city_state(self):
        """Test parsing city, state format."""
        coords = parse_location("Boston, MA")
        assert coords is not None
        assert abs(coords[0] - 42.36) < 0.1  # Latitude
        assert abs(coords[1] - (-71.06)) < 0.1  # Longitude

    def test_parse_location_city_only(self):
        """Test parsing city only."""
        coords = parse_location("Chicago")
        assert coords is not None

    def test_parse_location_remote(self):
        """Test that remote returns None."""
        assert parse_location("Remote") is None
        assert parse_location("Anywhere") is None
        assert parse_location("Virtual") is None

    def test_parse_location_unknown(self):
        """Test unknown location."""
        coords = parse_location("Small Town, XX")
        # Should return None for unknown locations
        assert coords is None

    def test_haversine_same_location(self):
        """Test distance to same location is zero."""
        boston = (42.3601, -71.0589)
        distance = haversine_distance(boston, boston)
        assert distance < 1  # Should be ~0

    def test_haversine_known_distance(self):
        """Test known distance between cities."""
        boston = (42.3601, -71.0589)
        new_york = (40.7128, -74.0060)
        distance = haversine_distance(boston, new_york)
        # Boston to NYC is ~190 miles
        assert 180 < distance < 220

    def test_compute_location_score_local(self):
        """Test local candidate score."""
        score, highlight = compute_location_score("Boston, MA", "Boston, MA")
        assert score == 1.0
        assert "Local" in highlight or highlight is None

    def test_compute_location_score_remote_job(self):
        """Test remote job gives full score."""
        score, highlight = compute_location_score(
            "San Francisco, CA", "Boston, MA", is_remote=True
        )
        assert score == 1.0
        assert "Remote" in highlight

    def test_compute_location_score_distant(self):
        """Test distant candidate gets lower score."""
        score, _ = compute_location_score("Los Angeles, CA", "Boston, MA")
        assert score < 0.5  # Should be penalized for distance


class TestRecencyWeighting:
    """Tests for recency-weighted experience scoring."""

    def test_parse_date_standard(self):
        """Test standard date parsing."""
        d = parse_date("2023-06-15")
        assert d == date(2023, 6, 15)

    def test_parse_date_year_month(self):
        """Test year-month format."""
        d = parse_date("2023-06")
        assert d.year == 2023
        assert d.month == 6

    def test_parse_date_present(self):
        """Test 'Present' returns today."""
        d = parse_date("Present")
        assert d == date.today()

    def test_parse_date_year_only(self):
        """Test year extraction."""
        d = parse_date("Started in 2020")
        assert d.year == 2020

    def test_recency_recent_experience(self):
        """Test recent experience gets high score."""
        recent_exp = [{
            "title": "Current Role",
            "employer": "Company",
            "start_date": "2023-01",
            "end_date": "Present"
        }]
        score, highlights = compute_recency_score(recent_exp)
        assert score > 0.7  # Recent should score high

    def test_recency_old_experience(self):
        """Test old experience gets lower score."""
        old_exp = [{
            "title": "Old Role",
            "employer": "Company",
            "start_date": "2010-01",
            "end_date": "2012-12"
        }]
        score, highlights = compute_recency_score(old_exp)
        assert score < 0.5  # Old should score lower

    def test_recency_empty_experience(self):
        """Test empty experience."""
        score, highlights = compute_recency_score([])
        assert score == 0.0

    def test_recency_multiple_experiences(self):
        """Test multiple experiences are weighted."""
        mixed_exp = [
            {"start_date": "2023-01", "end_date": "Present", "employer": "Current"},
            {"start_date": "2020-01", "end_date": "2022-12", "employer": "Previous"},
            {"start_date": "2015-01", "end_date": "2019-12", "employer": "Old"},
        ]
        score, highlights = compute_recency_score(mixed_exp)
        # Should be moderate - has mix of recent and old
        assert 0.3 < score < 0.9


class TestATSConnector:
    """Tests for ATS connector interface."""

    def test_mock_ats_connect(self):
        """Test mock ATS connection."""
        ats = MockATSConnector(Path("test_data"))
        assert ats.connect({}) is True
        assert ats.connected is True

    def test_mock_ats_fetch_resumes(self, tmp_path):
        """Test mock ATS resume fetch."""
        # Create test data
        resumes_dir = tmp_path / "resumes"
        resumes_dir.mkdir()
        (resumes_dir / "resume_001.json").write_text('{"id": "test1", "name": "Test"}')

        ats = MockATSConnector(tmp_path)
        ats.connect({})
        resumes = ats.fetch_resumes(limit=10)

        assert len(resumes) == 1
        assert resumes[0]["id"] == "test1"

    def test_mock_ats_push_rankings(self):
        """Test mock ATS ranking push."""
        ats = MockATSConnector(Path("test_data"))
        ats.connect({})

        rankings = [{"resume_id": "r1", "score": 0.9}]
        assert ats.push_rankings("job1", rankings) is True


class TestRankingVerifier:
    """Tests for ranking verification system."""

    @pytest.fixture
    def verifier(self):
        return RankingVerifier(MatchingCriteria())

    @pytest.fixture
    def valid_ranking(self):
        return [
            {"resume_id": "r1", "candidate_name": "Alice", "score": 0.9,
             "breakdown": {"tfidf_similarity": 0.7, "keyword_match": 0.2}, "highlights": []},
            {"resume_id": "r2", "candidate_name": "Bob", "score": 0.8,
             "breakdown": {"tfidf_similarity": 0.6, "keyword_match": 0.2}, "highlights": []},
            {"resume_id": "r3", "candidate_name": "Charlie", "score": 0.7,
             "breakdown": {"tfidf_similarity": 0.5, "keyword_match": 0.2}, "highlights": []},
        ]

    def test_valid_ranking_passes(self, verifier, valid_ranking):
        """Test that valid ranking passes verification."""
        job = {"id": "job1", "title": "Test Job"}
        result = verifier.verify_ranking(job, valid_ranking, [])

        assert result.is_valid is True
        assert result.ranking_consistency == 1.0
        assert len(result.issues) == 0

    def test_invalid_score_detected(self, verifier):
        """Test that invalid scores are detected."""
        invalid_ranking = [
            {"resume_id": "r1", "score": 1.5, "breakdown": {}, "highlights": []},  # Invalid
        ]
        job = {"id": "job1", "title": "Test Job"}
        result = verifier.verify_ranking(job, invalid_ranking, [])

        assert result.is_valid is False
        assert any("Invalid scores" in issue for issue in result.issues)

    def test_unsorted_ranking_detected(self, verifier):
        """Test that unsorted rankings are detected."""
        unsorted_ranking = [
            {"resume_id": "r1", "score": 0.5, "breakdown": {"tfidf_similarity": 0.5}, "highlights": []},
            {"resume_id": "r2", "score": 0.9, "breakdown": {"tfidf_similarity": 0.9}, "highlights": []},  # Out of order
        ]
        job = {"id": "job1", "title": "Test Job"}
        result = verifier.verify_ranking(job, unsorted_ranking, [])

        assert result.is_valid is False
        assert result.ranking_consistency < 1.0

    def test_audit_report_generated(self, verifier, valid_ranking):
        """Test audit report generation."""
        job = {"id": "job1", "title": "Test Job", "employer": "Test Corp"}
        result = verifier.verify_ranking(job, valid_ranking, [])
        report = verifier.generate_audit_report(job, valid_ranking, result)

        assert "AUDIT REPORT" in report
        assert "Test Job" in report
        assert "Alice" in report  # Top candidate


class TestDomainGeneralization:
    """Tests for domain generalization."""

    def test_create_healthcare_config(self):
        """Test healthcare config creation."""
        config = create_domain_config("healthcare")
        assert config.domain == "healthcare"
        assert config.primary_system_field == "primary_ehr_system"

    def test_create_technology_config(self):
        """Test technology config creation."""
        config = create_domain_config("technology")
        assert config.domain == "technology"
        assert config.primary_system_field == "primary_tech_stack"

    def test_create_finance_config(self):
        """Test finance config creation."""
        config = create_domain_config("finance")
        assert config.domain == "finance"
        assert config.certifications_weight == 0.20

    def test_unknown_domain_fallback(self):
        """Test unknown domain falls back to general."""
        config = create_domain_config("unknown_domain")
        assert config.domain == "general"

    def test_all_configs_validate(self):
        """Test all domain configs have valid weights."""
        for domain in ["healthcare", "technology", "finance", "general"]:
            config = create_domain_config(domain)
            assert config.validate() is True
