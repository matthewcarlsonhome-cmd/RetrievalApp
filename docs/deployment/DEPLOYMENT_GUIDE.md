# Knowledge Expert - Deployment Guide

## Overview

This guide covers deploying the Knowledge Expert AI-powered Q&A system to Render.

## Prerequisites

1. **GitHub Account** - Your code must be in a GitHub repository
2. **Render Account** - Sign up at [render.com](https://render.com)
3. **Anthropic API Key** - Get one at [console.anthropic.com](https://console.anthropic.com)

## Quick Start (Recommended)

### Step 1: Push Code to GitHub

```bash
git add .
git commit -m "Add Knowledge Expert system"
git push origin main
```

### Step 2: Create Render Service

1. Log in to [Render Dashboard](https://dashboard.render.com)
2. Click **New +** → **Blueprint**
3. Connect your GitHub repository
4. Select `render.yaml` as the blueprint file
5. Click **Apply**

### Step 3: Configure Environment Variables

In Render Dashboard, go to your service and add:

| Variable | Value | Description |
|----------|-------|-------------|
| `ANTHROPIC_API_KEY` | `sk-ant-...` | Your Claude API key |

### Step 4: Deploy

Render will automatically deploy when you push to GitHub.

Your app will be available at: `https://knowledge-expert.onrender.com`

---

## Manual Deployment (Alternative)

If you prefer not to use Blueprints:

### Step 1: Create Web Service

1. Go to Render Dashboard → **New +** → **Web Service**
2. Connect your GitHub repository
3. Configure:
   - **Name**: `knowledge-expert`
   - **Runtime**: Python
   - **Plan**: Starter ($7/mo)
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn knowledge_expert.app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120`

### Step 2: Add Disk Storage

1. Go to service settings → **Disks**
2. Add disk:
   - **Name**: `knowledge-data`
   - **Mount Path**: `/data`
   - **Size**: 1 GB

### Step 3: Set Environment Variables

Add these in **Environment** settings:

```
FLASK_ENV=production
SECRET_KEY=<generate-random-string>
ANTHROPIC_API_KEY=<your-api-key>
```

---

## Post-Deployment Setup

### 1. Seed Initial Data

SSH into your service or use the Shell feature:

```bash
python -m knowledge_expert.scripts.seed_data
```

This loads:
- Sample documents about Matthew Carlson Consulting
- 20 pre-configured Q&A pairs

### 2. Upload Your Documents

1. Go to `https://your-app.onrender.com/upload`
2. Drag and drop your company documents
3. Supported formats: PDF, DOCX, MD, TXT, HTML

### 3. Add Custom Q&A Pairs

1. Go to `https://your-app.onrender.com/qa`
2. Add question-answer pairs for common queries
3. These provide instant, accurate responses

### 4. Test the Chat

1. Go to `https://your-app.onrender.com`
2. Ask questions about your business
3. Check that responses are accurate and cite sources

---

## Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | Required | Claude API key |
| `OPENAI_API_KEY` | Optional | OpenAI fallback |
| `SECRET_KEY` | Auto-generated | Flask session key |
| `FLASK_ENV` | production | Environment mode |
| `LLM_MODEL` | claude-3-sonnet-20240229 | Claude model to use |
| `MAX_TOKENS` | 1000 | Max response tokens |
| `TEMPERATURE` | 0.3 | LLM temperature |

### Scaling

For higher traffic:

| Plan | RAM | Workers | Concurrent Users |
|------|-----|---------|------------------|
| Starter ($7) | 1GB | 2 | ~10-20 |
| Standard ($25) | 2GB | 4 | ~50-100 |
| Pro ($85) | 4GB | 8 | ~200+ |

---

## Monitoring

### Health Check

The app exposes `/api/health` for monitoring:

```bash
curl https://your-app.onrender.com/api/health
```

### Statistics

View system stats at:
- Dashboard: `https://your-app.onrender.com/admin`
- API: `https://your-app.onrender.com/api/stats`

### Logs

Access logs in Render Dashboard → Your Service → **Logs**

---

## Troubleshooting

### App Won't Start

**Symptom**: Deploy fails or app crashes on startup

**Solutions**:
1. Check you're using Starter plan ($7/mo) - free tier has insufficient memory
2. Verify `ANTHROPIC_API_KEY` is set
3. Check logs for specific error messages

### Embeddings Not Working

**Symptom**: Search returns no results or errors

**Solutions**:
1. Ensure disk storage is mounted at `/data`
2. Run seed script: `python -m knowledge_expert.scripts.seed_data`
3. Check memory usage - may need to upgrade plan

### Slow Responses

**Symptom**: Chat takes 10+ seconds to respond

**Solutions**:
1. First query loads ML models (~30 seconds) - subsequent queries are faster
2. Upgrade plan for more workers
3. Check Claude API status at status.anthropic.com

### Documents Not Processing

**Symptom**: Upload succeeds but document not searchable

**Solutions**:
1. Check document format is supported
2. Verify file isn't empty or corrupted
3. Check logs for parsing errors

---

## Security Best Practices

1. **API Keys**: Never commit API keys to Git. Always use environment variables.

2. **Content Moderation**: The system includes built-in content filtering. Review and customize `knowledge_expert/config.py` for your needs.

3. **Access Control**: For production, consider adding authentication:
   ```python
   # Add to app.py
   @app.before_request
   def require_auth():
       # Add your auth logic
       pass
   ```

4. **Rate Limiting**: Consider adding rate limiting for production:
   ```bash
   pip install flask-limiter
   ```

---

## Cost Estimation

### Render Hosting

| Component | Cost/Month |
|-----------|------------|
| Starter Plan | $7 |
| 1GB Disk | $0.25 |
| **Total** | **~$7.25** |

### Claude API

| Usage | Cost |
|-------|------|
| 1,000 queries/month | ~$3-5 |
| 10,000 queries/month | ~$30-50 |

Estimate: $10-15/month for a small business with moderate usage.

---

## Support

- **Documentation**: This guide and files in `docs/`
- **Issues**: Open an issue on GitHub
- **Contact**: matthewcarlsonconsulting.com
