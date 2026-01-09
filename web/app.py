#!/usr/bin/env python3
"""
Healthcare Resume Matching - Web Interface

A simple Flask application for non-technical users to search and match
resumes against job descriptions.
"""

import json
import os
import sys
from pathlib import Path
from flask import Flask, render_template, request, jsonify

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.match_resumes import SimpleResumeMatcher, load_json_files

app = Flask(__name__)

# =============================================================================
# DATA LOADING
# =============================================================================

BASE_DIR = Path(__file__).parent.parent
RESUMES_DIR = BASE_DIR / "test_data" / "resumes"
JOBS_DIR = BASE_DIR / "test_data" / "job_descriptions"

# Global data stores (loaded on startup)
RESUMES = []
JOBS = []
MATCHER = None


def load_data():
    """Load resumes and jobs on startup."""
    global RESUMES, JOBS, MATCHER

    if RESUMES_DIR.exists():
        RESUMES = load_json_files(RESUMES_DIR)
        print(f"Loaded {len(RESUMES)} resumes")
    else:
        print(f"Warning: {RESUMES_DIR} not found. Run generate_test_data.py first.")

    if JOBS_DIR.exists():
        JOBS = load_json_files(JOBS_DIR)
        print(f"Loaded {len(JOBS)} job descriptions")
    else:
        print(f"Warning: {JOBS_DIR} not found. Run generate_test_data.py first.")

    if RESUMES:
        MATCHER = SimpleResumeMatcher()
        MATCHER.index_resumes(RESUMES)
        print("Search index built successfully")


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


def filter_resumes(resumes: list, filters: dict) -> list:
    """Apply filters to resume list."""
    filtered = resumes

    # Filter by EHR system
    if filters.get("ehr_system"):
        ehr = filters["ehr_system"].lower()
        filtered = [
            r for r in filtered
            if r.get("primary_ehr_system", "").lower() == ehr
            or any(ehr in exp.get("ehr_systems", []) for exp in r.get("experience", []))
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
    ehr_systems = get_unique_values("primary_ehr_system", RESUMES)
    locations = sorted(set(
        r.get("personal_info", {}).get("location", "").split(",")[0].strip()
        for r in RESUMES
        if r.get("personal_info", {}).get("location")
    ))

    return render_template(
        "index.html",
        jobs=JOBS,
        ehr_systems=ehr_systems,
        locations=locations,
        resume_count=len(RESUMES),
        job_count=len(JOBS)
    )


@app.route("/search", methods=["GET", "POST"])
def search():
    """Search for matching candidates."""
    if request.method == "GET":
        return render_template("search.html", jobs=JOBS)

    # Get search parameters
    job_id = request.form.get("job_id")
    custom_query = request.form.get("custom_query", "").strip()
    top_k = int(request.form.get("top_k", 10))

    # Get filters
    filters = {
        "ehr_system": request.form.get("ehr_system"),
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
            message="No candidates match the selected filters"
        )

    # Create temporary matcher with filtered candidates
    temp_matcher = SimpleResumeMatcher()
    temp_matcher.index_resumes(candidates)

    # Run matching
    results = temp_matcher.match_job(job, top_k=min(top_k, len(candidates)))

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
        processing_time=results.processing_time_ms
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

    if not job_id:
        return jsonify({"error": "job_id required"}), 400

    job = next((j for j in JOBS if j.get("id") == job_id), None)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    candidates = filter_resumes(RESUMES, filters)

    if not candidates:
        return jsonify({"job": job, "matches": [], "message": "No candidates match filters"})

    temp_matcher = SimpleResumeMatcher()
    temp_matcher.index_resumes(candidates)
    results = temp_matcher.match_job(job, top_k=min(top_k, len(candidates)))

    return jsonify({
        "job": job,
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


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Healthcare Resume Matching - Web Interface")
    print("=" * 60)

    load_data()

    if not RESUMES:
        print("\nNo test data found. Generating...")
        import subprocess
        subprocess.run([sys.executable, str(BASE_DIR / "scripts" / "generate_test_data.py")])
        load_data()

    print(f"\nStarting web server...")
    print(f"Open http://localhost:5000 in your browser")
    print("=" * 60)

    app.run(debug=True, host="0.0.0.0", port=5000)
