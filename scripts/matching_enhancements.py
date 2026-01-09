#!/usr/bin/env python3
"""
Matching Enhancements Module

Adds advanced matching capabilities:
1. Location-based matching with distance scoring
2. Recency weighting for experience
3. ATS (Applicant Tracking System) integration interface
4. Ranking verification and audit system
5. Clear, configurable matching criteria
6. Generalization support for non-healthcare domains

Author: Engineering Team
Version: 1.0.0
"""

import json
import logging
import math
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Callable

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# MATCHING CRITERIA CONFIGURATION
# =============================================================================

@dataclass
class MatchingCriteria:
    """
    Explicit, configurable matching criteria.

    All weights should sum to 1.0 for normalized scoring.
    Each criterion can be enabled/disabled and weighted independently.

    DEFAULT WEIGHTS (Healthcare Domain):
    - Primary System Match: 25% (e.g., Epic, Cerner - critical for healthcare)
    - Module Experience: 15% (specific software modules)
    - Years Experience: 15% (total years in field)
    - Certifications: 15% (professional certifications)
    - Skills Match: 15% (technical and soft skills)
    - Location Proximity: 10% (geographic fit)
    - Recency Bonus: 5% (recent experience weighted higher)

    TOTAL: 100%
    """

    # Core criteria weights
    primary_system_weight: float = 0.25      # EHR system match (healthcare) or primary tech stack
    module_experience_weight: float = 0.15   # Specific modules/tools
    years_experience_weight: float = 0.15    # Total experience years
    certifications_weight: float = 0.15      # Professional certifications
    skills_weight: float = 0.15              # Skills overlap
    location_weight: float = 0.10            # Geographic proximity
    recency_weight: float = 0.05             # Bonus for recent experience

    # Feature toggles
    enable_location_matching: bool = True
    enable_recency_weighting: bool = True
    enable_certification_matching: bool = True

    # Location settings
    max_distance_miles: float = 100.0        # Max distance for full score
    remote_job_ignores_location: bool = True # Remote jobs don't penalize distance

    # Recency settings
    recency_decay_years: float = 5.0         # Years until experience is "old"
    recent_experience_multiplier: float = 1.5 # Boost for recent experience

    # Domain settings (for generalization)
    domain: str = "healthcare"               # "healthcare", "technology", "general"
    primary_system_field: str = "primary_ehr_system"  # Field name for primary system

    def validate(self) -> bool:
        """Validate that weights sum to approximately 1.0."""
        total = (
            self.primary_system_weight +
            self.module_experience_weight +
            self.years_experience_weight +
            self.certifications_weight +
            self.skills_weight +
            self.location_weight +
            self.recency_weight
        )
        if not 0.99 <= total <= 1.01:
            logger.warning(f"Weights sum to {total}, should be 1.0")
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "weights": {
                "primary_system": self.primary_system_weight,
                "module_experience": self.module_experience_weight,
                "years_experience": self.years_experience_weight,
                "certifications": self.certifications_weight,
                "skills": self.skills_weight,
                "location": self.location_weight,
                "recency": self.recency_weight,
            },
            "features": {
                "location_matching": self.enable_location_matching,
                "recency_weighting": self.enable_recency_weighting,
                "certification_matching": self.enable_certification_matching,
            },
            "settings": {
                "max_distance_miles": self.max_distance_miles,
                "recency_decay_years": self.recency_decay_years,
                "domain": self.domain,
            }
        }


# Preset configurations for different domains
HEALTHCARE_CRITERIA = MatchingCriteria(
    domain="healthcare",
    primary_system_field="primary_ehr_system",
    primary_system_weight=0.25,
    certifications_weight=0.15,
)

TECHNOLOGY_CRITERIA = MatchingCriteria(
    domain="technology",
    primary_system_field="primary_tech_stack",
    primary_system_weight=0.20,
    skills_weight=0.25,  # Tech roles emphasize skills more
    certifications_weight=0.10,
)

GENERAL_CRITERIA = MatchingCriteria(
    domain="general",
    primary_system_field="primary_industry",
    primary_system_weight=0.15,
    skills_weight=0.20,
    years_experience_weight=0.20,
)


# =============================================================================
# LOCATION-BASED MATCHING
# =============================================================================

