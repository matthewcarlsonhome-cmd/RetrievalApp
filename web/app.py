#!/usr/bin/env python3
"""
Resume Matching System - Web Interface

A Flask application for matching resumes to job descriptions across multiple domains:
- Healthcare IT (EHR systems, clinical implementations)
- Technology (software engineering, cloud, data)
- Business (analysts, product managers, operations)
- Marketing (digital, content, analytics)

Supports three matching modes:
- TF-IDF + Keywords (fast, no dependencies)
- Neural Embeddings (semantic understanding, requires sentence-transformers)
- Chunked Neural (proper chunking with vector persistence)
"""

import json
import logging
import os
import sys
import traceback
from pathlib import Path
from flask import Flask, render_template, request, jsonify

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.match_resumes import (
    TFIDFResumeMatcher,
    NeuralResumeMatcher,
    MatchingMode,
    is_neural_available,
    load_json_files
)

app = Flask(__name__)

# =============================================================================
# ERROR HANDLING
# =============================================================================

@app.errorhandler(Exception)
def handle_exception(e):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {e}")
    logger.error(traceback.format_exc())

    if request.path.startswith('/api/'):
        return jsonify({
            "error": "Internal server error",
            "message": str(e) if app.debug else "An unexpected error occurred"
        }), 500

    return render_template(
        "error.html",
        message=f"An error occurred: {str(e)}" if app.debug else "An unexpected error occurred"
    ), 500


