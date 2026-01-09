"""
Pytest configuration and shared fixtures.
"""

import json
import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def sample_resume():
    """Sample resume for testing."""
    return {
        "id": "test_resume_001",
        "personal_info": {
            "name": "John Smith",
            "location": "Boston, MA"
        },
        "summary": "Experienced Epic consultant with 8 years in healthcare IT implementation.",
        "years_experience": 8,
        "primary_ehr_system": "Epic",
        "experience": [
            {
                "title": "Senior Epic Consultant",
                "employer": "Healthcare Partners",
                "ehr_systems": ["Epic"],
                "modules": ["EpicCare Ambulatory", "Cadence", "MyChart"],
                "achievements": [
                    "Led implementation for 500-bed hospital",
                    "Reduced patient wait times by 25%"
                ]
            }
        ],
        "education": [
            {"degree": "BS Computer Science", "institution": "MIT"}
        ],
        "certifications": [
            "Epic Certified - EpicCare Ambulatory",
            "PMP"
        ],
        "skills": [
            "Epic", "Healthcare IT", "Project Management", "SQL", "Training"
        ]
    }


@pytest.fixture
def sample_job():
    """Sample job description for testing."""
    return {
        "id": "test_job_001",
        "title": "Senior Epic Implementation Consultant",
        "employer": "Regional Medical Center",
        "description": "Looking for experienced Epic consultant to lead ambulatory implementation.",
        "primary_ehr_system": "Epic",
        "modules": ["EpicCare Ambulatory", "MyChart", "Cadence"],
        "experience_required": {"min_years": 5},
        "required_qualifications": {
            "skills": ["Epic", "Healthcare IT", "Project Management"],
            "certifications": ["Epic Certified - EpicCare Ambulatory"]
        },
        "preferred_qualifications": {
            "skills": ["SQL", "Training"],
            "certifications": ["PMP"]
        }
    }


@pytest.fixture
def sample_resumes(sample_resume):
    """List of sample resumes for testing."""
    resumes = [sample_resume]

    # Add a few more varied resumes
    resumes.append({
        "id": "test_resume_002",
        "personal_info": {"name": "Jane Doe", "location": "Chicago, IL"},
        "summary": "Cerner specialist with revenue cycle expertise.",
        "years_experience": 5,
        "primary_ehr_system": "Cerner",
        "experience": [
            {
                "title": "Cerner Analyst",
                "employer": "Midwest Health",
                "ehr_systems": ["Cerner"],
                "modules": ["Revenue Cycle", "Scheduling"],
                "achievements": ["Improved billing accuracy by 30%"]
            }
        ],
        "education": [{"degree": "MBA", "institution": "Northwestern"}],
        "certifications": ["Cerner Certified"],
        "skills": ["Cerner", "Revenue Cycle", "Analytics"]
    })

    resumes.append({
        "id": "test_resume_003",
        "personal_info": {"name": "Bob Wilson", "location": "Houston, TX"},
        "summary": "Epic ambulatory expert with extensive experience.",
        "years_experience": 10,
        "primary_ehr_system": "Epic",
        "experience": [
            {
                "title": "Epic Principal Consultant",
                "employer": "Epic Systems",
                "ehr_systems": ["Epic"],
                "modules": ["EpicCare Ambulatory", "Cadence", "MyChart", "Willow"],
                "achievements": ["Trained 200+ end users"]
            }
        ],
        "education": [{"degree": "MS Healthcare Informatics", "institution": "UT Austin"}],
        "certifications": ["Epic Certified - EpicCare Ambulatory", "Epic Certified - Cadence"],
        "skills": ["Epic", "Training", "Healthcare IT", "SQL", "Project Management"]
    })

    return resumes


@pytest.fixture
def test_data_dir(tmp_path):
    """Create temporary test data directory."""
    resumes_dir = tmp_path / "resumes"
    jobs_dir = tmp_path / "job_descriptions"
    resumes_dir.mkdir()
    jobs_dir.mkdir()
    return tmp_path


@pytest.fixture
def populated_test_data(test_data_dir, sample_resumes, sample_job):
    """Create test data directory with sample files."""
    resumes_dir = test_data_dir / "resumes"
    jobs_dir = test_data_dir / "job_descriptions"

    for i, resume in enumerate(sample_resumes):
        with open(resumes_dir / f"resume_{i+1:03d}.json", "w") as f:
            json.dump(resume, f)

    with open(jobs_dir / "job_001.json", "w") as f:
        json.dump(sample_job, f)

    return test_data_dir
