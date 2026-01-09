# Quick Start Guide - Healthcare Resume Matching System

Get the system running in under 10 minutes.

## Prerequisites

- Python 3.9+ (download from https://python.org)
- pip (included with Python)
- Windows Command Prompt

---

## Option A: Web Interface (Recommended for Non-Technical Users)

### Step 1: Open Command Prompt and Navigate to Project

```cmd
cd C:\path\to\RetrievalApp
```

### Step 2: Install Flask

```cmd
pip install flask
```

### Step 3: Generate Test Data

```cmd
python scripts\generate_test_data.py
```

### Step 4: Start the Web Application

```cmd
python web\app.py
```

### Step 5: Open in Browser

Navigate to: **http://localhost:5000**

You can now:
- Search candidates by selecting a job or entering keywords
- Filter by EHR system, experience years, location, certifications
- View ranked results with match scores and explanations
- Click on candidates to see full profiles

---

## Option B: Command Line Scripts

### Step 1: Open Command Prompt and Navigate to Project

```cmd
cd C:\path\to\RetrievalApp
```

### Step 2: Install Dependencies

```cmd
pip install -e .
```

Or install core dependencies directly:

```cmd
pip install numpy
```

### Step 3: Generate Test Data

```cmd
python scripts\generate_test_data.py
```

This creates:
- `test_data\resumes\` - 100 healthcare implementation resumes
- `test_data\job_descriptions\` - 20 EHR/hospital implementation jobs

### Step 4: Run Resume Matching

```cmd
python scripts\match_resumes.py
```

This will:
1. Load all resumes and job descriptions
2. Build the retrieval index
3. Match each job to top candidate resumes
4. Output results to `results\matches.json`

### Step 5: View Results

```cmd
python scripts\view_results.py
```

Or check results directly:
```cmd
type results\matches.json
```

---

## One-Command Quick Start (CLI)

Run everything at once:

```cmd
python scripts\run_all.py
```

---

## Directory Structure After Setup

```
RetrievalApp\
├── test_data\
│   ├── resumes\              # 100 JSON resume files
│   │   ├── resume_001.json
│   │   └── ...
│   └── job_descriptions\     # 20 JSON job files
│       ├── job_001.json
│       └── ...
├── results\
│   └── matches.json          # Matching results
├── scripts\
│   ├── generate_test_data.py
│   ├── match_resumes.py
│   ├── view_results.py
│   └── run_all.py
└── web\
    └── app.py                # Web interface
```

---

## Customization

### Adjust Matching Parameters

Edit `scripts\match_resumes.py`:

```python
# Number of top candidates per job
TOP_K = 10

# Hybrid search weights (semantic vs keyword)
SEMANTIC_WEIGHT = 0.7
LEXICAL_WEIGHT = 0.3
```

### Generate More Test Data

```cmd
python scripts\generate_test_data.py --resumes 200 --jobs 50
```

---

## Troubleshooting

**'python' is not recognized as an internal or external command**
- Make sure Python is installed and added to PATH
- Try using `py` instead of `python`

**ImportError: No module named 'flask'**
```cmd
pip install flask
```

**Port 5000 already in use**
- Close other applications using port 5000, or
- Edit `web\app.py` and change `port=5000` to another port (e.g., `port=8080`)

**Memory issues with large datasets**
```cmd
set EMBEDDING_MODEL=all-MiniLM-L6-v2
python scripts\match_resumes.py
```

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

Results saved to: results\matches.json
Total time: 45 seconds
```

---

## Web Interface Screenshots

After starting the web app, you'll see:

1. **Home Page**: Search form with job selection and filters
2. **Results Page**: Ranked candidates with match percentages
3. **Candidate Page**: Full resume with experience, skills, certifications
4. **Job Page**: Complete job requirements and responsibilities
