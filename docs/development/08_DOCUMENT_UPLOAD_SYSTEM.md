# Document Upload & Management System

## Overview

This document specifies a user-friendly document upload system that allows non-technical users to add, update, and manage knowledge base content. Documents are automatically processed (parsed, chunked, embedded) and become searchable immediately.

---

## User Experience

### Upload Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DOCUMENT UPLOAD EXPERIENCE                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     KNOWLEDGE MANAGEMENT                             │   │
│  │                                                                       │   │
│  │  ┌─────────────────────────────────────────────────────────────┐    │   │
│  │  │                                                              │    │   │
│  │  │     ┌──────────────────────────────────────────────────┐    │    │   │
│  │  │     │                                                   │    │    │   │
│  │  │     │        📄  Drag & drop files here                │    │    │   │
│  │  │     │            or click to browse                     │    │    │   │
│  │  │     │                                                   │    │    │   │
│  │  │     │     Supported: PDF, DOCX, MD, HTML, TXT, CSV     │    │    │   │
│  │  │     │                                                   │    │    │   │
│  │  │     └──────────────────────────────────────────────────┘    │    │   │
│  │  │                                                              │    │   │
│  │  │     [Upload Files]                                           │    │   │
│  │  │                                                              │    │   │
│  │  └─────────────────────────────────────────────────────────────┘    │   │
│  │                                                                       │   │
│  │  ─────────────────────── OR ───────────────────────────              │   │
│  │                                                                       │   │
│  │  ┌─────────────────────────────────────────────────────────────┐    │   │
│  │  │  📝 Add Q&A Directly                                         │    │   │
│  │  │                                                              │    │   │
│  │  │  Question:                                                   │    │   │
│  │  │  ┌──────────────────────────────────────────────────────┐   │    │   │
│  │  │  │ What is the return policy for damaged items?         │   │    │   │
│  │  │  └──────────────────────────────────────────────────────┘   │    │   │
│  │  │                                                              │    │   │
│  │  │  Answer:                                                     │    │   │
│  │  │  ┌──────────────────────────────────────────────────────┐   │    │   │
│  │  │  │ Damaged items can be returned within 60 days for a   │   │    │   │
│  │  │  │ full refund. Please include photos of the damage     │   │    │   │
│  │  │  │ when submitting your return request.                  │   │    │   │
│  │  │  └──────────────────────────────────────────────────────┘   │    │   │
│  │  │                                                              │    │   │
│  │  │  Category: [Support ▼]    Tags: [returns, refunds]          │    │   │
│  │  │                                                              │    │   │
│  │  │  [Save Q&A]  [Save & Add Another]                           │    │   │
│  │  └─────────────────────────────────────────────────────────────┘    │   │
│  │                                                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Processing Status

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    UPLOAD PROCESSING STATUS                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Recently Uploaded                                                           │
│  ═══════════════════                                                        │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  📄 Product_Guide_v3.pdf                                             │   │
│  │     Status: ✅ Complete                                              │   │
│  │     45 chunks created • 12 Q&A pairs generated • Ready to query     │   │
│  │     Uploaded: 2 minutes ago                                          │   │
│  │     [View] [Edit Metadata] [Delete]                                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  📄 API_Reference.md                                                 │   │
│  │     Status: ⏳ Processing... (Generating embeddings)                 │   │
│  │     ████████████░░░░░░░░ 60%                                        │   │
│  │     Uploaded: 30 seconds ago                                         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  📄 Old_Policy.docx                                                  │   │
│  │     Status: ❌ Failed - Could not parse document                    │   │
│  │     Error: Document appears to be password protected                 │   │
│  │     [Retry] [Delete]                                                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Document Management

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    KNOWLEDGE BASE MANAGEMENT                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  [+ Upload New]  [+ Add Q&A]  [Bulk Import]                                 │
│                                                                              │
│  Search: [________________________] [🔍]     Filter: [All Types ▼]          │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Document                  │ Type │ Status │ Chunks │ Last Updated  │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │  📄 Product Guide v3.0     │ PDF  │ ✅     │ 45     │ 2 hours ago   │   │
│  │  📄 API Reference          │ MD   │ ✅     │ 78     │ 1 day ago     │   │
│  │  📝 Return Policy FAQ      │ FAQ  │ ✅     │ 12     │ 3 days ago    │   │
│  │  📄 Security Whitepaper    │ PDF  │ ✅     │ 23     │ 1 week ago    │   │
│  │  📄 Onboarding Guide       │ DOCX │ ⚠️ Exp │ 34     │ 45 days ago   │   │
│  │  📄 Pricing Sheet 2024     │ PDF  │ ⚠️ Old │ 8      │ 6 months ago  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  Showing 1-6 of 156 documents                    [< Prev] [1] [2] [Next >] │
│                                                                              │
│  ⚠️ 3 documents are expiring soon                                           │
│  ⚠️ 2 documents haven't been verified in 90+ days                           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Architecture

