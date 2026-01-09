#!/usr/bin/env python3
"""
Resume-to-Job Matching Script

Supports two matching modes:
1. TF-IDF + Keywords (fast, no dependencies)
2. Neural Embeddings (semantic understanding, requires sentence-transformers)
"""

import json
import os
import sys
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Literal
from enum import Enum
import argparse

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# =============================================================================
# CONFIGURATION
# =============================================================================

TOP_K = 10                    # Number of top candidates per job
SEMANTIC_WEIGHT = 0.7         # Weight for semantic (embedding) similarity
LEXICAL_WEIGHT = 0.3          # Weight for keyword matching


class MatchingMode(Enum):
    """Available matching algorithms."""
    TFIDF = "tfidf"           # TF-IDF + keyword matching (fast, no dependencies)
    NEURAL = "neural"         # Neural embeddings (semantic, requires sentence-transformers)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class MatchResult:
    """Result of matching a resume to a job."""
    resume_id: str
    candidate_name: str
    score: float
    breakdown: Dict[str, float]
    highlights: List[str]


@dataclass
class JobMatchResults:
    """All match results for a single job."""
    job_id: str
    job_title: str
    employer: str
    matches: List[MatchResult]
    processing_time_ms: float
    matching_mode: str


# =============================================================================
# BASE MATCHER CLASS
# =============================================================================

class BaseResumeMatcher:
    """Base class for resume matchers."""

    def __init__(self):
        self.resumes: List[Dict] = []

    def _resume_to_text(self, resume: Dict) -> str:
        """Convert resume JSON to searchable text."""
        parts = []

        if "personal_info" in resume:
            parts.append(resume["personal_info"].get("name", ""))

        if "summary" in resume:
            parts.append(resume["summary"])

        for exp in resume.get("experience", []):
            parts.append(exp.get("title", ""))
            parts.append(exp.get("employer", ""))
            for ehr in exp.get("ehr_systems", []):
                parts.append(ehr)
            for module in exp.get("modules", []):
                parts.append(module)
            for achievement in exp.get("achievements", []):
                parts.append(achievement)

        for edu in resume.get("education", []):
            parts.append(edu.get("degree", ""))
            parts.append(edu.get("institution", ""))

        parts.extend(resume.get("certifications", []))
        parts.extend(resume.get("skills", []))

        if "primary_ehr_system" in resume:
            parts.extend([resume["primary_ehr_system"]] * 3)

        return " ".join(parts)

    def _job_to_text(self, job: Dict) -> str:
        """Convert job description JSON to searchable text."""
        parts = []

        parts.append(job.get("title", ""))
        parts.append(job.get("employer", ""))
        parts.append(job.get("description", ""))

        if "primary_ehr_system" in job:
            parts.extend([job["primary_ehr_system"]] * 3)

        parts.extend(job.get("modules", []))
        parts.extend(job.get("responsibilities", []))

        req = job.get("required_qualifications", {})
        parts.extend(req.get("skills", []))
        parts.extend(req.get("certifications", []))

        pref = job.get("preferred_qualifications", {})
        parts.extend(pref.get("skills", []))
        parts.extend(pref.get("certifications", []))

        return " ".join(parts)

    def _compute_keyword_match(self, resume: Dict, job: Dict) -> tuple[float, List[str]]:
        """Compute keyword matching score and find highlights."""
        highlights = []
        score = 0.0
        max_possible = 0.0

        # EHR system match (highest weight)
        resume_ehr = resume.get("primary_ehr_system", "").lower()
        job_ehr = job.get("primary_ehr_system", "").lower()

        max_possible += 30
        if resume_ehr and job_ehr and resume_ehr == job_ehr:
            score += 30
            highlights.append(f"Primary EHR match: {resume.get('primary_ehr_system')}")
        elif resume_ehr and job_ehr:
            resume_text = self._resume_to_text(resume).lower()
            if job_ehr in resume_text:
                score += 20
                highlights.append(f"Has {job.get('primary_ehr_system')} experience")

        # Module matches
        job_modules = set(m.lower() for m in job.get("modules", []))
        resume_modules = set()
        for exp in resume.get("experience", []):
            resume_modules.update(m.lower() for m in exp.get("modules", []))

        matching_modules = job_modules & resume_modules
        if job_modules:
            max_possible += 20
            module_score = (len(matching_modules) / len(job_modules)) * 20
            score += module_score
            if matching_modules:
                highlights.append(f"Module matches: {len(matching_modules)}/{len(job_modules)}")

        # Experience years match
        min_years = job.get("experience_required", {}).get("min_years", 0)
        resume_years = resume.get("years_experience", 0)

        max_possible += 15
        if resume_years >= min_years:
            score += 15
            highlights.append(f"Experience: {resume_years} years (required: {min_years}+)")
        elif resume_years >= min_years - 2:
            score += 8
            highlights.append(f"Close experience: {resume_years} years (required: {min_years}+)")

        # Certification matches
        job_certs = set(c.lower() for c in job.get("required_qualifications", {}).get("certifications", []))
        resume_certs = set(c.lower() for c in resume.get("certifications", []))

        if job_certs:
            max_possible += 15
            matching_certs = job_certs & resume_certs
            cert_score = (len(matching_certs) / len(job_certs)) * 15
            score += cert_score
            if matching_certs:
                highlights.append(f"Required certifications: {len(matching_certs)}/{len(job_certs)}")

        # Skills overlap
        job_skills = set(s.lower() for s in job.get("required_qualifications", {}).get("skills", []))
        resume_skills = set(s.lower() for s in resume.get("skills", []))

        if job_skills:
            max_possible += 20
            matching_skills = job_skills & resume_skills
            skills_score = (len(matching_skills) / len(job_skills)) * 20
            score += skills_score
            if len(matching_skills) > 3:
                highlights.append(f"Skills match: {len(matching_skills)}/{len(job_skills)}")

        normalized = score / max_possible if max_possible > 0 else 0
        return normalized, highlights

    def index_resumes(self, resumes: List[Dict]):
        """Index all resumes for matching."""
        raise NotImplementedError

    def match_job(self, job: Dict, top_k: int = 10) -> JobMatchResults:
        """Find top matching resumes for a job."""
        raise NotImplementedError


