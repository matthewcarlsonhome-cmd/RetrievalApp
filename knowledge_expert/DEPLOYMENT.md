# Knowledge Expert - Deployment & Configuration Guide

## Overview

Knowledge Expert is a RAG (Retrieval-Augmented Generation) powered Q&A system that allows you to:
- Upload documents (PDF, DOCX, MD, TXT, HTML)
- Add direct Q&A pairs
- Answer user questions using AI with your knowledge base

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Web Frontend  │────▶│   Flask API     │────▶│   Claude API    │
│   (HTML/JS)     │     │   (Python)      │     │   (Anthropic)   │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
              ┌──────────┐ ┌──────────┐ ┌──────────┐
              │ ChromaDB │ │  SQLite  │ │  Uploads │
              │ (Vectors)│ │(Metadata)│ │  (Files) │
              └──────────┘ └──────────┘ └──────────┘
                    │            │            │
                    └────────────┴────────────┘
                                 │
                         /data (Persistent Disk)
```

### Components

1. **ChromaDB** - Embedded vector database storing document embeddings at `/data/chroma_db/`
2. **SQLite** - Stores document metadata, Q&A pairs, and query history at `/data/knowledge_expert.db`
3. **Uploads** - Original uploaded files stored at `/data/uploads/`
4. **sentence-transformers** - Uses `all-MiniLM-L6-v2` model for 384-dimensional embeddings

## Render Deployment

### Prerequisites

1. A Render account (Professional plan recommended for persistent storage)
2. An Anthropic API key from [console.anthropic.com](https://console.anthropic.com)

### Setup Steps

1. **Create a New Web Service**
   - Connect your GitHub repository
   - Select the branch with the code
   - Render will auto-detect the `render.yaml` configuration

2. **Add Environment Variables**
   ```
   ANTHROPIC_API_KEY=sk-ant-your-key-here
   SECRET_KEY=your-random-secret-key-here
   ```

3. **Configure Persistent Disk** (Professional Plan)
   - Name: `knowledge-data`
   - Mount Path: `/data`
   - Size: 1GB (or more as needed)

4. **Deploy**
   - Render will automatically build and deploy

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | Yes | - | Your Claude API key |
| `SECRET_KEY` | Yes | - | Flask session secret key |
| `OPENAI_API_KEY` | No | - | Fallback if Claude unavailable |
| `DATA_DIR` | No | `/data` | Base directory for all data |
| `LLM_MODEL` | No | `claude-sonnet-4-20250514` | Claude model to use |
| `MAX_TOKENS` | No | `1024` | Max response tokens |
| `TEMPERATURE` | No | `0.1` | LLM temperature (0-1) |
| `SKIP_ML_MODELS` | No | `false` | Set to `true` to disable embeddings (text search only) |

## How It Works

### Document Processing Pipeline

1. **Upload**: User uploads a document via the web interface
2. **Parse**: Text is extracted based on file type (PDF, DOCX, etc.)
3. **Chunk**: Text is split into ~500 token chunks with 50 token overlap
4. **Embed**: Each chunk is converted to a 384-dimensional vector
5. **Store**: Vectors go to ChromaDB, metadata to SQLite

### Query Processing

1. **User Query**: User asks a question in the chat interface
2. **Moderation**: Query is checked against blocked words/topics
3. **Search**: Hybrid search combines:
   - 70% Semantic search (vector similarity)
   - 20% Keyword search (BM25-style)
   - 10% Direct Q&A matching
4. **Retrieve**: Top 5 most relevant chunks are retrieved
5. **Generate**: Claude generates a response using the retrieved context
6. **Response**: Answer is returned with source citations

### Chunking Strategy

- **Target size**: 500 tokens per chunk
- **Overlap**: 50 tokens between chunks
- **Boundaries**: Respects sentence boundaries when possible
- **Sections**: Preserves section titles from markdown headers

## Admin Guide

### Accessing the Admin Panel

Navigate to `/admin` to view:
- Total documents, chunks, queries
- Feedback statistics (positive/negative)
- System health status

### Managing Documents

**Upload Page** (`/upload`):
1. Click "Choose File" or drag-and-drop
2. Select supported file types: PDF, DOCX, MD, TXT, HTML
3. Click "Upload Document"
4. Document will be processed and indexed automatically

**Viewing Documents**:
- The upload page shows all indexed documents
- Each document shows chunk count and upload date
- Click "Delete" to remove a document and its chunks

### Managing Q&A Pairs

**Q&A Page** (`/qa`):
1. Enter the question in the first field
2. Enter the answer in the second field
3. Optionally select a category
4. Click "Add Q&A Pair"

Direct Q&A pairs are:
- Matched against user queries with high priority
- Useful for common questions with specific answers
- Great for FAQs, pricing, contact info

### Content Moderation

The system automatically filters:
- Competitor mentions
- Inappropriate content
- Off-topic queries

To customize moderation rules, edit `knowledge_expert/config.py`:
```python
@dataclass
class ContentModeration:
    BLOCKED_WORDS: List[str] = field(default_factory=lambda: [
        "competitor1", "competitor2", ...
    ])
    BLOCKED_TOPICS: List[str] = field(default_factory=lambda: [
        "illegal", "harmful", ...
    ])
