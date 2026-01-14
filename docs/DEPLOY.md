# Deployment Guide

This guide covers deploying the Resume Matching application to Render.com (free tier).

## Quick Deploy to Render (Recommended)

### Option 1: One-Click Deploy

1. Push your code to GitHub
2. Click the button below (or visit [Render Dashboard](https://dashboard.render.com))

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

3. Connect your GitHub repository
4. Render will automatically detect the `render.yaml` and configure everything

### Option 2: Manual Setup

1. **Create a Render Account**
   - Go to [render.com](https://render.com) and sign up (free)
   - Connect your GitHub account

2. **Create New Web Service**
   - Click "New" → "Web Service"
   - Connect your GitHub repository
   - Configure:
     - **Name**: `resume-matching-app` (or your choice)
     - **Runtime**: Python
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `gunicorn --chdir web app:app --bind 0.0.0.0:$PORT`
     - **Plan**: Free

3. **Deploy**
   - Click "Create Web Service"
   - Wait 2-3 minutes for the build to complete
   - Your app will be live at `https://your-app-name.onrender.com`

## What Gets Deployed

```
RetrievalApp/
├── web/
│   ├── app.py              # Flask application
│   └── templates/          # HTML templates
├── scripts/
│   ├── match_resumes.py    # Matching engine
│   └── generate_test_data.py
├── test_data/              # Sample resumes and jobs
├── requirements.txt        # Python dependencies
└── render.yaml            # Render configuration
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | 5000 | Server port (set automatically by Render) |
| `FLASK_ENV` | production | Flask environment |
| `FLASK_DEBUG` | 0 | Debug mode (0=off, 1=on) |

## Endpoints

Once deployed, your app will have these endpoints:

| Endpoint | Description |
|----------|-------------|
| `/` | Main web interface |
| `/health` | Health check (used by Render) |
| `/api/status` | System status JSON |
| `/api/resumes` | List all resumes |
| `/api/jobs` | List all jobs |
| `/api/match` | Match resumes to jobs (POST) |

## Free Tier Limitations

Render's free tier includes:
- **750 hours/month** of runtime
- **Auto-sleep after 15 min inactivity** (first request after sleep takes ~30s)
- **Automatic HTTPS**
- **Custom domains** (optional)

### Keeping the App Awake

To prevent the app from sleeping, you can:
1. Use a service like [UptimeRobot](https://uptimerobot.com) to ping `/health` every 10 minutes
2. Upgrade to Render's paid tier ($7/month)

## Troubleshooting

### Build Fails

Check the build logs in Render dashboard. Common issues:
- Missing dependencies in `requirements.txt`
- Python version mismatch

### App Crashes on Start

Check the service logs. Common issues:
- Port binding (make sure to use `$PORT` environment variable)
- Import errors (check Python path configuration)

### No Data Showing

The app automatically loads test data from `test_data/` on startup. If the directory is empty:
1. Generate test data locally: `python scripts/generate_test_data.py`
2. Commit and push to trigger a redeploy

## Local Development

To run locally before deploying:

```bash
# Install dependencies
pip install -r requirements.txt

# Run the Flask development server
python web/app.py

# Or use gunicorn (same as production)
gunicorn --chdir web app:app --bind 0.0.0.0:5000
```

Open http://localhost:5000 in your browser.

## Enabling Neural Matching (Optional)

By default, only TF-IDF matching is enabled (fast, lightweight). To enable neural semantic matching:

1. Edit `requirements.txt` and uncomment:
   ```
   sentence-transformers>=2.2.0
   torch>=2.0.0
   ```

2. Commit and push to trigger a redeploy

**Warning**: This significantly increases:
- Build time (5-10 minutes)
- Memory usage (~1GB+)
- Startup time (30-60 seconds to load model)

The free tier should still work, but the app will be slower to start.

## Updating the App

Any push to your GitHub repository will automatically trigger a redeploy on Render.

```bash
# Make changes
git add .
git commit -m "Update feature"
git push origin main
```

Render will automatically detect the push and rebuild your app.