### Upload Processing Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DOCUMENT UPLOAD PIPELINE                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  User Upload                                                                 │
│       │                                                                      │
│       ▼                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ 1. VALIDATION                                                        │   │
│  │    • Check file type (PDF, DOCX, MD, HTML, TXT, CSV)                │   │
│  │    • Check file size (max 50MB)                                      │   │
│  │    • Virus scan (ClamAV)                                             │   │
│  │    • Check for duplicates (hash comparison)                          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│       │                                                                      │
│       ▼                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ 2. STORAGE                                                           │   │
│  │    • Store original file (S3/local)                                  │   │
│  │    • Create database record with status="pending"                    │   │
│  │    • Return upload_id to user immediately                            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│       │                                                                      │
│       ▼ [Async - Background Job]                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ 3. PARSING                                                           │   │
│  │    • Select parser based on file type                                │   │
│  │    • Extract text, sections, tables                                  │   │
│  │    • Extract metadata (title, author, date)                          │   │
│  │    • Update status="parsing"                                         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│       │                                                                      │
│       ▼                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ 4. CLASSIFICATION                                                    │   │
│  │    • Detect document type (doc, faq, workflow, product)              │   │
│  │    • Assign category (product, technical, policy, etc.)              │   │
│  │    • Detect audience (customer, employee, partner)                   │   │
│  │    • Update status="classifying"                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│       │                                                                      │
│       ▼                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ 5. CHUNKING                                                          │   │
│  │    • Apply chunking strategy based on type                           │   │
│  │    • Create chunk records in database                                │   │
│  │    • Update status="chunking"                                        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│       │                                                                      │
│       ▼                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ 6. ENRICHMENT                                                        │   │
│  │    • Generate summary (LLM)                                          │   │
│  │    • Extract entities                                                │   │
│  │    • Generate Q&A pairs (LLM)                                        │   │
│  │    • Update status="enriching"                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│       │                                                                      │
│       ▼                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ 7. EMBEDDING                                                         │   │
│  │    • Generate embeddings for all chunks                              │   │
│  │    • Store in PostgreSQL (pgvector)                                  │   │
│  │    • Update status="embedding"                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│       │                                                                      │
│       ▼                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ 8. INDEXING                                                          │   │
│  │    • Add to vector store (Pinecone/ChromaDB)                         │   │
│  │    • Add to BM25 index                                               │   │
│  │    • Add to FAQ index (if applicable)                                │   │
│  │    • Update status="indexing"                                        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│       │                                                                      │
│       ▼                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ 9. COMPLETE                                                          │   │
│  │    • Update status="complete"                                        │   │
│  │    • Send notification (email/webhook)                               │   │
│  │    • Document now searchable!                                        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Database Schema

### Upload Tracking Tables