```

## Troubleshooting

### Common Issues

**"Sorry, there was a network error"**
- Check that `ANTHROPIC_API_KEY` is set correctly
- Verify you have API credits available
- Check Render logs for specific errors

**Documents not appearing in list**
- Refresh the page after upload
- Check Render logs for parsing errors
- Verify file type is supported

**Q&A pairs not showing**
- Refresh the page after adding
- Check browser console for JavaScript errors
- Verify the POST request returned 200

**Out of memory errors**
- Upgrade to Render Professional plan
- Or set `SKIP_ML_MODELS=true` (disables semantic search)

### Checking Logs

In Render dashboard:
1. Go to your service
2. Click "Logs" tab
3. Look for:
   - `Collection 'knowledge_chunks' ready with X documents` - ChromaDB status
   - `Error processing document` - Upload issues
   - `Query error` - API or search issues

### Data Locations

On Render with persistent disk at `/data`:
- ChromaDB: `/data/chroma_db/`
- SQLite: `/data/knowledge_expert.db`
- Uploads: `/data/uploads/`

## API Reference

### POST /api/query
Ask a question.

```json
Request:
{
  "query": "What services do you offer?"
}

Response:
{
  "answer": "We offer consulting services including...",
  "sources": [
    {
      "title": "Services Overview",
      "section": "Core Services",
      "score": 0.85
    }
  ],
  "query_id": "uuid-here"
}
```

### POST /api/upload
Upload a document.

```
Content-Type: multipart/form-data
file: <binary file data>
```

### GET /api/documents
List all documents.

### DELETE /api/documents/<id>
Delete a document.

### POST /api/qa
Add a Q&A pair.

```json
{
  "question": "What is your pricing?",
  "answer": "Our hourly rate is $150/hour.",
  "category": "Pricing"
}
```

### GET /api/qa
List all Q&A pairs.

### GET /api/stats
Get system statistics.

## Security Considerations

1. **API Key Protection**: Never expose `ANTHROPIC_API_KEY` in client-side code
2. **File Uploads**: Only allow trusted file types; files are validated server-side
3. **Input Sanitization**: All user inputs are sanitized before processing
4. **Rate Limiting**: Consider adding rate limiting for production use

## Maintenance

### Backup

To backup your data, download these from Render's shell:
```bash
# Connect to Render shell
# Download these files:
/data/knowledge_expert.db  # SQLite database
/data/chroma_db/           # Vector database directory
```

### Updating

1. Push changes to your GitHub branch
2. Render will automatically redeploy
3. Persistent disk data is preserved across deployments

### Monitoring

Check these metrics regularly:
- Query response times
- Feedback ratio (positive/negative)
- Storage usage on persistent disk
- API usage (Anthropic console)
