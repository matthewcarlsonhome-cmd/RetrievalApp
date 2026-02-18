# Knowledge Expert - User Guide

## Getting Started

Knowledge Expert is your AI-powered assistant that answers questions using your company's knowledge base. This guide explains how to use and manage the system.

## Using the Chat Interface

### Asking Questions

1. Go to the main page (Chat)
2. Type your question in the input box
3. Press Enter or click "Ask"
4. The AI will respond using information from your knowledge base

### Tips for Better Answers

- **Be specific**: "What is the hourly rate for consulting?" gets better results than "How much?"
- **Use natural language**: Ask questions the way you'd ask a colleague
- **Check sources**: The AI cites its sources - click to verify information

### Example Questions

- "What services do you offer?"
- "How do I schedule a consultation?"
- "What are your business hours?"
- "Tell me about your team's experience"

## Adding Content to the Knowledge Base

### Uploading Documents

1. Click **Upload** in the navigation
2. Click "Choose File" or drag a file into the upload area
3. Supported formats:
   - PDF (.pdf)
   - Word Documents (.docx)
   - Markdown (.md)
   - Text files (.txt)
   - HTML pages (.html)
4. Click "Upload Document"
5. Wait for processing (usually a few seconds)

**Best Practices for Documents:**
- Use clear headings and structure
- Include comprehensive information
- Break long documents into focused topics
- Use consistent terminology

### Adding Q&A Pairs

For frequently asked questions with specific answers:

1. Click **Q&A** in the navigation
2. Fill in the Question field
3. Fill in the Answer field
4. Select a Category (optional but recommended)
5. Click "Add Q&A Pair"

**When to Use Q&A Pairs:**
- Common customer questions
- Pricing information
- Contact details
- Policy statements
- Quick facts

**Example:**
```
Question: What is your hourly rate?
Answer: Our standard consulting rate is $150/hour, with project-based
        pricing available for larger engagements.
Category: Pricing
```

## Managing Content

### Viewing Uploaded Documents

On the Upload page, you'll see:
- Document title
- Number of chunks (sections indexed)
- Upload date
- Delete option

### Deleting Documents

1. Find the document in the list
2. Click the "Delete" button
3. Confirm deletion

Note: Deleting removes the document and all its chunks from the search index.

### Viewing Q&A Pairs

On the Q&A page, scroll down to see "Existing Q&A Pairs":
- Question and answer text
- Category
- Date added
- Delete option

## Admin Dashboard

### Accessing Stats

1. Click **Admin** in the navigation
2. View system statistics:
   - Total documents indexed
   - Total chunks (searchable segments)
   - Total queries answered
   - Q&A pairs added
   - User feedback (positive/negative)

### Understanding Stats

- **Satisfaction Rate**: Percentage of positive feedback
- **Chunks per Document**: Average ~5-20 depending on document length
- **Query Count**: Total questions asked

## How the AI Works

### The RAG Process

1. **Your question** is analyzed
2. **Relevant content** is found in the knowledge base
3. **AI generates** an answer using that content
4. **Sources are cited** so you can verify

### Search Types

The system uses three search methods:
1. **Semantic Search**: Understands meaning (e.g., "cost" matches "pricing")
2. **Keyword Search**: Matches exact words
3. **Q&A Match**: Checks direct Q&A pairs first

### Content Sources

Answers come from:
- Uploaded documents (PDFs, Word docs, etc.)
- Direct Q&A pairs you've added
- Combined context from multiple sources

## Providing Feedback

After receiving an answer, you can:
- 👍 Mark as helpful (positive feedback)
- 👎 Mark as not helpful (negative feedback)

Feedback helps track system performance.

## Troubleshooting

### "I don't have information about that"

The AI only knows what's in the knowledge base. To fix:
1. Upload relevant documents
2. Add Q&A pairs for specific questions
3. Use different wording in your question

### Document Won't Upload

- Check file size (max 10MB recommended)
- Verify file format is supported
- Try a different browser
- Check if file is corrupted

### Answer Seems Wrong

- Verify the source document is accurate
- Add a direct Q&A pair for that specific question
- Check if multiple documents have conflicting info

### Chat Not Responding

- Refresh the page
- Check your internet connection
- Wait a moment and try again

## Content Guidelines

### What to Include

- Service descriptions
- Pricing and policies
- Team bios and expertise
- FAQs and common questions
- Process explanations
- Contact information

### What to Avoid

- Outdated information
- Conflicting documents
- Very long single documents (split into topics)
- Content without clear structure

## Tips for Success

1. **Start with FAQs**: Add your most common questions as Q&A pairs
2. **Structure documents**: Use headings and clear sections
3. **Update regularly**: Remove outdated content, add new information
4. **Test queries**: Ask questions to verify the AI gives good answers
5. **Use feedback**: Track which answers need improvement