# =============================================================================
# TF-IDF MATCHER (No External Dependencies)
# =============================================================================

class TFIDFResumeMatcher(BaseResumeMatcher):
    """
    Resume matching using TF-IDF and keyword overlap.
    Fast, no external dependencies required.
    """

    def __init__(self):
        super().__init__()
        self.resume_texts: List[str] = []
        self.resume_vectors: List[Dict[str, float]] = []
        self.idf_scores: Dict[str, float] = {}
        self.vocab: set = set()

    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization."""
        import re
        text = text.lower()
        words = re.findall(r'\b[a-z][a-z0-9+#]*\b', text)
        return [w for w in words if len(w) > 2]

    def _compute_tf(self, tokens: List[str]) -> Dict[str, float]:
        """Compute term frequency."""
        tf = {}
        for token in tokens:
            tf[token] = tf.get(token, 0) + 1
        max_freq = max(tf.values()) if tf else 1
        return {k: v / max_freq for k, v in tf.items()}

    def _compute_idf(self):
        """Compute inverse document frequency across all resumes."""
        import math
        doc_freq = {}
        n_docs = len(self.resume_texts)

        for text in self.resume_texts:
            tokens = set(self._tokenize(text))
            for token in tokens:
                doc_freq[token] = doc_freq.get(token, 0) + 1

        self.idf_scores = {
            token: math.log(n_docs / (freq + 1)) + 1
            for token, freq in doc_freq.items()
        }
        self.vocab = set(doc_freq.keys())

    def _text_to_vector(self, text: str) -> Dict[str, float]:
        """Convert text to TF-IDF vector."""
        tokens = self._tokenize(text)
        tf = self._compute_tf(tokens)
        return {
            token: tf_score * self.idf_scores.get(token, 1)
            for token, tf_score in tf.items()
        }

    def _cosine_similarity(self, vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
        """Compute cosine similarity between two sparse vectors."""
        import math

        common_keys = set(vec1.keys()) & set(vec2.keys())
        if not common_keys:
            return 0.0

        dot_product = sum(vec1[k] * vec2[k] for k in common_keys)
        norm1 = math.sqrt(sum(v ** 2 for v in vec1.values()))
        norm2 = math.sqrt(sum(v ** 2 for v in vec2.values()))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def index_resumes(self, resumes: List[Dict], quiet: bool = False):
        """Index all resumes for matching."""
        self.resumes = resumes
        self.resume_texts = [self._resume_to_text(r) for r in resumes]

        if not quiet:
            print("  Computing TF-IDF vectors...")
        self._compute_idf()
        self.resume_vectors = [self._text_to_vector(text) for text in self.resume_texts]
        if not quiet:
            print(f"  Indexed {len(resumes)} resumes with {len(self.vocab)} unique terms")

    def match_job(self, job: Dict, top_k: int = 10) -> JobMatchResults:
        """Find top matching resumes for a job."""
        start_time = time.time()

        job_text = self._job_to_text(job)
        job_vector = self._text_to_vector(job_text)

        scored_resumes = []
        for i, resume in enumerate(self.resumes):
            tfidf_score = self._cosine_similarity(job_vector, self.resume_vectors[i])
            keyword_score, highlights = self._compute_keyword_match(resume, job)
            combined = (SEMANTIC_WEIGHT * tfidf_score) + (LEXICAL_WEIGHT * keyword_score)

            scored_resumes.append({
                "index": i,
                "resume": resume,
                "score": combined,
                "tfidf_score": tfidf_score,
                "keyword_score": keyword_score,
                "highlights": highlights
            })

        scored_resumes.sort(key=lambda x: x["score"], reverse=True)

        matches = []
        for item in scored_resumes[:top_k]:
            resume = item["resume"]
            matches.append(MatchResult(
                resume_id=resume.get("id", "unknown"),
                candidate_name=resume.get("personal_info", {}).get("name", "Unknown"),
                score=round(item["score"], 4),
                breakdown={
                    "tfidf_similarity": round(item["tfidf_score"], 4),
                    "keyword_match": round(item["keyword_score"], 4)
                },
                highlights=item["highlights"]
            ))

        processing_time = (time.time() - start_time) * 1000

        return JobMatchResults(
            job_id=job.get("id", "unknown"),
            job_title=job.get("title", "Unknown"),
            employer=job.get("employer", "Unknown"),
            matches=matches,
            processing_time_ms=round(processing_time, 2),
            matching_mode="TF-IDF + Keywords"
        )


# =============================================================================
# NEURAL EMBEDDING MATCHER (Requires sentence-transformers)
# =============================================================================

class NeuralResumeMatcher(BaseResumeMatcher):
    """
    Resume matching using neural embeddings from sentence-transformers.
    Provides semantic understanding of text similarity.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        super().__init__()
        self.model_name = model_name
        self.model = None
        self.resume_embeddings = None

    def _load_model(self):
        """Lazy load the sentence transformer model."""
        if self.model is None:
            try:
                from sentence_transformers import SentenceTransformer
                print(f"  Loading neural model: {self.model_name}...")
                self.model = SentenceTransformer(self.model_name)
                print(f"  Model loaded successfully")
            except ImportError:
                raise ImportError(
                    "Neural matching requires sentence-transformers. "
                    "Install with: pip install sentence-transformers"
                )

    def _cosine_similarity_np(self, vec1, vec2) -> float:
        """Compute cosine similarity using numpy."""
        import numpy as np
        dot = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(dot / (norm1 * norm2))

    def index_resumes(self, resumes: List[Dict], quiet: bool = False):
        """Index all resumes using neural embeddings."""
        self._load_model()
        self.resumes = resumes

        if not quiet:
            print("  Generating neural embeddings for resumes...")

        resume_texts = [self._resume_to_text(r) for r in resumes]
        self.resume_embeddings = self.model.encode(resume_texts, show_progress_bar=not quiet)

        if not quiet:
            print(f"  Indexed {len(resumes)} resumes with {self.resume_embeddings.shape[1]}-dim embeddings")

    def match_job(self, job: Dict, top_k: int = 10) -> JobMatchResults:
        """Find top matching resumes using neural similarity."""
        start_time = time.time()

        job_text = self._job_to_text(job)
        job_embedding = self.model.encode([job_text])[0]

        scored_resumes = []
        for i, resume in enumerate(self.resumes):
            # Neural semantic similarity
            neural_score = self._cosine_similarity_np(job_embedding, self.resume_embeddings[i])

            # Keyword matching (still important for exact matches)
            keyword_score, highlights = self._compute_keyword_match(resume, job)

            # Combined score - neural is the "semantic" component
            combined = (SEMANTIC_WEIGHT * neural_score) + (LEXICAL_WEIGHT * keyword_score)

            scored_resumes.append({
                "index": i,
                "resume": resume,
                "score": combined,
                "neural_score": neural_score,
                "keyword_score": keyword_score,
                "highlights": highlights
            })

        scored_resumes.sort(key=lambda x: x["score"], reverse=True)

        matches = []
        for item in scored_resumes[:top_k]:
            resume = item["resume"]
            matches.append(MatchResult(
                resume_id=resume.get("id", "unknown"),
                candidate_name=resume.get("personal_info", {}).get("name", "Unknown"),
                score=round(item["score"], 4),
                breakdown={
                    "neural_similarity": round(item["neural_score"], 4),
                    "keyword_match": round(item["keyword_score"], 4)
                },
                highlights=item["highlights"]
            ))

        processing_time = (time.time() - start_time) * 1000

        return JobMatchResults(
            job_id=job.get("id", "unknown"),
            job_title=job.get("title", "Unknown"),
            employer=job.get("employer", "Unknown"),
            matches=matches,
            processing_time_ms=round(processing_time, 2),
            matching_mode="Neural Embeddings (sentence-transformers)"
        )


