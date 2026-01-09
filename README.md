# Healthcare Resume Matching System

A production-ready retrieval system for matching healthcare implementation professional resumes to EHR job descriptions. Built on a RAG (Retrieval-Augmented Generation) architecture.

## Features

- **Web Interface** - Search and filter candidates with a user-friendly UI
- **Resume-Job Matching** - TF-IDF + keyword scoring with explainable results
- **Filtering** - Filter by EHR system, experience, location, certifications
- **Test Data** - Generate realistic healthcare IT resumes and job descriptions

---

## Quick Start (Windows)

### Option A: Web Interface (Recommended)

```cmd
:: 1. Navigate to project folder
cd C:\path\to\RetrievalApp

:: 2. Install Flask
pip install flask

:: 3. Generate test data (100 resumes, 20 jobs)
python scripts\generate_test_data.py

:: 4. Start the web server
python web\app.py
```

**Open http://localhost:5000 in your browser**

### Option B: Command Line

```cmd
:: Generate data and run matching
python scripts\generate_test_data.py
python scripts\match_resumes.py
python scripts\view_results.py
```

---

## Web Interface

The web UI allows non-technical users to:

| Feature | Description |
|---------|-------------|
| **Search** | Select a job or enter custom keywords |
| **Filter** | EHR system, experience range, location, certifications |
| **Results** | Ranked candidates with match scores (0-100%) |
| **Explanations** | See WHY each candidate matched |
| **Profiles** | View full candidate resumes |

### Screenshots

After starting `python web\app.py`:

1. **Home Page** - Search form with job selection and filters
2. **Results Page** - Ranked candidates with match percentages
3. **Candidate Page** - Full resume with experience, skills, certifications
4. **Job Page** - Complete job requirements

---

## Test Data

Generate realistic healthcare IT test data:

```cmd
:: Default: 100 resumes, 20 jobs
python scripts\generate_test_data.py

:: Custom amounts
python scripts\generate_test_data.py --resumes 500 --jobs 100
```

### Resume Data Includes:
- Names, contact info, locations
- EHR systems (Epic, Cerner, MEDITECH, athenahealth, Allscripts)
- Modules (EpicCare Ambulatory, Cadence, PowerChart, etc.)
- Certifications (Epic Certified, PMP, CPHIMS, etc.)
- Work history with achievements
- Education and skills

### Job Data Includes:
- Full-time and part-time positions
- Contract and permanent roles
- Remote, hybrid, on-site options
- Required qualifications and certifications
- Salary ranges

---

## How Matching Works

Candidates are scored using a weighted combination:

| Component | Weight | Description |
|-----------|--------|-------------|
| EHR System Match | 30% | Primary EHR system alignment |
| Module Experience | 20% | Specific module knowledge |
| Years Experience | 15% | Meets minimum requirements |
| Certifications | 15% | Required certifications held |
| Skills Overlap | 20% | Matching technical skills |

Results include explanations:
```
#1: Jonathan Allen - 51.3% Match
    ✓ Primary EHR match: Epic
    ✓ Module matches: 2/3
    ✓ Experience: 15 years (required: 2+)
    ✓ Required certifications: 1/1
```

---

## API Endpoints

For programmatic access:

```
GET  /api/resumes     - List all candidates
GET  /api/jobs        - List all jobs
POST /api/search      - Search with filters (JSON body)
```

Example API search:
```cmd
curl -X POST http://localhost:5000/api/search ^
  -H "Content-Type: application/json" ^
  -d "{\"job_id\": \"job_001\", \"top_k\": 10}"
```

---

## Project Structure

```
RetrievalApp\
├── web\
│   ├── app.py                 # Flask web application
│   └── templates\             # HTML templates
├── scripts\
│   ├── generate_test_data.py  # Create test resumes/jobs
│   ├── match_resumes.py       # CLI matching script
│   ├── view_results.py        # View results
│   └── run_all.py             # One-command runner
├── test_data\                 # Generated test data
│   ├── resumes\               # JSON resume files
│   └── job_descriptions\      # JSON job files
├── results\                   # Matching results
├── docs\
│   └── DESIGN.md              # Architecture documentation
├── QUICKSTART.md              # Detailed setup guide
└── README.md                  # This file
```

---

## Configuration

Edit `scripts\match_resumes.py` to adjust:

```python
TOP_K = 10              # Number of top candidates per job
SEMANTIC_WEIGHT = 0.7   # Weight for TF-IDF similarity
LEXICAL_WEIGHT = 0.3    # Weight for keyword matching
```

---

## Troubleshooting

**'python' is not recognized**
```cmd
py scripts\generate_test_data.py
py web\app.py
```

**ImportError: No module named 'flask'**
```cmd
pip install flask
```

**Port 5000 already in use**
- Edit `web\app.py` and change `port=5000` to `port=8080`

---

## Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - Step-by-step setup guide
- **[docs/DESIGN.md](docs/DESIGN.md)** - Architecture and design decisions

---

## License

MIT