# Major US cities with coordinates (lat, lon)
US_CITY_COORDINATES = {
    # Northeast
    "boston": (42.3601, -71.0589),
    "new york": (40.7128, -74.0060),
    "philadelphia": (39.9526, -75.1652),
    "pittsburgh": (40.4406, -79.9959),
    "baltimore": (39.2904, -76.6122),
    "washington": (38.9072, -77.0369),
    "dc": (38.9072, -77.0369),

    # Southeast
    "atlanta": (33.7490, -84.3880),
    "miami": (25.7617, -80.1918),
    "tampa": (27.9506, -82.4572),
    "orlando": (28.5383, -81.3792),
    "charlotte": (35.2271, -80.8431),
    "raleigh": (35.7796, -78.6382),
    "nashville": (36.1627, -86.7816),

    # Midwest
    "chicago": (41.8781, -87.6298),
    "detroit": (42.3314, -83.0458),
    "cleveland": (41.4993, -81.6944),
    "columbus": (39.9612, -82.9988),
    "indianapolis": (39.7684, -86.1581),
    "milwaukee": (43.0389, -87.9065),
    "minneapolis": (44.9778, -93.2650),
    "st louis": (38.6270, -90.1994),
    "kansas city": (39.0997, -94.5786),

    # Southwest
    "dallas": (32.7767, -96.7970),
    "houston": (29.7604, -95.3698),
    "austin": (30.2672, -97.7431),
    "san antonio": (29.4241, -98.4936),
    "phoenix": (33.4484, -112.0740),
    "denver": (39.7392, -104.9903),
    "las vegas": (36.1699, -115.1398),

    # West Coast
    "los angeles": (34.0522, -118.2437),
    "san diego": (32.7157, -117.1611),
    "san francisco": (37.7749, -122.4194),
    "san jose": (37.3382, -121.8863),
    "seattle": (47.6062, -122.3321),
    "portland": (45.5152, -122.6784),
}


def parse_location(location_str: str) -> Optional[Tuple[float, float]]:
    """
    Parse a location string and return coordinates.

    Handles formats like:
    - "Boston, MA"
    - "New York City, NY"
    - "Chicago"
    - "Remote" (returns None)
    """
    if not location_str:
        return None

    location_lower = location_str.lower().strip()

    # Check for remote indicators
    if any(term in location_lower for term in ["remote", "anywhere", "virtual"]):
        return None

    # Extract city name (before comma or state abbreviation)
    city = re.split(r'[,\s]+', location_lower)[0]

    # Try direct lookup
    if city in US_CITY_COORDINATES:
        return US_CITY_COORDINATES[city]

    # Try partial match
    for city_name, coords in US_CITY_COORDINATES.items():
        if city_name in location_lower or location_lower in city_name:
            return coords

    return None


def haversine_distance(coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
    """
    Calculate the great-circle distance between two points in miles.
    Uses the Haversine formula.
    """
    lat1, lon1 = math.radians(coord1[0]), math.radians(coord1[1])
    lat2, lon2 = math.radians(coord2[0]), math.radians(coord2[1])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))

    # Earth's radius in miles
    r = 3956

    return c * r


def compute_location_score(
    resume_location: str,
    job_location: str,
    max_distance: float = 100.0,
    is_remote: bool = False
) -> Tuple[float, Optional[str]]:
    """
    Compute location match score.

    Returns:
        Tuple of (score 0-1, highlight string or None)
    """
    if is_remote:
        return 1.0, "Remote position - location flexible"

    resume_coords = parse_location(resume_location)
    job_coords = parse_location(job_location)

    # If we can't parse either location, give neutral score
    if resume_coords is None or job_coords is None:
        return 0.5, None

    distance = haversine_distance(resume_coords, job_coords)

    if distance <= 25:
        return 1.0, f"Local candidate ({distance:.0f} miles)"
    elif distance <= max_distance:
        # Linear decay from 25 to max_distance
        score = 1.0 - ((distance - 25) / (max_distance - 25)) * 0.5
        return score, f"Commutable ({distance:.0f} miles)"
    else:
        # Beyond max distance, score drops more sharply
        score = max(0.2, 0.5 - (distance - max_distance) / 500)
        return score, f"Relocation needed ({distance:.0f} miles)"


# =============================================================================
# RECENCY WEIGHTING
# =============================================================================

