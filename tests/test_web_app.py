"""
Tests for the web application.
"""

import pytest
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def app():
    """Create test Flask app."""
    from web.app import app, load_data, RESUMES, JOBS

    app.config['TESTING'] = True

    # Load data if not already loaded
    if not RESUMES:
        load_data()

    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


class TestHealthEndpoints:
    """Tests for health/status endpoints."""

    def test_index_loads(self, client):
        """Test that index page loads."""
        response = client.get('/')
        assert response.status_code == 200
        assert b'Healthcare Resume Matching' in response.data or b'Search' in response.data

    def test_api_status(self, client):
        """Test API status endpoint."""
        response = client.get('/api/status')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'resumes_loaded' in data
        assert 'jobs_loaded' in data
        assert 'matching_modes' in data


class TestAPIEndpoints:
    """Tests for API endpoints."""

    def test_api_resumes(self, client):
        """Test resumes API endpoint."""
        response = client.get('/api/resumes')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'count' in data
        assert 'resumes' in data
        assert isinstance(data['resumes'], list)

    def test_api_jobs(self, client):
        """Test jobs API endpoint."""
        response = client.get('/api/jobs')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'count' in data
        assert 'jobs' in data
        assert isinstance(data['jobs'], list)

    def test_api_search_requires_job_id(self, client):
        """Test that API search requires job_id."""
        response = client.post('/api/search',
                               json={},
                               content_type='application/json')
        assert response.status_code == 400

        data = json.loads(response.data)
        assert 'error' in data

    def test_api_search_with_invalid_job(self, client):
        """Test API search with invalid job ID."""
        response = client.post('/api/search',
                               json={'job_id': 'nonexistent_job'},
                               content_type='application/json')
        assert response.status_code == 404


class TestSearchFlow:
    """Tests for the search flow."""

    def test_search_page_loads(self, client):
        """Test that search page loads."""
        response = client.get('/search')
        assert response.status_code == 200

    def test_search_with_job_id(self, client):
        """Test search with a job ID."""
        # First get a valid job ID
        jobs_response = client.get('/api/jobs')
        jobs = json.loads(jobs_response.data)['jobs']

        if not jobs:
            pytest.skip("No jobs available for testing")

        job_id = jobs[0]['id']

        response = client.post('/search',
                               data={'job_id': job_id, 'top_k': '5'},
                               follow_redirects=True)
        assert response.status_code == 200

    def test_search_with_custom_query(self, client):
        """Test search with custom query."""
        response = client.post('/search',
                               data={
                                   'custom_query': 'Epic implementation consultant',
                                   'top_k': '5'
                               },
                               follow_redirects=True)
        assert response.status_code == 200

    def test_search_empty_returns_error(self, client):
        """Test that empty search returns error."""
        response = client.post('/search',
                               data={},
                               follow_redirects=True)
        # Should show error page or redirect
        assert response.status_code == 200
        assert b'error' in response.data.lower() or b'select' in response.data.lower()


class TestCandidateAndJobPages:
    """Tests for candidate and job detail pages."""

    def test_candidate_page(self, client):
        """Test candidate detail page."""
        # First get a valid resume ID
        resumes_response = client.get('/api/resumes')
        resumes = json.loads(resumes_response.data)['resumes']

        if not resumes:
            pytest.skip("No resumes available for testing")

        resume_id = resumes[0]['id']
        response = client.get(f'/candidate/{resume_id}')
        assert response.status_code == 200

    def test_candidate_not_found(self, client):
        """Test candidate not found."""
        response = client.get('/candidate/nonexistent_id')
        assert response.status_code == 200
        assert b'not found' in response.data.lower() or b'error' in response.data.lower()

    def test_job_page(self, client):
        """Test job detail page."""
        # First get a valid job ID
        jobs_response = client.get('/api/jobs')
        jobs = json.loads(jobs_response.data)['jobs']

        if not jobs:
            pytest.skip("No jobs available for testing")

        job_id = jobs[0]['id']
        response = client.get(f'/job/{job_id}')
        assert response.status_code == 200

    def test_job_not_found(self, client):
        """Test job not found."""
        response = client.get('/job/nonexistent_id')
        assert response.status_code == 200
        assert b'not found' in response.data.lower() or b'error' in response.data.lower()


class TestFilters:
    """Tests for search filters."""

    def test_ehr_filter(self, client):
        """Test EHR system filter."""
        jobs_response = client.get('/api/jobs')
        jobs = json.loads(jobs_response.data)['jobs']

        if not jobs:
            pytest.skip("No jobs available for testing")

        response = client.post('/search',
                               data={
                                   'job_id': jobs[0]['id'],
                                   'ehr_system': 'Epic',
                                   'top_k': '5'
                               },
                               follow_redirects=True)
        assert response.status_code == 200

    def test_experience_filter(self, client):
        """Test experience filter."""
        jobs_response = client.get('/api/jobs')
        jobs = json.loads(jobs_response.data)['jobs']

        if not jobs:
            pytest.skip("No jobs available for testing")

        response = client.post('/search',
                               data={
                                   'job_id': jobs[0]['id'],
                                   'min_experience': '5',
                                   'top_k': '5'
                               },
                               follow_redirects=True)
        assert response.status_code == 200


class TestErrorHandling:
    """Tests for error handling."""

    def test_invalid_json_body(self, client):
        """Test handling of invalid JSON in API."""
        response = client.post('/api/search',
                               data='not json',
                               content_type='application/json')
        # Should handle gracefully
        assert response.status_code in [400, 415, 500]

    def test_missing_content_type(self, client):
        """Test API without content type."""
        response = client.post('/api/search', data='{}')
        # Should handle gracefully
        assert response.status_code in [400, 415, 200]