@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors."""
    if request.path.startswith('/api/'):
        return jsonify({"error": "Not found"}), 404
    return render_template("error.html", message="Page not found"), 404

# =============================================================================
# DATA LOADING
# =============================================================================

BASE_DIR = Path(__file__).parent.parent

# Data directories - healthcare (original) and general (IT/Business/Marketing)
HEALTHCARE_RESUMES_DIR = BASE_DIR / "test_data" / "resumes"
HEALTHCARE_JOBS_DIR = BASE_DIR / "test_data" / "job_descriptions"
GENERAL_RESUMES_DIR = BASE_DIR / "data" / "general" / "resumes"
GENERAL_JOBS_DIR = BASE_DIR / "data" / "general" / "job_descriptions"

# Global data stores (loaded on startup)
RESUMES = []
JOBS = []

# Matcher cache - stores indexed matchers for all modes
MATCHERS = {
    "tfidf": None,
    "neural": None,
    "chunked": None
}
NEURAL_AVAILABLE = False
CHUNKED_AVAILABLE = False


def load_data():
    """Load resumes and jobs from all data sources on startup."""
    global RESUMES, JOBS, MATCHERS, NEURAL_AVAILABLE, CHUNKED_AVAILABLE

    try:
        # Load healthcare resumes
        if HEALTHCARE_RESUMES_DIR.exists():
            healthcare_resumes = load_json_files(HEALTHCARE_RESUMES_DIR)
            RESUMES.extend(healthcare_resumes)
            logger.info(f"Loaded {len(healthcare_resumes)} healthcare resumes")
        else:
            logger.warning(f"{HEALTHCARE_RESUMES_DIR} not found. Run generate_test_data.py first.")

        # Load general resumes (IT, Business, Marketing)
        if GENERAL_RESUMES_DIR.exists():
            general_resumes = load_json_files(GENERAL_RESUMES_DIR)
            RESUMES.extend(general_resumes)
            logger.info(f"Loaded {len(general_resumes)} general resumes")
        else:
            logger.warning(f"{GENERAL_RESUMES_DIR} not found. Run generate_general_test_data.py first.")

        logger.info(f"Total resumes loaded: {len(RESUMES)}")

        # Load healthcare jobs
        if HEALTHCARE_JOBS_DIR.exists():
            healthcare_jobs = load_json_files(HEALTHCARE_JOBS_DIR)
            JOBS.extend(healthcare_jobs)
            logger.info(f"Loaded {len(healthcare_jobs)} healthcare jobs")
        else:
            logger.warning(f"{HEALTHCARE_JOBS_DIR} not found. Run generate_test_data.py first.")

        # Load general jobs (IT, Business, Marketing)
        if GENERAL_JOBS_DIR.exists():
            general_jobs = load_json_files(GENERAL_JOBS_DIR)
            JOBS.extend(general_jobs)
            logger.info(f"Loaded {len(general_jobs)} general jobs")
        else:
            logger.warning(f"{GENERAL_JOBS_DIR} not found. Run generate_general_test_data.py first.")

        logger.info(f"Total jobs loaded: {len(JOBS)}")

        # Check if neural matching is available
        NEURAL_AVAILABLE = is_neural_available()
        CHUNKED_AVAILABLE = NEURAL_AVAILABLE  # Chunked mode also requires sentence-transformers

        if NEURAL_AVAILABLE:
            logger.info("Neural matching: AVAILABLE (sentence-transformers installed)")
        else:
            logger.info("Neural matching: NOT AVAILABLE (install sentence-transformers to enable)")

        # Pre-build TF-IDF index (fast)
        if RESUMES:
            logger.info("Building TF-IDF index...")
            MATCHERS["tfidf"] = TFIDFResumeMatcher()
            MATCHERS["tfidf"].index_resumes(RESUMES, quiet=True)
            logger.info("TF-IDF index ready")

    except Exception as e:
        logger.error(f"Error loading data: {e}")
        logger.error(traceback.format_exc())


def get_matcher(mode: str, candidates: list = None):
    """
    Get or create a matcher for the specified mode.

    If candidates is None, returns the global matcher (for all resumes).
    If candidates is provided, creates a temporary matcher for filtered candidates.

    Modes:
    - tfidf: TF-IDF + keyword matching (fast, no dependencies)
    - neural: Neural embeddings (semantic, may truncate long documents)
    - chunked: Chunked neural with proper vector storage (recommended for neural)
    """
    global MATCHERS, NEURAL_AVAILABLE, CHUNKED_AVAILABLE

    try:
        # Handle chunked mode
        if mode == "chunked":
            if not CHUNKED_AVAILABLE:
                logger.warning("Chunked mode not available, falling back to TF-IDF")
                return MATCHERS["tfidf"]

            from scripts.vector_store import ChunkedNeuralMatcher

            if candidates is not None:
                # Create temporary chunked matcher for filtered candidates
                import tempfile
                temp_dir = Path(tempfile.mkdtemp())
                matcher = ChunkedNeuralMatcher(store_path=temp_dir)
                matcher.index_resumes(candidates, quiet=True)
                return matcher

            # Lazy-load global chunked matcher
            if MATCHERS["chunked"] is None:
                logger.info("Building chunked neural index (first use)...")
                store_path = BASE_DIR / "vector_store"
                MATCHERS["chunked"] = ChunkedNeuralMatcher(store_path=store_path)
                MATCHERS["chunked"].index_resumes(RESUMES, quiet=False)
                logger.info("Chunked neural index ready")

            return MATCHERS["chunked"]

        # If filtering candidates, always create a new temporary matcher
        if candidates is not None:
            if mode == "neural" and NEURAL_AVAILABLE:
                matcher = NeuralResumeMatcher()
                matcher.index_resumes(candidates, quiet=True)
                return matcher
            else:
                matcher = TFIDFResumeMatcher()
                matcher.index_resumes(candidates, quiet=True)
                return matcher

        # Otherwise, use global cached matchers
        if mode == "neural":
            if not NEURAL_AVAILABLE:
                logger.warning("Neural not available, falling back to TF-IDF")
                return MATCHERS["tfidf"]

            # Lazy-load neural matcher on first use
            if MATCHERS["neural"] is None:
                logger.info("Building neural index (first use)...")
                MATCHERS["neural"] = NeuralResumeMatcher()
                MATCHERS["neural"].index_resumes(RESUMES, quiet=False)
                logger.info("Neural index ready")

            return MATCHERS["neural"]
        else:
            return MATCHERS["tfidf"]

    except Exception as e:
        logger.error(f"Error creating matcher: {e}")
        logger.error(traceback.format_exc())
        # Fall back to TF-IDF on error
        return MATCHERS["tfidf"]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_unique_values(field_path: str, data_list: list) -> list:
    """Extract unique values from a nested field across all items."""
    values = set()
    for item in data_list:
        parts = field_path.split(".")
        value = item
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            elif isinstance(value, list) and part.isdigit():
                value = value[int(part)] if int(part) < len(value) else None
            else:
                value = None
            if value is None:
                break
        if value:
            if isinstance(value, list):
                values.update(value)
            else:
                values.add(value)
    return sorted(values)


def get_primary_systems(resumes: list) -> list:
    """
    Extract all primary systems/technologies from resumes across all domains.

    Handles:
    - Healthcare: primary_ehr_system (Epic, Cerner, etc.)
    - Technology: primary_tech_stack (AWS, Python, etc.)
    - Business: primary_specialty (analysis, product, etc.)
    - Marketing: primary_specialty (digital, content, etc.)
    """
    systems = set()
    for r in resumes:
        # Healthcare
        if r.get("primary_ehr_system"):
            systems.add(r["primary_ehr_system"])
        # Technology
        if r.get("primary_tech_stack"):
            systems.add(r["primary_tech_stack"])
        # Business/Marketing specialty
        if r.get("primary_specialty"):
            systems.add(r["primary_specialty"].replace("_", " ").title())
        # Tech specialization
        if r.get("tech_specialization"):
            systems.add(r["tech_specialization"].title())
    return sorted(systems)


def get_domains(resumes: list) -> list:
    """Extract unique domains from resumes."""
    domains = set()
    for r in resumes:
        if r.get("domain"):
            domains.add(r["domain"].title())
        elif r.get("primary_ehr_system"):
            domains.add("Healthcare")
    return sorted(domains)


def filter_resumes(resumes: list, filters: dict) -> list:
    """Apply filters to resume list across all domains."""
    filtered = resumes

    # Filter by primary system (EHR, tech stack, or specialty)
    if filters.get("primary_system"):
        system = filters["primary_system"].lower()
        filtered = [
            r for r in filtered
            if system in r.get("primary_ehr_system", "").lower()
            or system in r.get("primary_tech_stack", "").lower()
            or system in r.get("primary_specialty", "").lower()
            or system in r.get("tech_specialization", "").lower()
            or any(system in str(exp.get("ehr_systems", [])).lower() for exp in r.get("experience", []))
            or any(system in str(exp.get("tech_stack", [])).lower() for exp in r.get("experience", []))
        ]

    # Filter by domain
    if filters.get("domain"):
        domain = filters["domain"].lower()
        filtered = [
            r for r in filtered
            if r.get("domain", "").lower() == domain
            or (domain == "healthcare" and r.get("primary_ehr_system"))
        ]

    # Filter by minimum experience
    if filters.get("min_experience"):
        min_exp = int(filters["min_experience"])
        filtered = [r for r in filtered if r.get("years_experience", 0) >= min_exp]

    # Filter by maximum experience
    if filters.get("max_experience"):
        max_exp = int(filters["max_experience"])
        filtered = [r for r in filtered if r.get("years_experience", 0) <= max_exp]

    # Filter by location (partial match)
    if filters.get("location"):
        loc = filters["location"].lower()
        filtered = [
            r for r in filtered
            if loc in r.get("personal_info", {}).get("location", "").lower()
        ]

    # Filter by certification (partial match)
    if filters.get("certification"):
        cert = filters["certification"].lower()
        filtered = [
            r for r in filtered
            if any(cert in c.lower() for c in r.get("certifications", []))
        ]

    return filtered


# =============================================================================
# ROUTES
# =============================================================================

@app.route("/")
def index():
    """Home page - search interface."""
    # Get unique values for filter dropdowns
    primary_systems = get_primary_systems(RESUMES)
    domains = get_domains(RESUMES)
    locations = sorted(set(
        r.get("personal_info", {}).get("location", "").split(",")[0].strip()
        for r in RESUMES
        if r.get("personal_info", {}).get("location")
    ))

    return render_template(
        "index.html",
        jobs=JOBS,
        primary_systems=primary_systems,
        domains=domains,
        locations=locations,
        resume_count=len(RESUMES),
        job_count=len(JOBS),
        neural_available=NEURAL_AVAILABLE,
        chunked_available=CHUNKED_AVAILABLE
    )


@app.route("/search", methods=["GET", "POST"])
def search():
    """Search for matching candidates."""
    if request.method == "GET":
        return render_template("search.html", jobs=JOBS, neural_available=NEURAL_AVAILABLE)

    # Get search parameters
    job_id = request.form.get("job_id")
    custom_query = request.form.get("custom_query", "").strip()
    top_k = int(request.form.get("top_k", 10))
    matching_mode = request.form.get("matching_mode", "tfidf")

    # Validate matching mode
    if matching_mode == "neural" and not NEURAL_AVAILABLE:
        matching_mode = "tfidf"

    # Get filters
    filters = {
        "primary_system": request.form.get("primary_system"),
        "domain": request.form.get("domain"),
        "min_experience": request.form.get("min_experience"),
        "max_experience": request.form.get("max_experience"),
        "location": request.form.get("location"),
        "certification": request.form.get("certification"),
    }

    # Build job query
    if job_id:
        job = next((j for j in JOBS if j.get("id") == job_id), None)
        if not job:
            return render_template("error.html", message="Job not found")
    elif custom_query:
        # Create a synthetic job from the custom query
        job = {
            "id": "custom",
            "title": "Custom Search",
            "description": custom_query,
            "employer": "Custom Query",
            "primary_ehr_system": request.form.get("ehr_system", ""),
            "modules": [],
            "experience_required": {"min_years": int(filters.get("min_experience") or 0)},
            "required_qualifications": {
                "skills": custom_query.split(),
                "certifications": []
            },
            "preferred_qualifications": {"skills": [], "certifications": []}
        }
    else:
        return render_template("error.html", message="Please select a job or enter a search query")

    # Apply pre-filters to reduce candidate pool
    candidates = filter_resumes(RESUMES, filters)

    if not candidates:
        return render_template(
            "results.html",
            job=job,
            matches=[],
            filters=filters,
            matching_mode=matching_mode,
            neural_available=NEURAL_AVAILABLE,
            message="No candidates match the selected filters"
        )

    # Get matcher for the selected mode (creates temp matcher for filtered candidates)
    matcher = get_matcher(matching_mode, candidates)

    # Run matching
    results = matcher.match_job(job, top_k=min(top_k, len(candidates)))

    # Enrich results with full resume data
    matches = []
    for match in results.matches:
        resume = next((r for r in candidates if r.get("id") == match.resume_id), None)
        if resume:
            matches.append({
                "rank": len(matches) + 1,
                "score": match.score,
                "breakdown": match.breakdown,
                "highlights": match.highlights,
                "resume": resume
            })

    return render_template(
        "results.html",
        job=job,
        matches=matches,
        filters=filters,
        total_candidates=len(candidates),
        processing_time=results.processing_time_ms,
        matching_mode=matching_mode,
        matching_mode_display=results.matching_mode,
        neural_available=NEURAL_AVAILABLE
    )


@app.route("/candidate/<resume_id>")
def candidate_detail(resume_id):
    """View detailed candidate profile."""
    resume = next((r for r in RESUMES if r.get("id") == resume_id), None)
    if not resume:
        return render_template("error.html", message="Candidate not found")

    return render_template("candidate.html", resume=resume)


@app.route("/job/<job_id>")
def job_detail(job_id):
    """View detailed job description."""
    job = next((j for j in JOBS if j.get("id") == job_id), None)
    if not job:
        return render_template("error.html", message="Job not found")

    return render_template("job.html", job=job)


@app.route("/api/search", methods=["POST"])
def api_search():
    """API endpoint for programmatic search."""
    data = request.get_json()

    job_id = data.get("job_id")
    top_k = data.get("top_k", 10)
    filters = data.get("filters", {})
    matching_mode = data.get("matching_mode", "tfidf")

    # Validate matching mode
    if matching_mode == "neural" and not NEURAL_AVAILABLE:
        matching_mode = "tfidf"

    if not job_id:
        return jsonify({"error": "job_id required"}), 400

    job = next((j for j in JOBS if j.get("id") == job_id), None)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    candidates = filter_resumes(RESUMES, filters)

    if not candidates:
        return jsonify({"job": job, "matches": [], "message": "No candidates match filters"})

    matcher = get_matcher(matching_mode, candidates)
    results = matcher.match_job(job, top_k=min(top_k, len(candidates)))

    return jsonify({
        "job": job,
        "matching_mode": results.matching_mode,
        "matches": [
            {
                "rank": i + 1,
                "resume_id": m.resume_id,
                "candidate_name": m.candidate_name,
                "score": m.score,
                "breakdown": m.breakdown,
                "highlights": m.highlights
            }
            for i, m in enumerate(results.matches)
        ],
        "total_candidates": len(candidates),
        "processing_time_ms": results.processing_time_ms
    })


@app.route("/api/resumes")
def api_resumes():
    """API endpoint to list all resumes."""
    return jsonify({
        "count": len(RESUMES),
        "resumes": [
            {
                "id": r.get("id"),
                "name": r.get("personal_info", {}).get("name"),
                "primary_ehr": r.get("primary_ehr_system"),
                "years_experience": r.get("years_experience"),
                "location": r.get("personal_info", {}).get("location")
            }
            for r in RESUMES
        ]
    })


@app.route("/api/jobs")
def api_jobs():
    """API endpoint to list all jobs."""
    return jsonify({
        "count": len(JOBS),
        "jobs": [
            {
                "id": j.get("id"),
                "title": j.get("title"),
                "employer": j.get("employer"),
                "primary_ehr": j.get("primary_ehr_system"),
                "employment_type": j.get("employment_type"),
                "contract_type": j.get("contract_type")
            }
            for j in JOBS
        ]
    })


@app.route("/api/status")
def api_status():
    """API endpoint for system status."""
    modes = ["tfidf"]
    if NEURAL_AVAILABLE:
        modes.append("neural")
    if CHUNKED_AVAILABLE:
        modes.append("chunked")

    return jsonify({
        "resumes_loaded": len(RESUMES),
        "jobs_loaded": len(JOBS),
        "neural_available": NEURAL_AVAILABLE,
        "chunked_available": CHUNKED_AVAILABLE,
        "matching_modes": modes,
        "tfidf_indexed": MATCHERS["tfidf"] is not None,
        "neural_indexed": MATCHERS["neural"] is not None,
        "chunked_indexed": MATCHERS["chunked"] is not None,
        "vector_store_path": str(BASE_DIR / "vector_store") if CHUNKED_AVAILABLE else None
    })


@app.route("/health")
def health_check():
    """Health check endpoint for Render/production monitoring."""
    return jsonify({
        "status": "healthy",
        "resumes_loaded": len(RESUMES),
        "jobs_loaded": len(JOBS),
        "tfidf_ready": MATCHERS["tfidf"] is not None
    }), 200


# =============================================================================
# STARTUP - Load data when module is imported (for gunicorn)
# =============================================================================

# Load data on module import (needed for gunicorn/production)
logger.info("Initializing Resume Matching Application...")
load_data()

# Auto-generate test data if none exists (development convenience)
if not RESUMES and RESUMES_DIR.parent.exists():
    logger.info("No test data found. Generating sample data...")
    try:
        import subprocess
        subprocess.run([sys.executable, str(BASE_DIR / "scripts" / "generate_test_data.py")],
                      capture_output=True, timeout=60)
        load_data()
    except Exception as e:
        logger.warning(f"Could not auto-generate test data: {e}")


# =============================================================================
# MAIN (for local development)
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Resume Matching - Web Interface")
    print("=" * 60)
    print(f"Resumes loaded: {len(RESUMES)}")
    print(f"Jobs loaded: {len(JOBS)}")
    print(f"Neural matching: {'Available' if NEURAL_AVAILABLE else 'Not available'}")

    # Use environment variables for configuration
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"

    print(f"\nStarting web server on port {port}...")
    print(f"Open http://localhost:{port} in your browser")
    print("=" * 60)

    app.run(debug=debug, host="0.0.0.0", port=port)