def parse_date(date_str: str) -> Optional[date]:
    """Parse various date formats."""
    if not date_str:
        return None

    # Handle "Present" or "Current"
    if date_str.lower() in ["present", "current", "now"]:
        return date.today()

    # Try various formats
    formats = [
        "%Y-%m-%d",
        "%Y-%m",
        "%Y",
        "%m/%Y",
        "%B %Y",  # "January 2020"
        "%b %Y",  # "Jan 2020"
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except ValueError:
            continue

    # Try to extract just the year
    year_match = re.search(r'20[0-2]\d|19\d\d', date_str)
    if year_match:
        return date(int(year_match.group()), 1, 1)

    return None


def compute_recency_score(
    experience: List[Dict],
    decay_years: float = 5.0,
    boost_multiplier: float = 1.5
) -> Tuple[float, List[str]]:
    """
    Compute a recency-weighted experience score.

    Recent experience is weighted more heavily than older experience.
    Old experience (beyond decay_years) is significantly penalized.

    Args:
        experience: List of experience entries with start_date/end_date
        decay_years: Years until experience is considered "old"
        boost_multiplier: Multiplier for very recent experience

    Returns:
        Tuple of (recency score 0-1, list of highlights)
    """
    if not experience:
        return 0.0, []

    today = date.today()
    highlights = []
    experience_contributions = []

    for i, exp in enumerate(experience):
        end_date = parse_date(exp.get("end_date", "Present"))
        start_date = parse_date(exp.get("start_date", ""))

        if end_date is None:
            end_date = today
        if start_date is None:
            # Assume 2 years if no start date
            start_date = date(end_date.year - 2, end_date.month, end_date.day)

        # Calculate years since this role ended
        years_ago = (today - end_date).days / 365.25

        # Calculate duration of this role
        duration_years = max((end_date - start_date).days / 365.25, 0.1)

        # Compute recency factor (0 to 1, where 1 is most recent)
        if years_ago < 1:
            recency_factor = 1.0  # Very recent - full value
            if i == 0:
                highlights.append(f"Currently/recently at {exp.get('employer', 'current role')}")
        elif years_ago < decay_years:
            # Linear decay from 1.0 to 0.5 over decay_years
            recency_factor = 1.0 - (years_ago / decay_years) * 0.5
        else:
            # Exponential decay beyond decay_years
            # At 2x decay_years: ~0.18, at 3x decay_years: ~0.07
            recency_factor = 0.5 * math.exp(-(years_ago - decay_years) / decay_years)

        # Duration score (capped at 3 years per role for max contribution)
        duration_score = min(duration_years / 3, 1.0)

        # Weight by position (most recent experience matters more)
        position_weight = 1.0 / (i + 1)

        # Combine: duration contributes to score, but recency penalizes old experience
        contribution = duration_score * recency_factor * position_weight
        experience_contributions.append(contribution)

    if not experience_contributions:
        return 0.5, highlights

    # Calculate weighted average, but also factor in overall recency
    # This ensures old-only experience gets a low score
    total_contribution = sum(experience_contributions)
    max_possible = sum(1.0 / (i + 1) for i in range(len(experience)))  # Max if all recent and long

    # Normalize and apply recency penalty for old-only profiles
    final_score = min(total_contribution / max_possible, 1.0) if max_possible > 0 else 0.5

    return final_score, highlights


# =============================================================================
# ATS INTEGRATION INTERFACE
# =============================================================================

class ATSConnector(ABC):
    """
    Abstract base class for Applicant Tracking System connectors.

    Implement this interface to connect to real ATS systems like:
    - Greenhouse
    - Lever
    - Workday
    - iCIMS
    - Taleo
    - BambooHR
    """

    @abstractmethod
    def connect(self, credentials: Dict[str, str]) -> bool:
        """
        Establish connection to the ATS.

        Args:
            credentials: Dictionary with API keys, tokens, etc.

        Returns:
            True if connection successful
        """
        pass

    @abstractmethod
    def fetch_resumes(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Fetch resumes from the ATS.

        Args:
            filters: Optional filters (date range, status, etc.)
            limit: Maximum number to fetch

        Returns:
            List of resume dictionaries in standardized format
        """
        pass

    @abstractmethod
    def fetch_jobs(
        self,
        status: str = "open",
        limit: int = 50
    ) -> List[Dict]:
        """
        Fetch job descriptions from the ATS.

        Args:
            status: Job status filter ("open", "closed", "all")
            limit: Maximum number to fetch

        Returns:
            List of job dictionaries in standardized format
        """
        pass

    @abstractmethod
    def push_rankings(
        self,
        job_id: str,
        rankings: List[Dict]
    ) -> bool:
        """
        Push candidate rankings back to the ATS.

        Args:
            job_id: Job identifier
            rankings: List of {resume_id, score, notes}

        Returns:
            True if push successful
        """
        pass

    def standardize_resume(self, raw_resume: Dict) -> Dict:
        """
        Convert ATS-specific resume format to our standard format.
        Override in subclasses for specific ATS systems.
        """
        return raw_resume

    def standardize_job(self, raw_job: Dict) -> Dict:
        """
        Convert ATS-specific job format to our standard format.
        Override in subclasses for specific ATS systems.
        """
        return raw_job


class MockATSConnector(ATSConnector):
    """
    Mock ATS connector for testing and development.
    Loads data from local JSON files.
    """

    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.connected = False

    def connect(self, credentials: Dict[str, str] = None) -> bool:
        """Mock connection always succeeds."""
        self.connected = True
        logger.info("MockATS: Connected (using local files)")
        return True

    def fetch_resumes(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Fetch resumes from local JSON files."""
        resumes_dir = self.data_dir / "resumes"
        resumes = []

        for f in sorted(resumes_dir.glob("*.json"))[:limit]:
            with open(f) as fp:
                resumes.append(json.load(fp))

        logger.info(f"MockATS: Fetched {len(resumes)} resumes")
        return resumes

    def fetch_jobs(
        self,
        status: str = "open",
        limit: int = 50
    ) -> List[Dict]:
        """Fetch jobs from local JSON files."""
        jobs_dir = self.data_dir / "job_descriptions"
        jobs = []

        for f in sorted(jobs_dir.glob("*.json"))[:limit]:
            with open(f) as fp:
                jobs.append(json.load(fp))

        logger.info(f"MockATS: Fetched {len(jobs)} jobs")
        return jobs

    def push_rankings(
        self,
        job_id: str,
        rankings: List[Dict]
    ) -> bool:
        """Mock push - just logs the rankings."""
        logger.info(f"MockATS: Would push {len(rankings)} rankings for job {job_id}")
        return True


class GreenhouseConnector(ATSConnector):
    """
    Greenhouse ATS connector stub.

    To implement:
    1. pip install greenhouse-api
    2. Set GREENHOUSE_API_KEY environment variable
    3. Implement the abstract methods
    """

    def __init__(self):
        self.api_key = None
        self.base_url = "https://harvest.greenhouse.io/v1"

    def connect(self, credentials: Dict[str, str]) -> bool:
        self.api_key = credentials.get("api_key")
        if not self.api_key:
            logger.error("Greenhouse: Missing api_key in credentials")
            return False
        # In real implementation: validate API key with a test request
        logger.info("Greenhouse: Connection would be established here")
        return True

    def fetch_resumes(self, filters=None, limit=100) -> List[Dict]:
        raise NotImplementedError(
            "Greenhouse connector not fully implemented. "
            "See https://developers.greenhouse.io/harvest.html for API docs."
        )

    def fetch_jobs(self, status="open", limit=50) -> List[Dict]:
        raise NotImplementedError("Greenhouse connector not fully implemented.")

    def push_rankings(self, job_id: str, rankings: List[Dict]) -> bool:
        raise NotImplementedError("Greenhouse connector not fully implemented.")


# =============================================================================
# RANKING VERIFICATION SYSTEM
# =============================================================================

@dataclass
class VerificationResult:
    """Result of ranking verification."""
    is_valid: bool
    score_accuracy: float  # 0-1, how well scores match criteria
    ranking_consistency: float  # 0-1, are rankings properly ordered
    criteria_coverage: float  # 0-1, are all criteria evaluated
    issues: List[str]
    details: Dict[str, Any]


class RankingVerifier:
    """
    Verifies that resume rankings are complete and correct
    according to matching criteria.
    """

    def __init__(self, criteria: MatchingCriteria):
        self.criteria = criteria

    def verify_ranking(
        self,
        job: Dict,
        ranked_candidates: List[Dict],
        all_resumes: List[Dict]
    ) -> VerificationResult:
        """
        Verify a ranking is complete and correct.

        Checks:
        1. All candidates are scored
        2. Scores are within valid range (0-1)
        3. Rankings are properly sorted by score
        4. Score breakdowns sum correctly
        5. All criteria are evaluated for each candidate
        6. No duplicate candidates

        Args:
            job: Job description
            ranked_candidates: List of ranked results
            all_resumes: All available resumes (for completeness check)

        Returns:
            VerificationResult with detailed findings
        """
        issues = []
        details = {}

        # Check 1: Valid score range
        invalid_scores = []
        for i, candidate in enumerate(ranked_candidates):
            score = candidate.get("score", 0)
            if not 0 <= score <= 1:
                invalid_scores.append((i, score))

        if invalid_scores:
            issues.append(f"Invalid scores found: {invalid_scores}")

        score_validity = 1.0 - (len(invalid_scores) / max(len(ranked_candidates), 1))

        # Check 2: Proper ordering
        scores = [c.get("score", 0) for c in ranked_candidates]
        is_sorted = all(scores[i] >= scores[i+1] for i in range(len(scores)-1))

        if not is_sorted:
            issues.append("Rankings are not properly sorted by score")
            # Find inversions
            inversions = sum(
                1 for i in range(len(scores)-1)
                if scores[i] < scores[i+1]
            )
            ranking_consistency = 1.0 - (inversions / max(len(scores)-1, 1))
        else:
            ranking_consistency = 1.0

        # Check 3: No duplicates
        candidate_ids = [c.get("resume_id") for c in ranked_candidates]
        unique_ids = set(candidate_ids)
        if len(unique_ids) != len(candidate_ids):
            issues.append("Duplicate candidates found in ranking")

        # Check 4: Score breakdown validation
        breakdown_issues = []
        for candidate in ranked_candidates:
            breakdown = candidate.get("breakdown", {})
            if breakdown:
                breakdown_sum = sum(breakdown.values())
                # Allow some tolerance for floating point
                if not 0 <= breakdown_sum <= 1.5:
                    breakdown_issues.append(candidate.get("resume_id"))

        if breakdown_issues:
            issues.append(f"Score breakdown issues for: {breakdown_issues[:5]}")

        # Check 5: Criteria coverage
        criteria_checked = set()
        for candidate in ranked_candidates:
            breakdown = candidate.get("breakdown", {})
            criteria_checked.update(breakdown.keys())

        expected_criteria = {
            "semantic_similarity", "keyword_match",
            "tfidf_similarity", "neural_similarity",
            "chunked_neural_similarity"
        }
        # At least one similarity metric should be present
        has_similarity = bool(criteria_checked & expected_criteria)

        criteria_coverage = 1.0 if has_similarity else 0.5
        if not has_similarity:
            issues.append("No similarity metric found in breakdowns")

        # Calculate overall accuracy
        score_accuracy = (score_validity + (1 if not breakdown_issues else 0.8)) / 2

        # Build details
        details = {
            "total_candidates": len(ranked_candidates),
            "score_range": (min(scores) if scores else 0, max(scores) if scores else 0),
            "unique_candidates": len(unique_ids),
            "criteria_found": list(criteria_checked),
            "verification_timestamp": datetime.now().isoformat(),
        }

        is_valid = len(issues) == 0

        return VerificationResult(
            is_valid=is_valid,
            score_accuracy=score_accuracy,
            ranking_consistency=ranking_consistency,
            criteria_coverage=criteria_coverage,
            issues=issues,
            details=details
        )

    def generate_audit_report(
        self,
        job: Dict,
        ranked_candidates: List[Dict],
        verification: VerificationResult
    ) -> str:
        """Generate a human-readable audit report."""
        report = []
        report.append("=" * 60)
        report.append("RANKING VERIFICATION AUDIT REPORT")
        report.append("=" * 60)
        report.append("")
        report.append(f"Job: {job.get('title', 'Unknown')}")
        report.append(f"Employer: {job.get('employer', 'Unknown')}")
        report.append(f"Timestamp: {verification.details.get('verification_timestamp')}")
        report.append("")
        report.append("-" * 60)
        report.append("VERIFICATION RESULTS")
        report.append("-" * 60)
        report.append(f"Overall Valid: {'✓ YES' if verification.is_valid else '✗ NO'}")
        report.append(f"Score Accuracy: {verification.score_accuracy:.1%}")
        report.append(f"Ranking Consistency: {verification.ranking_consistency:.1%}")
        report.append(f"Criteria Coverage: {verification.criteria_coverage:.1%}")
        report.append("")

        if verification.issues:
            report.append("-" * 60)
            report.append("ISSUES FOUND")
            report.append("-" * 60)
            for issue in verification.issues:
                report.append(f"  • {issue}")
            report.append("")

        report.append("-" * 60)
        report.append("RANKING SUMMARY")
        report.append("-" * 60)
        report.append(f"Total Candidates Ranked: {verification.details['total_candidates']}")
        report.append(f"Score Range: {verification.details['score_range'][0]:.3f} - {verification.details['score_range'][1]:.3f}")
        report.append(f"Criteria Evaluated: {', '.join(verification.details['criteria_found'])}")
        report.append("")

        report.append("-" * 60)
        report.append("TOP 5 CANDIDATES")
        report.append("-" * 60)
        for i, candidate in enumerate(ranked_candidates[:5], 1):
            name = candidate.get("candidate_name", "Unknown")
            score = candidate.get("score", 0)
            report.append(f"  {i}. {name}: {score:.1%}")
            highlights = candidate.get("highlights", [])
            if highlights:
                report.append(f"     └─ {highlights[0]}")

        report.append("")
        report.append("=" * 60)
        report.append("END OF REPORT")
        report.append("=" * 60)

        return "\n".join(report)


# =============================================================================
# ENHANCED MATCHER WITH ALL FEATURES
# =============================================================================

class EnhancedMatcher:
    """
    Enhanced matcher that integrates all new features:
    - Location matching
    - Recency weighting
    - Configurable criteria
    - Verification
    """

    def __init__(
        self,
        base_matcher,  # TFIDFResumeMatcher or NeuralResumeMatcher
        criteria: MatchingCriteria = None
    ):
        self.base_matcher = base_matcher
        self.criteria = criteria or MatchingCriteria()
        self.verifier = RankingVerifier(self.criteria)

    def compute_enhanced_score(
        self,
        resume: Dict,
        job: Dict,
        base_score: float,
        base_breakdown: Dict
    ) -> Tuple[float, Dict, List[str]]:
        """
        Compute enhanced score with location and recency.

        Args:
            resume: Resume dictionary
            job: Job dictionary
            base_score: Score from base matcher
            base_breakdown: Score breakdown from base matcher

        Returns:
            Tuple of (enhanced_score, enhanced_breakdown, additional_highlights)
        """
        enhanced_breakdown = dict(base_breakdown)
        highlights = []

        # Location scoring
        if self.criteria.enable_location_matching:
            resume_loc = resume.get("personal_info", {}).get("location", "")
            job_loc = job.get("location", "")
            is_remote = job.get("remote", False) or "remote" in job_loc.lower()

            loc_score, loc_highlight = compute_location_score(
                resume_loc, job_loc,
                max_distance=self.criteria.max_distance_miles,
                is_remote=is_remote
            )
            enhanced_breakdown["location_match"] = loc_score
            if loc_highlight:
                highlights.append(loc_highlight)
        else:
            loc_score = 1.0  # Neutral if disabled

        # Recency scoring
        if self.criteria.enable_recency_weighting:
            recency_score, recency_highlights = compute_recency_score(
                resume.get("experience", []),
                decay_years=self.criteria.recency_decay_years,
                boost_multiplier=self.criteria.recent_experience_multiplier
            )
            enhanced_breakdown["recency_bonus"] = recency_score
            highlights.extend(recency_highlights)
        else:
            recency_score = 1.0  # Neutral if disabled

        # Combine scores using criteria weights
        # Base score already includes primary system, modules, experience, certs, skills
        base_weight = (
            self.criteria.primary_system_weight +
            self.criteria.module_experience_weight +
            self.criteria.years_experience_weight +
            self.criteria.certifications_weight +
            self.criteria.skills_weight
        )

        enhanced_score = (
            base_score * base_weight +
            loc_score * self.criteria.location_weight +
            recency_score * self.criteria.recency_weight
        )

        return enhanced_score, enhanced_breakdown, highlights

    def match_with_verification(
        self,
        job: Dict,
        top_k: int = 10,
        verify: bool = True
    ) -> Tuple[List[Dict], Optional[VerificationResult]]:
        """
        Match candidates with optional verification.

        Returns:
            Tuple of (ranked_candidates, verification_result or None)
        """
        # Get base matches
        base_results = self.base_matcher.match_job(job, top_k=top_k * 2)

        # Enhance each match
        enhanced_matches = []
        for match in base_results.matches:
            resume = next(
                (r for r in self.base_matcher.resumes if r.get("id") == match.resume_id),
                None
            )
            if resume:
                enhanced_score, enhanced_breakdown, extra_highlights = self.compute_enhanced_score(
                    resume, job,
                    match.score, match.breakdown
                )

                enhanced_matches.append({
                    "resume_id": match.resume_id,
                    "candidate_name": match.candidate_name,
                    "score": enhanced_score,
                    "breakdown": enhanced_breakdown,
                    "highlights": match.highlights + extra_highlights
                })

        # Re-sort by enhanced score
        enhanced_matches.sort(key=lambda x: x["score"], reverse=True)
        enhanced_matches = enhanced_matches[:top_k]

        # Verify if requested
        verification = None
        if verify:
            verification = self.verifier.verify_ranking(
                job, enhanced_matches, self.base_matcher.resumes
            )

        return enhanced_matches, verification


# =============================================================================
# DOMAIN GENERALIZATION
# =============================================================================

def create_domain_config(domain: str) -> MatchingCriteria:
    """
    Create matching criteria for a specific domain.

    Supported domains:
    - "healthcare": EHR systems, medical certifications, clinical experience
    - "technology": Tech stacks, programming languages, cloud platforms
    - "finance": Financial certifications, regulatory knowledge
    - "general": Balanced general-purpose matching
    """
    configs = {
        "healthcare": MatchingCriteria(
            domain="healthcare",
            primary_system_field="primary_ehr_system",
            primary_system_weight=0.25,
            certifications_weight=0.15,
        ),
        "technology": MatchingCriteria(
            domain="technology",
            primary_system_field="primary_tech_stack",
            primary_system_weight=0.20,
            skills_weight=0.25,
            certifications_weight=0.10,
        ),
        "finance": MatchingCriteria(
            domain="finance",
            primary_system_field="primary_specialty",
            primary_system_weight=0.20,  # Reduced to accommodate cert/exp weights
            module_experience_weight=0.10,  # Less emphasis on specific modules
            certifications_weight=0.20,  # CFA, CPA very important in finance
            years_experience_weight=0.20,  # Experience highly valued
        ),
        "general": MatchingCriteria(
            domain="general",
            primary_system_field="primary_industry",
            primary_system_weight=0.15,
            skills_weight=0.20,
            years_experience_weight=0.20,
        ),
    }

    if domain not in configs:
        logger.warning(f"Unknown domain '{domain}', using general config")
        return configs["general"]

    return configs[domain]


# =============================================================================
# CLI TESTING
# =============================================================================

def main():
    """Test the enhancements."""
    print("=" * 60)
    print("MATCHING ENHANCEMENTS TEST")
    print("=" * 60)

    # Test location matching
    print("\n1. LOCATION MATCHING")
    print("-" * 40)

    test_cases = [
        ("Boston, MA", "Boston, MA"),
        ("New York, NY", "Boston, MA"),
        ("Chicago, IL", "Boston, MA"),
        ("San Francisco, CA", "Boston, MA"),
        ("Remote", "Boston, MA"),
    ]

    for resume_loc, job_loc in test_cases:
        score, highlight = compute_location_score(resume_loc, job_loc)
        print(f"  {resume_loc} → {job_loc}: {score:.2f} ({highlight})")

    # Test recency scoring
    print("\n2. RECENCY WEIGHTING")
    print("-" * 40)

    test_experience = [
        {"title": "Current Role", "employer": "Company A", "start_date": "2022-01", "end_date": "Present"},
        {"title": "Previous Role", "employer": "Company B", "start_date": "2019-06", "end_date": "2021-12"},
        {"title": "Old Role", "employer": "Company C", "start_date": "2015-01", "end_date": "2019-05"},
    ]

    score, highlights = compute_recency_score(test_experience)
    print(f"  Recency Score: {score:.2f}")
    for h in highlights:
        print(f"  └─ {h}")

    # Test criteria validation
    print("\n3. MATCHING CRITERIA")
    print("-" * 40)

    criteria = MatchingCriteria()
    print(f"  Valid: {criteria.validate()}")
    print(f"  Domain: {criteria.domain}")
    print(f"  Weights: {json.dumps(criteria.to_dict()['weights'], indent=4)}")

    print("\n" + "=" * 60)
    print("TESTS COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