```sql
-- Track document uploads and their processing status
CREATE TABLE document_uploads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- File information
    original_filename VARCHAR(500) NOT NULL,
    file_type VARCHAR(20) NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    file_hash VARCHAR(64) NOT NULL,          -- SHA-256 for dedup
    storage_path VARCHAR(1000) NOT NULL,     -- S3 or local path

    -- Upload metadata
    uploaded_by UUID REFERENCES users(id),
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- User-provided metadata
    title VARCHAR(500),
    description TEXT,
    category VARCHAR(100),
    subcategory VARCHAR(100),
    tags TEXT[],
    audience TEXT[],                         -- ['customer', 'employee', 'partner']

    -- Processing status
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    -- 'pending', 'validating', 'parsing', 'classifying',
    -- 'chunking', 'enriching', 'embedding', 'indexing',
    -- 'complete', 'failed'

    status_message TEXT,                     -- Current step description
    progress_percent INTEGER DEFAULT 0,      -- 0-100

    -- Processing results
    knowledge_item_id UUID REFERENCES knowledge_items(id),
    chunks_created INTEGER,
    qa_pairs_generated INTEGER,
    entities_extracted INTEGER,

    -- Error handling
    error_message TEXT,
    error_details JSONB,
    retry_count INTEGER DEFAULT 0,

    -- Timestamps
    processing_started_at TIMESTAMP WITH TIME ZONE,
    processing_completed_at TIMESTAMP WITH TIME ZONE,

    -- Soft delete
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- Indexes
CREATE INDEX idx_uploads_status ON document_uploads(status);
CREATE INDEX idx_uploads_user ON document_uploads(uploaded_by);
CREATE INDEX idx_uploads_hash ON document_uploads(file_hash);
CREATE INDEX idx_uploads_created ON document_uploads(uploaded_at DESC);

-- Direct Q&A entries (not from documents)
CREATE TABLE direct_qa_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Q&A content
    question TEXT NOT NULL,
    answer TEXT NOT NULL,

    -- Metadata
    category VARCHAR(100),
    subcategory VARCHAR(100),
    tags TEXT[],
    audience TEXT[],

    -- Status
    status VARCHAR(50) DEFAULT 'active',     -- 'active', 'archived', 'pending_review'

    -- Linking
    knowledge_item_id UUID REFERENCES knowledge_items(id),

    -- Authorship
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_by UUID REFERENCES users(id),
    updated_at TIMESTAMP WITH TIME ZONE,

    -- Verification
    verified_by UUID REFERENCES users(id),
    verified_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE
);

-- Bulk import jobs
CREATE TABLE bulk_import_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Job info
    job_type VARCHAR(50) NOT NULL,           -- 'csv_qa', 'zip_documents', 'url_crawl'
    source_file VARCHAR(1000),

    -- Status
    status VARCHAR(50) DEFAULT 'pending',
    total_items INTEGER,
    processed_items INTEGER DEFAULT 0,
    successful_items INTEGER DEFAULT 0,
    failed_items INTEGER DEFAULT 0,

    -- Tracking
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,

    -- Results
    results JSONB                            -- Detailed per-item results
);
```

---

## API Endpoints

### Upload Endpoints

```yaml
# POST /api/v1/documents/upload
# Upload a single document
Request:
  Content-Type: multipart/form-data
  Body:
    file: <binary>
    title: "Product Guide v3.0"           # optional, extracted if not provided
    category: "product"                    # optional, auto-detected if not provided
    tags: ["onboarding", "getting-started"]
    audience: ["customer"]

Response:
  {
    "upload_id": "up_abc123",
    "status": "pending",
    "message": "Upload received. Processing will begin shortly.",
    "estimated_time_seconds": 30
  }

---

# GET /api/v1/documents/upload/{upload_id}/status
# Check upload processing status
Response:
  {
    "upload_id": "up_abc123",
    "status": "embedding",
    "progress_percent": 75,
    "status_message": "Generating embeddings for 45 chunks...",
    "steps_completed": ["validation", "parsing", "classification", "chunking", "enrichment"],
    "steps_remaining": ["embedding", "indexing"],
    "started_at": "2025-01-15T10:30:00Z",
    "estimated_completion": "2025-01-15T10:31:00Z"
  }

---

# POST /api/v1/documents/qa
# Add a direct Q&A entry
Request:
  {
    "question": "What is the return policy for damaged items?",
    "answer": "Damaged items can be returned within 60 days...",
    "category": "support",
    "tags": ["returns", "refunds"],
    "audience": ["customer"]
  }

Response:
  {
    "qa_id": "qa_xyz789",
    "knowledge_item_id": "ki_abc123",
    "status": "active",
    "message": "Q&A added successfully and is now searchable."
  }

---

# POST /api/v1/documents/bulk
# Bulk import from CSV or ZIP
Request:
  Content-Type: multipart/form-data
  Body:
    file: <qa_import.csv or documents.zip>
    type: "csv_qa" | "zip_documents"

Response:
  {
    "job_id": "job_bulk123",
    "status": "processing",
    "total_items": 150,
    "message": "Bulk import started. Check status for progress."
  }

---

# GET /api/v1/documents
# List all documents with filtering
Query Parameters:
  - status: pending|complete|failed
  - category: product|technical|support
  - type: document|faq|workflow
  - search: text search
  - page: 1
  - limit: 20

Response:
  {
    "documents": [...],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 156,
      "total_pages": 8
    }
  }

---

# DELETE /api/v1/documents/{knowledge_item_id}
# Delete a document and all its chunks/embeddings
Response:
  {
    "status": "deleted",
    "chunks_removed": 45,
    "embeddings_removed": 45,
    "message": "Document and all associated data removed."
  }

---

# PUT /api/v1/documents/{knowledge_item_id}
# Update document metadata
Request:
  {
    "title": "Product Guide v3.1",
    "category": "product",
    "tags": ["updated", "2025"],
    "expires_at": "2025-12-31T00:00:00Z"
  }

Response:
  {
    "status": "updated",
    "knowledge_item_id": "ki_abc123"
  }

---

# POST /api/v1/documents/{knowledge_item_id}/reprocess
# Re-process an existing document (re-chunk, re-embed)
# Useful after model upgrades or when fixing issues
Response:
  {
    "upload_id": "up_reprocess123",
    "status": "pending",
    "message": "Document queued for reprocessing."
  }
```

