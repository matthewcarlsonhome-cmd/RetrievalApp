# Quick Start Guide - Healthcare Resume Matching System

Get the system running in under 10 minutes.

## Prerequisites

- Python 3.9+
- pip

---

## Option A: Web Interface (Recommended for Non-Technical Users)

### Step 1: Install Dependencies

```bash
cd /home/user/RetrievalApp
pip install flask
```

### Step 2: Generate Test Data

```bash
python scripts/generate_test_data.py
```

### Step 3: Start the Web Application

```bash
python web/app.py
```

### Step 4: Open in Browser

Navigate to: **http://localhost:5000**

You can now:
- Search candidates by selecting a job or entering keywords
- Filter by EHR system, experience years, location, certifications
- View ranked results with match scores and explanations
- Click on candidates to see full profiles

---

## Option B: Command Line Scripts

### Step 1: Install Dependencies

```bash
cd /home/user/RetrievalApp
pip install -e .
```

Or install core dependencies directly:

```bash
pip install numpy
```

### Step 2: Generate Test Data

```bash
python scripts/generate_test_data.py
```

This creates:
- `test_data/resumes/` - 100 healthcare implementation resumes
- `test_data/job_descriptions/` - 20 EHR/hospital implementation jobs

### Step 3: Run Resume Matching

```bash
python scripts/match_resumes.py
```

This will:
1. Load all resumes and job descriptions
2. Build the retrieval index
3. Match each job to top candidate resumes
4. Output results to `results/matches.json`

### Step 4: View Results

```bash
python scripts/view_results.py
```

Or check results directly:
```bash
cat results/matches.json | python -m json.tool | head -100
```

---

## One-Command Quick Start (CLI)

Run everything at once:

```bash
python scripts/run_all.py
```

---

## Directory Structure After Setup

```
RetrievalApp/
├── test_data/
│   ├── resumes/           # 100 JSON resume files
│   │   ├── resume_001.json
│   │   └── ...
│   └── job_descriptions/  # 20 JSON job files
│       ├── job_001.json
│       └── ...
├── results/
│   └── matches.json       # Matching results
└── scripts/
    ├── generate_test_data.py
    ├── match_resumes.py
    ├── view_results.py
    └── run_all.py
```

---

## Customization

### Adjust Matching Parameters

Edit `scripts/match_resumes.py`:

```python
# Number of top candidates per job
TOP_K = 10

# Hybrid search weights (semantic vs keyword)
SEMANTIC_WEIGHT = 0.7
LEXICAL_WEIGHT = 0.3
```

### Generate More Test Data

```bash
python scripts/generate_test_data.py --resumes 200 --jobs 50
```

---

## Troubleshooting

**ImportError: No module named 'sentence_transformers'**
```bash
pip install sentence-transformers
```

**Memory issues with large datasets**
```bash
# Use smaller embedding model
export EMBEDDING_MODEL=all-MiniLM-L6-v2
```

**Slow first run**
- First run downloads embedding model (~90MB)
- Subsequent runs use cached model

---

## Expected Output

```
=== Healthcare Resume Matching System ===

Loading 100 resumes...
Loading 20 job descriptions...
Building search index...

Matching Job: Senior EHR Implementation Consultant
  #1: John Smith (Score: 0.89) - 8 yrs Epic experience
  #2: Sarah Johnson (Score: 0.85) - 6 yrs Cerner experience
  #3: Michael Chen (Score: 0.82) - 7 yrs healthcare IT
  ...

Results saved to: results/matches.json
Total time: 45 seconds
```