# =============================================================================
# MATCHER FACTORY
# =============================================================================

def create_matcher(mode: MatchingMode, model_name: str = "all-MiniLM-L6-v2") -> BaseResumeMatcher:
    """Factory function to create the appropriate matcher."""
    if mode == MatchingMode.TFIDF:
        return TFIDFResumeMatcher()
    elif mode == MatchingMode.NEURAL:
        return NeuralResumeMatcher(model_name=model_name)
    else:
        raise ValueError(f"Unknown matching mode: {mode}")


def is_neural_available() -> bool:
    """Check if neural matching is available."""
    try:
        from sentence_transformers import SentenceTransformer
        return True
    except ImportError:
        return False


# Keep SimpleResumeMatcher as alias for backward compatibility
SimpleResumeMatcher = TFIDFResumeMatcher


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def load_json_files(directory: Path) -> List[Dict]:
    """Load all JSON files from a directory."""
    files = sorted(directory.glob("*.json"))
    data = []
    for f in files:
        with open(f) as fp:
            data.append(json.load(fp))
    return data


def results_to_dict(results: List[JobMatchResults], mode: str) -> Dict[str, Any]:
    """Convert results to JSON-serializable dict."""
    return {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "config": {
            "top_k": TOP_K,
            "semantic_weight": SEMANTIC_WEIGHT,
            "lexical_weight": LEXICAL_WEIGHT,
            "matching_mode": mode
        },
        "job_matches": [
            {
                "job_id": r.job_id,
                "job_title": r.job_title,
                "employer": r.employer,
                "processing_time_ms": r.processing_time_ms,
                "matching_mode": r.matching_mode,
                "top_candidates": [
                    {
                        "rank": i + 1,
                        "resume_id": m.resume_id,
                        "candidate_name": m.candidate_name,
                        "match_score": m.score,
                        "score_breakdown": m.breakdown,
                        "match_highlights": m.highlights
                    }
                    for i, m in enumerate(r.matches)
                ]
            }
            for r in results
        ]
    }