---

## Frontend Implementation

### Upload Component (React)

```tsx
// components/DocumentUpload.tsx
import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';

interface UploadState {
  file: File | null;
  status: 'idle' | 'uploading' | 'processing' | 'complete' | 'error';
  progress: number;
  uploadId: string | null;
  error: string | null;
}

export const DocumentUpload: React.FC = () => {
  const [uploads, setUploads] = useState<UploadState[]>([]);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    for (const file of acceptedFiles) {
      // Add to upload list
      const uploadState: UploadState = {
        file,
        status: 'uploading',
        progress: 0,
        uploadId: null,
        error: null,
      };
      setUploads(prev => [...prev, uploadState]);

      try {
        // Upload file
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch('/api/v1/documents/upload', {
          method: 'POST',
          body: formData,
        });

        const data = await response.json();

        // Update with upload ID and start polling
        updateUpload(file.name, {
          status: 'processing',
          uploadId: data.upload_id,
        });

        // Poll for status
        pollStatus(data.upload_id, file.name);

      } catch (error) {
        updateUpload(file.name, {
          status: 'error',
          error: error.message,
        });
      }
    }
  }, []);

  const pollStatus = async (uploadId: string, fileName: string) => {
    const interval = setInterval(async () => {
      const response = await fetch(`/api/v1/documents/upload/${uploadId}/status`);
      const data = await response.json();

      updateUpload(fileName, {
        progress: data.progress_percent,
        status: data.status === 'complete' ? 'complete' : 'processing',
      });

      if (data.status === 'complete' || data.status === 'failed') {
        clearInterval(interval);
        if (data.status === 'failed') {
          updateUpload(fileName, {
            status: 'error',
            error: data.error_message,
          });
        }
      }
    }, 2000); // Poll every 2 seconds
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/markdown': ['.md'],
      'text/html': ['.html'],
      'text/plain': ['.txt'],
      'text/csv': ['.csv'],
    },
    maxSize: 50 * 1024 * 1024, // 50MB
  });

  return (
    <div className="upload-container">
      {/* Dropzone */}
      <div {...getRootProps()} className={`dropzone ${isDragActive ? 'active' : ''}`}>
        <input {...getInputProps()} />
        <div className="dropzone-content">
          <span className="icon">📄</span>
          <p>Drag & drop files here, or click to browse</p>
          <p className="supported">PDF, DOCX, MD, HTML, TXT, CSV (max 50MB)</p>
        </div>
      </div>

      {/* Upload Progress List */}
      {uploads.length > 0 && (
        <div className="upload-list">
          <h3>Uploads</h3>
          {uploads.map((upload, index) => (
            <UploadItem key={index} upload={upload} />
          ))}
        </div>
      )}
    </div>
  );
};

const UploadItem: React.FC<{ upload: UploadState }> = ({ upload }) => {
  return (
    <div className={`upload-item status-${upload.status}`}>
      <div className="file-info">
        <span className="filename">{upload.file?.name}</span>
        <span className="status-badge">{upload.status}</span>
      </div>

      {upload.status === 'processing' && (
        <div className="progress-bar">
          <div className="progress" style={{ width: `${upload.progress}%` }} />
        </div>
      )}

      {upload.status === 'complete' && (
        <div className="success-message">
          ✅ Ready to query
        </div>
      )}

      {upload.status === 'error' && (
        <div className="error-message">
          ❌ {upload.error}
        </div>
      )}
    </div>
  );
};
```

