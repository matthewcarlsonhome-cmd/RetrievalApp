# Knowledge Expert - User Training Guide

## Welcome!

This guide will help you get the most out of your Knowledge Expert AI assistant.

---

## Getting Started

### Accessing the System

Open your web browser and go to your Knowledge Expert URL:
- **Chat**: `https://your-domain.com` - Ask questions
- **Upload**: `https://your-domain.com/upload` - Add documents
- **Q&A**: `https://your-domain.com/qa` - Manage Q&A pairs
- **Admin**: `https://your-domain.com/admin` - View statistics

---

## Using the Chat

### Asking Questions

1. Type your question in the chat box
2. Press Enter or click the send button
3. Wait for the AI to respond (usually 2-5 seconds)

### Tips for Better Answers

**Be specific:**
- Instead of: "What do you do?"
- Try: "What AI automation services do you offer?"

**Ask one thing at a time:**
- Instead of: "What are your rates and where are you located?"
- Try: "What are your hourly rates?" then "Where are you located?"

**Use natural language:**
- The AI understands conversational questions
- "Can you help with marketing?" works as well as formal queries

### Understanding Responses

Responses include:
- **Answer**: The AI's response based on your knowledge base
- **Sources**: Documents or Q&A pairs used to generate the answer
- **Feedback buttons**: Rate the response to help improve the system

### Providing Feedback

After each response, you'll see thumbs up/down buttons:

- **Thumbs Up** 👍: The answer was helpful and accurate
- **Thumbs Down** 👎: The answer was wrong, incomplete, or unhelpful

When you click thumbs down, you can add details about what was wrong. This feedback helps improve future responses.

---

## Uploading Documents

### Supported File Types

| Format | Extension | Best For |
|--------|-----------|----------|
| PDF | .pdf | Reports, brochures, manuals |
| Word | .docx | Documents, proposals |
| Markdown | .md | Structured content, FAQs |
| Text | .txt | Simple text content |
| HTML | .html | Web pages, exported content |

### How to Upload

1. Go to the **Upload** page
2. Drag files into the drop zone, OR click to browse
3. Wait for processing (usually 10-30 seconds per document)
4. Verify the document appears in the list

### Best Practices for Documents

**Content Structure:**
- Use clear headings and sections
- Keep related information together
- Avoid excessive formatting or images

**File Naming:**
- Use descriptive names: `pricing-guide-2024.pdf` not `doc1.pdf`
- Include dates for time-sensitive content

**File Size:**
- Maximum: 10MB per file
- Larger files take longer to process

**What to Upload:**
- Company information and policies
- Product/service descriptions
- Pricing information
- FAQs and common questions
- Process documentation

**What NOT to Upload:**
- Confidential client information
- Personal employee data
- Financial statements (unless needed for queries)
- Very large files with minimal text

---

## Managing Q&A Pairs

### What are Q&A Pairs?

Direct Q&A pairs are pre-defined questions and answers that the AI uses first when responding. They ensure consistent, accurate answers for common questions.

### Adding Q&A Pairs

1. Go to the **Q&A** page
2. Fill in the form:
   - **Question**: How users might ask this
   - **Answer**: The complete, accurate response
   - **Category**: Topic area (Services, Pricing, etc.)
3. Click **Add Q&A Pair**

### Writing Good Q&A Pairs

**Questions should match how users ask:**
```
Good: "What are your consulting rates?"
Good: "How much do you charge?"
Less ideal: "Fee structure for professional services"
```

**Answers should be complete but concise:**
```
Good: "Our standard consulting rate is $200 per hour.
This applies to all strategy, implementation, and
support work. We also offer fixed-price projects
and monthly retainers."

Too short: "$200/hour"
Too long: [Multiple paragraphs of tangential information]
```

### Categories

Use categories to organize Q&A pairs:

| Category | Examples |
|----------|----------|
| General | Company info, location, contact |
| Services | What you offer, capabilities |
| Pricing | Rates, packages, payment terms |
| Process | How engagements work, timelines |
| Technical | Specific technical questions |
| Contact | How to reach you, hours |

---

## Admin Dashboard

### Overview

The Admin page shows:
- **Documents**: Number of uploaded documents
- **Chunks**: Total text segments (for search)
- **Queries**: Total questions asked
- **Q&A Pairs**: Direct question-answer count

### System Status

Check that all components show "Active":
- **Embedding Model**: Converts text to searchable format
- **Vector Store**: Stores and searches embeddings
- **Search Engine**: Combines search methods
- **LLM Provider**: Generates responses (Claude)

### Feedback Summary

Shows how users rate responses:
- Track positive vs negative feedback
- High negative feedback may indicate missing content
- Use feedback to add/update Q&A pairs

---

## Content Guidelines

### What the AI Will Answer

The AI answers questions based on:
1. Uploaded documents
2. Q&A pairs you've added
3. General knowledge (with caution)

### What the AI Won't Discuss

The system is configured to avoid:
- Profanity and explicit content
- Political opinions
- Religious discussions
- Competitor recommendations
- Personal opinions on controversial topics

### Keeping Content Fresh

**Regular updates:**
- Add new Q&A pairs as common questions emerge
- Update documents when information changes
- Remove outdated content

**After major changes:**
- Update relevant documents
- Add Q&A pairs for new offerings
- Test by asking questions about new content

---

## Troubleshooting

### "I don't have information about that"

The AI couldn't find relevant content. Solutions:
1. Check if the topic is covered in your documents
2. Add a Q&A pair for this question
3. Upload additional documentation

### Incorrect or Outdated Answers

1. Click the thumbs down button
2. Add feedback about what's wrong
3. Update the relevant document or Q&A pair

### Slow Responses

Normal response time is 2-5 seconds. If slower:
- First query of the day may take 10-20 seconds (loading models)
- Check your internet connection
- Contact admin if consistently slow

### Upload Failures

If document upload fails:
1. Check file format is supported
2. Ensure file is under 10MB
3. Try a different browser
4. Contact admin with the error message

---

## Quick Reference

### Chat Shortcuts

Click the quick question buttons for common queries:
- "What services do you offer?"
- "What are your rates?"
- "Project timelines?"
- "AI automation?"

### Keyboard Shortcuts

- **Enter**: Send message
- **Shift+Enter**: New line in message

### Support

For system issues, contact your administrator.

For content questions, update your documents or Q&A pairs.

---

## Appendix: Feedback Examples

### Helpful Feedback

When rating responses negatively, include details:

**Good feedback:**
- "The pricing is outdated - we changed rates last month"
- "Missing information about our new service"
- "Answer was too generic - we have a specific process"

**Less helpful:**
- "Wrong"
- "Bad"
- "Doesn't work"

Your detailed feedback helps improve the system for everyone!