def print_results_summary(results: List[JobMatchResults]):
    """Print a summary of matching results."""
    print("\n" + "=" * 70)
    print("RESUME MATCHING RESULTS")
    print("=" * 70)

    for job_result in results:
        print(f"\n{'─' * 70}")
        print(f"JOB: {job_result.job_title}")
        print(f"Employer: {job_result.employer}")
        print(f"Mode: {job_result.matching_mode}")
        print(f"Processing time: {job_result.processing_time_ms:.1f}ms")
        print(f"{'─' * 70}")

        for i, match in enumerate(job_result.matches[:5], 1):
            print(f"\n  #{i}: {match.candidate_name}")
            breakdown_str = ", ".join(f"{k}: {v:.3f}" for k, v in match.breakdown.items())
            print(f"      Score: {match.score:.3f} ({breakdown_str})")
            if match.highlights:
                print(f"      Highlights: {'; '.join(match.highlights[:3])}")


def main():
    parser = argparse.ArgumentParser(description="Match resumes to job descriptions")
    parser.add_argument("--resumes-dir", type=str, default="test_data/resumes",
                        help="Directory containing resume JSON files")
    parser.add_argument("--jobs-dir", type=str, default="test_data/job_descriptions",
                        help="Directory containing job JSON files")
    parser.add_argument("--output", type=str, default="results/matches.json",
                        help="Output file for results")
    parser.add_argument("--top-k", type=int, default=TOP_K,
                        help="Number of top candidates per job")
    parser.add_argument("--mode", type=str, choices=["tfidf", "neural"], default="tfidf",
                        help="Matching mode: 'tfidf' (fast, no deps) or 'neural' (semantic)")
    parser.add_argument("--model", type=str, default="all-MiniLM-L6-v2",
                        help="Neural model name (for --mode neural)")
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress detailed output")
    args = parser.parse_args()

    base_dir = Path(__file__).parent.parent
    resumes_dir = base_dir / args.resumes_dir
    jobs_dir = base_dir / args.jobs_dir
    output_path = base_dir / args.output

    print("=" * 70)
    print("HEALTHCARE RESUME MATCHING SYSTEM")
    print("=" * 70)

    # Check neural availability
    mode = MatchingMode(args.mode)
    if mode == MatchingMode.NEURAL and not is_neural_available():
        print("\nWARNING: Neural mode requested but sentence-transformers not installed.")
        print("Install with: pip install sentence-transformers")
        print("Falling back to TF-IDF mode.\n")
        mode = MatchingMode.TFIDF

    print(f"\nMatching Mode: {mode.value.upper()}")

    # Load data
    print(f"\nLoading resumes from {resumes_dir}...")
    resumes = load_json_files(resumes_dir)
    print(f"  Loaded {len(resumes)} resumes")

    print(f"\nLoading job descriptions from {jobs_dir}...")
    jobs = load_json_files(jobs_dir)
    print(f"  Loaded {len(jobs)} job descriptions")

    if not resumes:
        print("\nERROR: No resumes found. Run generate_test_data.py first.")
        sys.exit(1)

    if not jobs:
        print("\nERROR: No job descriptions found. Run generate_test_data.py first.")
        sys.exit(1)

    # Initialize matcher
    print("\nBuilding search index...")
    matcher = create_matcher(mode, model_name=args.model)
    matcher.index_resumes(resumes, quiet=args.quiet)

    # Match all jobs
    print(f"\nMatching {len(jobs)} jobs to {len(resumes)} resumes...")
    start_time = time.time()

    results = []
    for i, job in enumerate(jobs, 1):
        result = matcher.match_job(job, top_k=args.top_k)
        results.append(result)
        if not args.quiet:
            print(f"  Matched job {i}/{len(jobs)}: {job.get('title', 'Unknown')[:40]}...")

    total_time = time.time() - start_time

    # Print results
    if not args.quiet:
        print_results_summary(results)

    # Save results
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results_to_dict(results, mode.value), f, indent=2)

    print(f"\n{'=' * 70}")
    print(f"COMPLETE")
    print(f"{'=' * 70}")
    print(f"Matching mode: {mode.value.upper()}")
    print(f"Total processing time: {total_time:.2f} seconds")
    print(f"Average time per job: {(total_time / len(jobs)) * 1000:.1f}ms")
    print(f"Results saved to: {output_path}")


if __name__ == "__main__":
    main()