### Direct Q&A Form

```tsx
// components/DirectQAForm.tsx
import React, { useState } from 'react';

export const DirectQAForm: React.FC = () => {
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState('');
  const [category, setCategory] = useState('');
  const [tags, setTags] = useState<string[]>([]);
  const [status, setStatus] = useState<'idle' | 'saving' | 'success' | 'error'>('idle');

  const handleSubmit = async (e: React.FormEvent, addAnother: boolean = false) => {
    e.preventDefault();
    setStatus('saving');

    try {
      const response = await fetch('/api/v1/documents/qa', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, answer, category, tags }),
      });

      if (response.ok) {
        setStatus('success');
        if (addAnother) {
          // Clear form for another entry
          setQuestion('');
          setAnswer('');
          setTimeout(() => setStatus('idle'), 2000);
        }
      } else {
        throw new Error('Failed to save');
      }
    } catch (error) {
      setStatus('error');
    }
  };

  return (
    <form className="qa-form" onSubmit={(e) => handleSubmit(e, false)}>
      <h3>📝 Add Q&A Directly</h3>

      <div className="form-group">
        <label>Question</label>
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="What is the return policy for damaged items?"
          rows={2}
          required
        />
      </div>

      <div className="form-group">
        <label>Answer</label>
        <textarea
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
          placeholder="Damaged items can be returned within 60 days..."
          rows={4}
          required
        />
        <small>Tip: You can use Markdown formatting</small>
      </div>

      <div className="form-row">
        <div className="form-group">
          <label>Category</label>
          <select value={category} onChange={(e) => setCategory(e.target.value)}>
            <option value="">Select category...</option>
            <option value="product">Product</option>
            <option value="technical">Technical</option>
            <option value="support">Support</option>
            <option value="policy">Policy</option>
            <option value="billing">Billing</option>
          </select>
        </div>

        <div className="form-group">
          <label>Tags</label>
          <input
            type="text"
            placeholder="returns, refunds (comma-separated)"
            onChange={(e) => setTags(e.target.value.split(',').map(t => t.trim()))}
          />
        </div>
      </div>

      <div className="form-actions">
        <button type="submit" disabled={status === 'saving'}>
          {status === 'saving' ? 'Saving...' : 'Save Q&A'}
        </button>
        <button
          type="button"
          onClick={(e) => handleSubmit(e as any, true)}
          disabled={status === 'saving'}
        >
          Save & Add Another
        </button>
      </div>

      {status === 'success' && (
        <div className="success-message">✅ Q&A saved and ready to query!</div>
      )}
    </form>
  );
};
```

---

## Bulk Import Formats

### CSV Format for Q&A Import

```csv
question,answer,category,tags,audience
"What is the return policy?","Items can be returned within 30 days...","support","returns,refunds","customer"
"How do I reset my password?","Go to Settings > Account > Reset Password...","technical","account,password","customer,employee"
"What are the API rate limits?","Free tier: 100 req/min. Pro: 1000 req/min...","technical","api,limits","developer"
```

### Bulk Import API

```python
# Example: Bulk import Q&A from CSV
import csv
from io import StringIO


class BulkImportService:
    """Handle bulk imports of Q&A and documents."""

    def import_qa_csv(self, file_content: str, user_id: str) -> dict:
        """Import Q&A pairs from CSV."""
        reader = csv.DictReader(StringIO(file_content))

        job_id = str(uuid.uuid4())
        results = {"success": [], "failed": []}

        for row in reader:
            try:
                # Create Q&A entry
                qa_id = self.create_qa_entry(
                    question=row['question'],
                    answer=row['answer'],
                    category=row.get('category'),
                    tags=row.get('tags', '').split(','),
                    audience=row.get('audience', '').split(','),
                    created_by=user_id
                )
                results["success"].append({"row": row, "qa_id": qa_id})

            except Exception as e:
                results["failed"].append({"row": row, "error": str(e)})

        return {
            "job_id": job_id,
            "total": len(results["success"]) + len(results["failed"]),
            "successful": len(results["success"]),
            "failed": len(results["failed"]),
            "results": results
        }

    def import_document_zip(self, zip_file: bytes, user_id: str) -> dict:
        """Import multiple documents from ZIP file."""
        import zipfile
        from io import BytesIO

        job_id = str(uuid.uuid4())
        results = {"success": [], "failed": []}

        with zipfile.ZipFile(BytesIO(zip_file)) as zf:
            for filename in zf.namelist():
                if filename.endswith(('.pdf', '.docx', '.md', '.html', '.txt')):
                    try:
                        # Extract and upload
                        content = zf.read(filename)
                        upload_id = self.upload_document(
                            filename=filename,
                            content=content,
                            user_id=user_id
                        )
                        results["success"].append({"filename": filename, "upload_id": upload_id})

                    except Exception as e:
                        results["failed"].append({"filename": filename, "error": str(e)})

        return {
            "job_id": job_id,
            "total": len(results["success"]) + len(results["failed"]),
            "successful": len(results["success"]),
            "failed": len(results["failed"]),
            "results": results
        }
```

---

## Background Job Implementation

### Celery Tasks for Document Processing

```python
from celery import Celery, chain
from typing import Optional

app = Celery('document_processing')


@app.task(bind=True, max_retries=3)
def process_document_upload(self, upload_id: str):
    """Main task that orchestrates document processing."""
    try:
        upload = get_upload(upload_id)

        # Execute pipeline steps
        steps = [
            ('validating', validate_document),
            ('parsing', parse_document),
            ('classifying', classify_document),
            ('chunking', chunk_document),
            ('enriching', enrich_document),
            ('embedding', embed_chunks),
            ('indexing', index_chunks),
        ]

        for step_name, step_func in steps:
            update_status(upload_id, step_name)
            step_func(upload_id)

        # Complete
        update_status(upload_id, 'complete')
        send_completion_notification(upload_id)

    except Exception as e:
        update_status(upload_id, 'failed', error=str(e))
        raise self.retry(exc=e, countdown=60)  # Retry in 1 minute


@app.task
def validate_document(upload_id: str):
    """Validate uploaded document."""
    upload = get_upload(upload_id)

    # Check file type
    if upload.file_type not in ALLOWED_TYPES:
        raise ValueError(f"Unsupported file type: {upload.file_type}")

    # Check for duplicates
    existing = find_by_hash(upload.file_hash)
    if existing:
        raise ValueError(f"Duplicate document. Already exists as: {existing.title}")

    # Virus scan (if configured)
    if VIRUS_SCAN_ENABLED:
        scan_result = scan_file(upload.storage_path)
        if not scan_result.clean:
            raise ValueError(f"Virus detected: {scan_result.threat}")

    update_progress(upload_id, 10)


@app.task
def parse_document(upload_id: str):
    """Parse document and extract content."""
    upload = get_upload(upload_id)

    # Select parser
    parser = get_parser(upload.file_type)

    # Parse
    document = parser.parse(upload.storage_path)

    # Store parsed content
    store_parsed_content(upload_id, document)

    update_progress(upload_id, 25)


@app.task
def classify_document(upload_id: str):
    """Classify document type and category."""
    upload = get_upload(upload_id)
    document = get_parsed_content(upload_id)

    classifier = DocumentClassifier()
    knowledge_type, category, audience = classifier.classify(document)

    # Update with classification
    update_classification(upload_id, knowledge_type, category, audience)

    update_progress(upload_id, 35)


@app.task
def chunk_document(upload_id: str):
    """Chunk document into searchable pieces."""
    upload = get_upload(upload_id)
    document = get_parsed_content(upload_id)
    knowledge_type = upload.knowledge_type

    chunker = ChunkingPipeline()
    chunks = chunker.chunk(document, knowledge_type)

    # Store chunks
    chunk_ids = store_chunks(upload_id, chunks)

    update_upload(upload_id, chunks_created=len(chunks))
    update_progress(upload_id, 50)


@app.task
def enrich_document(upload_id: str):
    """Generate summaries, Q&A pairs, extract entities."""
    upload = get_upload(upload_id)
    document = get_parsed_content(upload_id)

    # Generate summary
    summary = summary_generator.generate(document.content)

    # Extract entities
    entities = entity_extractor.extract(document.content)

    # Generate Q&A pairs
    qa_pairs = qa_generator.generate(document.content)

    # Store enrichments
    store_enrichments(upload_id, summary, entities, qa_pairs)

    update_upload(upload_id, qa_pairs_generated=len(qa_pairs))
    update_progress(upload_id, 70)


@app.task
def embed_chunks(upload_id: str):
    """Generate embeddings for all chunks."""
    chunks = get_chunks(upload_id)

    embedder = EmbeddingGenerator()

    for i, chunk in enumerate(chunks):
        embedding = embedder.embed_single(chunk.content)
        store_embedding(chunk.id, embedding)

        # Update progress incrementally
        progress = 70 + (20 * (i + 1) / len(chunks))
        update_progress(upload_id, int(progress))


@app.task
def index_chunks(upload_id: str):
    """Add chunks to search indexes."""
    chunks = get_chunks_with_embeddings(upload_id)

    # Add to vector store
    vector_store.add(
        ids=[c.id for c in chunks],
        embeddings=[c.embedding for c in chunks],
        metadata=[c.metadata for c in chunks]
    )

    # Add to BM25 index
    for chunk in chunks:
        bm25_index.add_document(chunk.id, chunk.content)

    update_progress(upload_id, 100)


def update_status(upload_id: str, status: str, error: Optional[str] = None):
    """Update upload status in database."""
    db.execute("""
        UPDATE document_uploads
        SET status = %s, status_message = %s, error_message = %s
        WHERE id = %s
    """, (status, STATUS_MESSAGES.get(status), error, upload_id))


def update_progress(upload_id: str, progress: int):
    """Update processing progress."""
    db.execute("""
        UPDATE document_uploads
        SET progress_percent = %s
        WHERE id = %s
    """, (progress, upload_id))


STATUS_MESSAGES = {
    'pending': 'Waiting to start processing...',
    'validating': 'Validating document...',
    'parsing': 'Extracting text and structure...',
    'classifying': 'Detecting document type and category...',
    'chunking': 'Splitting into searchable chunks...',
    'enriching': 'Generating summaries and Q&A pairs...',
    'embedding': 'Creating vector embeddings...',
    'indexing': 'Adding to search indexes...',
    'complete': 'Processing complete. Document is now searchable.',
    'failed': 'Processing failed.',
}
```

---

## Document Update/Replace Flow

### Updating Existing Documents

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DOCUMENT UPDATE FLOW                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  User uploads new version of "Product Guide v3.0"                           │
│       │                                                                      │
│       ▼                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ DUPLICATE DETECTION                                                  │   │
│  │                                                                       │   │
│  │ System detects similar document exists:                              │   │
│  │ "Product Guide v3.0" uploaded 30 days ago                           │   │
│  │                                                                       │   │
│  │ ┌─────────────────────────────────────────────────────────────────┐ │   │
│  │ │  ⚠️ Similar document found                                       │ │   │
│  │ │                                                                   │ │   │
│  │ │  "Product Guide v3.0" was uploaded on Jan 1, 2025               │ │   │
│  │ │                                                                   │ │   │
│  │ │  What would you like to do?                                      │ │   │
│  │ │                                                                   │ │   │
│  │ │  [Replace existing]  [Keep both]  [Cancel]                      │ │   │
│  │ └─────────────────────────────────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│       │                                                                      │
│       ▼ [User clicks "Replace existing"]                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ REPLACEMENT PROCESS                                                  │   │
│  │                                                                       │   │
│  │ 1. Archive old document (keep for 30 days)                          │   │
│  │ 2. Remove old chunks from indexes                                    │   │
│  │ 3. Process new document                                              │   │
│  │ 4. Link feedback from old document to new                           │   │
│  │ 5. Notify content owner of update                                    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Integration with Existing System

### Where Upload Fits in Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    COMPLETE SYSTEM ARCHITECTURE                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────┐                      ┌──────────────────┐             │
│  │  DOCUMENT UPLOAD │                      │   QUERY SYSTEM   │             │
│  │                  │                      │                  │             │
│  │  • Web UI        │                      │  • Chat UI       │             │
│  │  • API           │                      │  • API           │             │
│  │  • Bulk Import   │                      │  • Slack/Teams   │             │
│  └────────┬─────────┘                      └────────┬─────────┘             │
│           │                                         │                        │
│           ▼                                         ▼                        │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                        SHARED DATA LAYER                              │  │
│  │                                                                        │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐     │  │
│  │  │ Knowledge  │  │   Chunks   │  │ Embeddings │  │   Vector   │     │  │
│  │  │   Items    │  │            │  │            │  │   Store    │     │  │
│  │  │ (Postgres) │  │ (Postgres) │  │ (pgvector) │  │ (Pinecone) │     │  │
│  │  └────────────┘  └────────────┘  └────────────┘  └────────────┘     │  │
│  │                                                                        │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐                      │  │
│  │  │   BM25     │  │    FAQ     │  │  Metadata  │                      │  │
│  │  │   Index    │  │   Index    │  │   Index    │                      │  │
│  │  │ (Elastic)  │  │ (Vector)   │  │ (Postgres) │                      │  │
│  │  └────────────┘  └────────────┘  └────────────┘                      │  │
│  │                                                                        │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  Upload writes to ──▶ All indexes ──▶ Query reads from                     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Security Considerations

### Upload Security

```python
class UploadSecurityValidator:
    """Validate uploads for security."""

    ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.md', '.html', '.txt', '.csv'}
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    ALLOWED_MIME_TYPES = {
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'text/markdown',
        'text/html',
        'text/plain',
        'text/csv',
    }

    def validate(self, file: UploadFile) -> ValidationResult:
        """Comprehensive security validation."""
        errors = []

        # 1. Extension check
        ext = Path(file.filename).suffix.lower()
        if ext not in self.ALLOWED_EXTENSIONS:
            errors.append(f"File type {ext} not allowed")

        # 2. Size check
        if file.size > self.MAX_FILE_SIZE:
            errors.append(f"File too large. Max: {self.MAX_FILE_SIZE / 1024 / 1024}MB")

        # 3. MIME type check (don't trust Content-Type header)
        import magic
        mime_type = magic.from_buffer(file.read(1024), mime=True)
        file.seek(0)  # Reset file position
        if mime_type not in self.ALLOWED_MIME_TYPES:
            errors.append(f"Invalid file content type: {mime_type}")

        # 4. Filename sanitization
        safe_filename = self.sanitize_filename(file.filename)
        if not safe_filename:
            errors.append("Invalid filename")

        # 5. Virus scan (if enabled)
        if VIRUS_SCAN_ENABLED:
            scan_result = self.virus_scan(file)
            if not scan_result.clean:
                errors.append(f"Security threat detected: {scan_result.threat}")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            sanitized_filename=safe_filename
        )

    def sanitize_filename(self, filename: str) -> str:
        """Remove potentially dangerous characters from filename."""
        import re
        # Remove path separators and null bytes
        safe = re.sub(r'[/\\:\x00]', '', filename)
        # Remove leading dots (hidden files)
        safe = safe.lstrip('.')
        # Limit length
        return safe[:255] if safe else None
```

---

## Implementation Checklist Addition

### Week 15 (Add to Phase 7)

#### Document Upload System
- [ ] Create `document_uploads` table
- [ ] Create `direct_qa_entries` table
- [ ] Create `bulk_import_jobs` table
- [ ] Implement file validation
- [ ] Implement secure file storage (S3 or local)
- [ ] Implement upload API endpoint
- [ ] Implement status polling endpoint
- [ ] Create Celery tasks for processing pipeline
- [ ] Implement progress tracking
- [ ] Write upload UI component
- [ ] Write Q&A form component
- [ ] Write document list/management UI
- [ ] Implement bulk CSV import
- [ ] Implement bulk ZIP import
- [ ] Add duplicate detection
- [ ] Add document replacement flow
- [ ] Write unit tests
- [ ] Write integration tests

**Checkpoint**: Users can upload documents and see them become searchable

---

## Summary

The document upload system provides:

1. **Easy Upload** - Drag & drop, bulk import, direct Q&A entry
2. **Real-time Status** - Progress tracking with status updates
3. **Automatic Processing** - Parse → Chunk → Embed → Index pipeline
4. **Document Management** - View, edit, delete, replace documents
5. **Security** - File validation, virus scanning, access control
6. **Bulk Operations** - CSV Q&A import, ZIP document batch upload

Users can add new knowledge in seconds, and it becomes queryable immediately after processing completes.
