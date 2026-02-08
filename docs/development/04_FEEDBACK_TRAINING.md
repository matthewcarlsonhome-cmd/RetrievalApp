# Feedback and Training Loop Specification

## Overview

This document details the complete feedback capture, processing, and model fine-tuning system. The goal is **continuous improvement**: the system gets smarter with every customer interaction.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CONTINUOUS LEARNING SYSTEM                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  REAL-TIME LAYER (Per Interaction)                                          │
│  ═══════════════════════════════════                                        │
│                                                                              │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐             │
│  │ Customer │───▶│  Query   │───▶│ Response │───▶│ Feedback │             │
│  │  Query   │    │ Process  │    │ Generate │    │ Capture  │             │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘             │
│                                                        │                     │
│                                                        ▼                     │
│                                               ┌──────────────┐              │
│                                               │   Feedback   │              │
│                                               │   Database   │              │
│                                               └──────────────┘              │
│                                                        │                     │
│  ═══════════════════════════════════════════════════════════════════════   │
│                                                                              │
│  BATCH PROCESSING LAYER (Scheduled)                                         │
│  ═══════════════════════════════════                                        │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                         DAILY JOBS                                     │ │
│  │                                                                         │ │
│  │  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐                  │ │
│  │  │  Aggregate  │   │   Quality   │   │  Generate   │                  │ │
│  │  │  Feedback   │   │   Scoring   │   │  Training   │                  │ │
│  │  │  Metrics    │   │             │   │    Data     │                  │ │
│  │  └─────────────┘   └─────────────┘   └─────────────┘                  │ │
│  │                                              │                          │ │
│  └──────────────────────────────────────────────┼──────────────────────────┘ │
│                                                 ▼                            │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                        WEEKLY JOBS                                     │ │
│  │                                                                         │ │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │ │
│  │  │                   EMBEDDING FINE-TUNING                          │  │ │
│  │  │                                                                   │  │ │
│  │  │  1. Collect training triplets from positive feedback             │  │ │
│  │  │  2. Validate quality (score >= 0.7)                              │  │ │
│  │  │  3. Fine-tune Sentence-Transformer model                         │  │ │
│  │  │  4. Evaluate on held-out test set                                │  │ │
│  │  │  5. A/B test new vs old model                                    │  │ │
│  │  │  6. Promote if metrics improve                                   │  │ │
│  │  └─────────────────────────────────────────────────────────────────┘  │ │
│  │                                                                         │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                       MONTHLY JOBS                                     │ │
│  │                                                                         │ │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │ │
│  │  │                    LLM FINE-TUNING                               │  │ │
│  │  │                                                                   │  │ │
│  │  │  1. Collect Q&A pairs from corrections and high-rated responses  │  │ │
│  │  │  2. Human review sample (10%)                                    │  │ │
│  │  │  3. Format for OpenAI/Anthropic fine-tuning API                  │  │ │
│  │  │  4. Submit fine-tuning job                                       │  │ │
│  │  │  5. Gradual rollout (10% → 50% → 100%)                          │  │ │
│  │  │  6. Monitor for regression                                       │  │ │
│  │  └─────────────────────────────────────────────────────────────────┘  │ │
│  │                                                                         │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Part 1: Feedback Capture

### Feedback Types

| Type | UI Element | Data Captured | Training Use |
|------|------------|---------------|--------------|
| **Thumbs Up** | 👍 button | response_id, timestamp | Positive example for embedding training |
| **Thumbs Down** | 👎 button | response_id, timestamp, optional reason | Negative signal, triggers review |
| **Correction** | Text input | user's correct answer | Gold standard for LLM fine-tuning |
| **Not Helpful** | Dropdown | issue type (wrong, outdated, incomplete) | Categorizes failure modes |
| **Report** | Flag button | reason (inappropriate, offensive) | Content moderation review |

### Feedback Capture Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         RESPONSE WITH FEEDBACK UI                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                       │   │
│  │  Q: How do I reset my password?                                      │   │
│  │                                                                       │   │
│  │  A: To reset your password, follow these steps:                      │   │
│  │                                                                       │   │
│  │     1. Go to Settings > Account > Security                           │   │
│  │     2. Click "Reset Password"                                        │   │
│  │     3. Enter your email address                                      │   │
│  │     4. Check your email for the reset link                           │   │
│  │                                                                       │   │
│  │  Source: [User Guide v2.1, Section 3.2]                              │   │
│  │                                                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         FEEDBACK OPTIONS                              │   │
│  │                                                                       │   │
│  │   ┌───────┐  ┌───────┐                                              │   │
│  │   │  👍   │  │  👎   │   Was this helpful?                         │   │
│  │   │ Yes   │  │  No   │                                              │   │
│  │   └───────┘  └───────┘                                              │   │
│  │                                                                       │   │
│  │   [If 👎 clicked:]                                                   │   │
│  │   ┌─────────────────────────────────────────────────────────────┐   │   │
│  │   │  What was wrong?                                             │   │   │
│  │   │                                                               │   │   │
│  │   │  ○ Wrong answer                                              │   │   │
│  │   │  ○ Outdated information                                      │   │   │
│  │   │  ○ Incomplete answer                                         │   │   │
│  │   │  ○ Not what I was looking for                               │   │   │
│  │   │  ○ Other: [________________]                                 │   │   │
│  │   │                                                               │   │   │
│  │   │  ┌─────────────────────────────────────────────────────────┐│   │   │
│  │   │  │ What's the correct answer? (optional)                   ││   │   │
│  │   │  │                                                          ││   │   │
│  │   │  │ [                                                      ] ││   │   │
│  │   │  │                                                          ││   │   │
│  │   │  └─────────────────────────────────────────────────────────┘│   │   │
│  │   │                                                               │   │   │
│  │   │  [Submit Feedback]                                           │   │   │
│  │   └─────────────────────────────────────────────────────────────┘   │   │
│  │                                                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Feedback API

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from enum import Enum


class FeedbackType(Enum):
    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"
    CORRECTION = "correction"
    REPORT = "report"


class IssueType(Enum):
    WRONG_ANSWER = "wrong_answer"
    OUTDATED = "outdated"
    INCOMPLETE = "incomplete"
    NOT_RELEVANT = "not_relevant"
    INAPPROPRIATE = "inappropriate"
    OTHER = "other"


@dataclass
class FeedbackSubmission:
    """Feedback submission from user."""
    response_id: str
    feedback_type: FeedbackType
    issue_type: Optional[IssueType] = None
    comment: Optional[str] = None
    correction: Optional[str] = None
    user_id: Optional[str] = None


class FeedbackService:
    """Handle feedback submission and storage."""

    def __init__(self, db_connection):
        self.db = db_connection

    def submit(self, feedback: FeedbackSubmission) -> str:
        """Submit and store feedback."""
        feedback_id = str(uuid.uuid4())

        self.db.execute("""
            INSERT INTO feedback (
                id, response_id, user_id, feedback_type,
                issue_type, comment, correction, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            feedback_id,
            feedback.response_id,
            feedback.user_id,
            feedback.feedback_type.value,
            feedback.issue_type.value if feedback.issue_type else None,
            feedback.comment,
            feedback.correction,
            datetime.utcnow()
        ))

        self.db.commit()

        # Trigger async processing
        self._enqueue_processing(feedback_id, feedback.feedback_type)

        return feedback_id

    def _enqueue_processing(self, feedback_id: str, feedback_type: FeedbackType):
        """Enqueue feedback for async processing."""
        if feedback_type == FeedbackType.THUMBS_UP:
            # Queue for training data generation
            celery_app.send_task(
                'tasks.generate_training_example',
                args=[feedback_id]
            )
        elif feedback_type == FeedbackType.CORRECTION:
            # Queue for training data + human review
            celery_app.send_task(
                'tasks.process_correction',
                args=[feedback_id]
            )
        elif feedback_type == FeedbackType.REPORT:
            # Queue for moderation review
            celery_app.send_task(
                'tasks.moderation_review',
                args=[feedback_id]
            )
```

### Implicit Feedback Tracking

```python
class ImplicitFeedbackTracker:
    """Track implicit signals of response quality."""

    def __init__(self, db_connection, analytics_client):
        self.db = db_connection
        self.analytics = analytics_client

    def track_click_through(self, response_id: str, source_clicked: str):
        """User clicked on a source citation."""
        self.analytics.track('source_click', {
            'response_id': response_id,
            'source': source_clicked
        })
        # Positive signal: user engaged with sources

    def track_time_on_response(self, response_id: str, duration_seconds: int):
        """Time user spent reading response."""
        self.analytics.track('response_view_time', {
            'response_id': response_id,
            'duration': duration_seconds
        })
        # Long read time = engaged = likely helpful

    def track_follow_up_query(self, response_id: str, follow_up_query: str):
        """User asked a follow-up question."""
        self.analytics.track('follow_up', {
            'response_id': response_id,
            'follow_up': follow_up_query
        })
        # Follow-up may indicate incomplete answer

    def track_support_ticket_created(self, response_id: str, ticket_id: str):
        """User created support ticket after getting response."""
        self.analytics.track('support_escalation', {
            'response_id': response_id,
            'ticket_id': ticket_id
        })
        # Strong negative signal: response didn't help
```

---

## Part 2: Training Data Generation

### Training Data Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     TRAINING DATA GENERATION PIPELINE                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      SOURCE: POSITIVE FEEDBACK                        │   │
│  │                                                                       │   │
│  │  Feedback: 👍 Thumbs Up                                              │   │
│  │  Query: "How do I cancel my subscription?"                           │   │
│  │  Response: "To cancel, go to Settings > Billing > Cancel Plan..."   │   │
│  │  Retrieved Chunks: [chunk_123, chunk_456, chunk_789]                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                      │                                       │
│                                      ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    GENERATE EMBEDDING TRIPLETS                        │   │
│  │                                                                       │   │
│  │  For each retrieved chunk that was relevant:                         │   │
│  │                                                                       │   │
│  │  Triplet = (                                                         │   │
│  │      anchor:   "How do I cancel my subscription?",                   │   │
│  │      positive: chunk_123.content,  # Was retrieved and helpful       │   │
│  │      negative: random_chunk.content  # Unrelated chunk               │   │
│  │  )                                                                    │   │
│  │                                                                       │   │
│  │  Store in: training_data (training_type='embedding')                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                      │                                       │
│                                      ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     GENERATE LLM TRAINING EXAMPLE                     │   │
│  │                                                                       │   │
│  │  Example = {                                                          │   │
│  │      "messages": [                                                    │   │
│  │          {"role": "system", "content": SYSTEM_PROMPT},               │   │
│  │          {"role": "user", "content": "Context: {chunks}\n\n          │   │
│  │                                        Question: How do I cancel?"}, │   │
│  │          {"role": "assistant", "content": response_text}             │   │
│  │      ]                                                                │   │
│  │  }                                                                    │   │
│  │                                                                       │   │
│  │  Store in: training_data (training_type='generation')                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ═══════════════════════════════════════════════════════════════════════   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      SOURCE: USER CORRECTIONS                         │   │
│  │                                                                       │   │
│  │  Feedback: Correction provided                                        │   │
│  │  Query: "What's the refund policy?"                                  │   │
│  │  Original Response: "Refunds are processed within 7 days..."        │   │
│  │  Correction: "Actually, refunds take 3-5 business days, not 7"      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                      │                                       │
│                                      ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      QUALITY VALIDATION                               │   │
│  │                                                                       │   │
│  │  1. Check correction length (min 20 chars)                           │   │
│  │  2. Check correction differs from original                           │   │
│  │  3. Run toxicity/moderation check                                    │   │
│  │  4. Assign quality score                                             │   │
│  │  5. If score >= 0.8, auto-approve                                    │   │
│  │  6. If score 0.5-0.8, queue for human review                        │   │
│  │  7. If score < 0.5, reject                                           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                      │                                       │
│                                      ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    GENERATE HIGH-QUALITY EXAMPLE                      │   │
│  │                                                                       │   │
│  │  LLM Training Example = {                                             │   │
│  │      "messages": [                                                    │   │
│  │          {"role": "system", "content": SYSTEM_PROMPT},               │   │
│  │          {"role": "user", "content": "Context: {original_chunks}\n\n │   │
│  │                                        Question: What's refund..."},  │   │
│  │          {"role": "assistant", "content": CORRECTED_ANSWER}          │   │
│  │      ]                                                                │   │
│  │  }                                                                    │   │
│  │                                                                       │   │
│  │  NOTE: Uses user's correction as the target answer!                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Training Data Generator Implementation

```python
from typing import List, Tuple, Optional
from dataclasses import dataclass
import random
import uuid


@dataclass
class EmbeddingTriplet:
    """Training triplet for embedding fine-tuning."""
    anchor: str      # Query text
    positive: str    # Relevant document
    negative: str    # Irrelevant document


@dataclass
class LLMTrainingExample:
    """Training example for LLM fine-tuning."""
    system_prompt: str
    user_message: str
    assistant_message: str


class TrainingDataGenerator:
    """Generate training data from feedback."""

    SYSTEM_PROMPT = """You are a helpful company knowledge assistant.
Answer questions accurately based ONLY on the provided context.
If you don't know the answer from the context, say so.
Always cite your sources.
Maintain a professional, helpful tone.
Never include inappropriate content."""

    def __init__(self, db_connection, chunk_repository):
        self.db = db_connection
        self.chunks = chunk_repository

    def generate_from_positive_feedback(self, feedback_id: str) -> Tuple[List[EmbeddingTriplet], Optional[LLMTrainingExample]]:
        """Generate training data from thumbs-up feedback."""

        # Get feedback details
        feedback = self.db.query("""
            SELECT f.*, r.response_text, r.retrieved_chunk_ids, q.query_text
            FROM feedback f
            JOIN responses r ON f.response_id = r.id
            JOIN queries q ON r.query_id = q.id
            WHERE f.id = %s
        """, (feedback_id,)).fetchone()

        if not feedback:
            return [], None

        # Generate embedding triplets
        triplets = self._generate_embedding_triplets(
            query=feedback['query_text'],
            relevant_chunk_ids=feedback['retrieved_chunk_ids']
        )

        # Generate LLM example
        llm_example = self._generate_llm_example(
            query=feedback['query_text'],
            chunk_ids=feedback['retrieved_chunk_ids'],
            response=feedback['response_text']
        )

        # Store in database
        for triplet in triplets:
            self._store_embedding_triplet(triplet, feedback_id)

        if llm_example:
            self._store_llm_example(llm_example, feedback_id)

        return triplets, llm_example

    def generate_from_correction(self, feedback_id: str) -> Optional[LLMTrainingExample]:
        """Generate high-quality training example from user correction."""

        feedback = self.db.query("""
            SELECT f.*, r.response_text, r.retrieved_chunk_ids, q.query_text
            FROM feedback f
            JOIN responses r ON f.response_id = r.id
            JOIN queries q ON r.query_id = q.id
            WHERE f.id = %s AND f.correction IS NOT NULL
        """, (feedback_id,)).fetchone()

        if not feedback or not feedback['correction']:
            return None

        # Validate correction quality
        quality_score = self._score_correction_quality(
            original=feedback['response_text'],
            correction=feedback['correction']
        )

        if quality_score < 0.5:
            return None  # Reject low-quality corrections

        # Get context chunks
        chunks = self.chunks.get_by_ids(feedback['retrieved_chunk_ids'])
        context = "\n\n".join([c.content for c in chunks])

        # Create LLM training example with CORRECTED answer
        example = LLMTrainingExample(
            system_prompt=self.SYSTEM_PROMPT,
            user_message=f"Context:\n{context}\n\nQuestion: {feedback['query_text']}",
            assistant_message=feedback['correction']  # Use correction!
        )

        # Store with quality score
        self._store_llm_example(example, feedback_id, quality_score)

        # Mark feedback as processed
        self.db.execute("""
            UPDATE feedback SET training_data_generated = TRUE WHERE id = %s
        """, (feedback_id,))

        return example

    def _generate_embedding_triplets(
        self,
        query: str,
        relevant_chunk_ids: List[str]
    ) -> List[EmbeddingTriplet]:
        """Generate triplets for embedding training."""
        triplets = []

        # Get relevant chunks
        relevant_chunks = self.chunks.get_by_ids(relevant_chunk_ids)

        # Get random negative chunks
        negative_chunks = self.chunks.get_random(
            count=len(relevant_chunks),
            exclude_ids=relevant_chunk_ids
        )

        for pos_chunk, neg_chunk in zip(relevant_chunks, negative_chunks):
            triplets.append(EmbeddingTriplet(
                anchor=query,
                positive=pos_chunk.content,
                negative=neg_chunk.content
            ))

        return triplets

    def _generate_llm_example(
        self,
        query: str,
        chunk_ids: List[str],
        response: str
    ) -> LLMTrainingExample:
        """Generate LLM fine-tuning example."""
        chunks = self.chunks.get_by_ids(chunk_ids)
        context = "\n\n".join([
            f"[Source {i+1}]: {c.content}"
            for i, c in enumerate(chunks)
        ])

        return LLMTrainingExample(
            system_prompt=self.SYSTEM_PROMPT,
            user_message=f"Context:\n{context}\n\nQuestion: {query}",
            assistant_message=response
        )

    def _score_correction_quality(self, original: str, correction: str) -> float:
        """Score the quality of a user correction."""
        score = 1.0

        # Penalty for very short corrections
        if len(correction) < 20:
            score -= 0.3

        # Penalty if identical to original
        if correction.strip() == original.strip():
            return 0.0

        # Penalty for potential spam/abuse
        if self._contains_spam_patterns(correction):
            score -= 0.5

        # Bonus for including citations
        if '[source' in correction.lower() or '[1]' in correction:
            score += 0.1

        return max(0.0, min(1.0, score))

    def _contains_spam_patterns(self, text: str) -> bool:
        """Check for spam/abuse patterns."""
        spam_patterns = [
            r'http[s]?://',  # URLs
            r'[A-Z]{20,}',   # All caps text
            r'(.)\1{10,}',   # Repeated characters
        ]
        import re
        return any(re.search(p, text) for p in spam_patterns)

    def _store_embedding_triplet(self, triplet: EmbeddingTriplet, feedback_id: str):
        """Store embedding triplet in database."""
        self.db.execute("""
            INSERT INTO training_data (
                id, feedback_id, source_type, training_type,
                anchor_text, positive_text, negative_text,
                quality_score, validated, created_at
            ) VALUES (%s, %s, 'positive_feedback', 'embedding',
                      %s, %s, %s, 0.8, TRUE, NOW())
        """, (
            str(uuid.uuid4()),
            feedback_id,
            triplet.anchor,
            triplet.positive,
            triplet.negative
        ))

    def _store_llm_example(
        self,
        example: LLMTrainingExample,
        feedback_id: str,
        quality_score: float = 0.8
    ):
        """Store LLM example in database."""
        self.db.execute("""
            INSERT INTO training_data (
                id, feedback_id, source_type, training_type,
                system_prompt, user_message, assistant_message,
                quality_score, validated, created_at
            ) VALUES (%s, %s, 'positive_feedback', 'generation',
                      %s, %s, %s, %s, %s, NOW())
        """, (
            str(uuid.uuid4()),
            feedback_id,
            example.system_prompt,
            example.user_message,
            example.assistant_message,
            quality_score,
            quality_score >= 0.8  # Auto-validate high quality
        ))
```

---

## Part 3: Embedding Fine-Tuning

### Weekly Embedding Training Pipeline

```python
from sentence_transformers import SentenceTransformer, InputExample, losses
from torch.utils.data import DataLoader
from typing import List, Tuple
import torch


class EmbeddingFineTuner:
    """Fine-tune embedding model on company-specific data."""

    def __init__(
        self,
        base_model: str = "all-MiniLM-L6-v2",
        db_connection = None
    ):
        self.base_model = base_model
        self.db = db_connection
        self.model = SentenceTransformer(base_model)

    def get_training_data(self, min_quality: float = 0.7) -> List[Tuple[str, str, str]]:
        """Get validated training triplets from database."""
        rows = self.db.query("""
            SELECT anchor_text, positive_text, negative_text
            FROM training_data
            WHERE training_type = 'embedding'
            AND validated = TRUE
            AND used_in_training = FALSE
            AND quality_score >= %s
        """, (min_quality,)).fetchall()

        return [(r['anchor_text'], r['positive_text'], r['negative_text']) for r in rows]

    def fine_tune(
        self,
        training_data: List[Tuple[str, str, str]],
        epochs: int = 3,
        batch_size: int = 16,
        warmup_steps: int = 100
    ) -> str:
        """Fine-tune the embedding model."""
        if len(training_data) < 100:
            raise ValueError(f"Need at least 100 training examples, got {len(training_data)}")

        # Prepare training examples
        train_examples = []
        for anchor, positive, negative in training_data:
            # Positive pair
            train_examples.append(InputExample(texts=[anchor, positive], label=1.0))
            # Negative pair
            train_examples.append(InputExample(texts=[anchor, negative], label=0.0))

        # Create dataloader
        train_dataloader = DataLoader(train_examples, shuffle=True, batch_size=batch_size)

        # Define loss
        train_loss = losses.CosineSimilarityLoss(self.model)

        # Train
        self.model.fit(
            train_objectives=[(train_dataloader, train_loss)],
            epochs=epochs,
            warmup_steps=warmup_steps,
            show_progress_bar=True
        )

        # Save model
        output_path = f"models/embeddings/fine-tuned-{datetime.now().strftime('%Y%m%d')}"
        self.model.save(output_path)

        return output_path

    def evaluate(self, test_data: List[Tuple[str, str, str]]) -> dict:
        """Evaluate model on test data."""
        from sentence_transformers import evaluation

        # Prepare evaluation data
        anchors = [t[0] for t in test_data]
        positives = [t[1] for t in test_data]
        negatives = [t[2] for t in test_data]

        evaluator = evaluation.TripletEvaluator(
            anchors=anchors,
            positives=positives,
            negatives=negatives,
            name="triplet_eval"
        )

        score = evaluator(self.model)

        return {
            "triplet_accuracy": score,
            "test_size": len(test_data)
        }


class WeeklyEmbeddingTrainingJob:
    """Scheduled job for weekly embedding fine-tuning."""

    def __init__(self, db_connection, model_registry, config):
        self.db = db_connection
        self.registry = model_registry
        self.config = config

    def run(self):
        """Execute weekly training job."""
        job_id = str(uuid.uuid4())

        # Log job start
        self.db.execute("""
            INSERT INTO training_jobs (id, training_type, model_type, status, created_at)
            VALUES (%s, 'embedding', 'sentence-transformer', 'running', NOW())
        """, (job_id,))

        try:
            # Get training data
            tuner = EmbeddingFineTuner(db_connection=self.db)
            training_data = tuner.get_training_data()

            if len(training_data) < self.config.min_training_examples:
                self._log_skip(job_id, f"Only {len(training_data)} examples, need {self.config.min_training_examples}")
                return

            # Split train/test
            split_idx = int(len(training_data) * 0.9)
            train_data = training_data[:split_idx]
            test_data = training_data[split_idx:]

            # Train
            model_path = tuner.fine_tune(train_data)

            # Evaluate
            metrics = tuner.evaluate(test_data)

            # Compare with current model
            current_metrics = self._get_current_model_metrics()

            if metrics['triplet_accuracy'] > current_metrics.get('triplet_accuracy', 0):
                # New model is better - register and start A/B test
                version_id = self.registry.register(
                    model_type='embedding',
                    model_path=model_path,
                    metrics=metrics,
                    training_job_id=job_id
                )

                # Start A/B test with 10% traffic
                self.registry.set_traffic(version_id, percentage=10)

                self._log_success(job_id, metrics, model_path)
            else:
                self._log_skip(job_id, f"New model not better: {metrics} vs {current_metrics}")

            # Mark training data as used
            self._mark_data_used(training_data)

        except Exception as e:
            self._log_failure(job_id, str(e))
            raise

    def _get_current_model_metrics(self) -> dict:
        """Get metrics for currently active model."""
        row = self.db.query("""
            SELECT evaluation_metrics
            FROM model_versions
            WHERE model_type = 'embedding' AND is_active = TRUE
            ORDER BY activated_at DESC LIMIT 1
        """).fetchone()

        return row['evaluation_metrics'] if row else {}

    def _mark_data_used(self, training_data):
        """Mark training data as used."""
        # Implementation would mark records in training_data table
        pass

    def _log_success(self, job_id: str, metrics: dict, model_path: str):
        self.db.execute("""
            UPDATE training_jobs
            SET status = 'completed', metrics = %s, completed_at = NOW()
            WHERE id = %s
        """, (json.dumps(metrics), job_id))

    def _log_skip(self, job_id: str, reason: str):
        self.db.execute("""
            UPDATE training_jobs
            SET status = 'skipped', error_message = %s, completed_at = NOW()
            WHERE id = %s
        """, (reason, job_id))

    def _log_failure(self, job_id: str, error: str):
        self.db.execute("""
            UPDATE training_jobs
            SET status = 'failed', error_message = %s, completed_at = NOW()
            WHERE id = %s
        """, (error, job_id))
```

---

## Part 4: LLM Fine-Tuning

### Monthly LLM Training Pipeline

```python
import openai
from typing import List, Dict
import json


class LLMFineTuner:
    """Fine-tune LLM on company Q&A pairs."""

    def __init__(self, api_key: str, db_connection):
        self.client = openai.OpenAI(api_key=api_key)
        self.db = db_connection

    def get_training_data(self, min_quality: float = 0.8) -> List[Dict]:
        """Get validated training examples."""
        rows = self.db.query("""
            SELECT system_prompt, user_message, assistant_message
            FROM training_data
            WHERE training_type = 'generation'
            AND validated = TRUE
            AND used_in_training = FALSE
            AND quality_score >= %s
        """, (min_quality,)).fetchall()

        return [
            {
                "messages": [
                    {"role": "system", "content": r['system_prompt']},
                    {"role": "user", "content": r['user_message']},
                    {"role": "assistant", "content": r['assistant_message']}
                ]
            }
            for r in rows
        ]

    def prepare_training_file(self, examples: List[Dict]) -> str:
        """Create JSONL file for fine-tuning."""
        file_path = f"/tmp/training_{datetime.now().strftime('%Y%m%d')}.jsonl"

        with open(file_path, 'w') as f:
            for example in examples:
                f.write(json.dumps(example) + '\n')

        return file_path

    def upload_training_file(self, file_path: str) -> str:
        """Upload training file to OpenAI."""
        with open(file_path, 'rb') as f:
            response = self.client.files.create(
                file=f,
                purpose='fine-tune'
            )
        return response.id

    def start_fine_tuning(
        self,
        training_file_id: str,
        base_model: str = "gpt-3.5-turbo",
        epochs: int = 3
    ) -> str:
        """Start fine-tuning job."""
        response = self.client.fine_tuning.jobs.create(
            training_file=training_file_id,
            model=base_model,
            hyperparameters={
                "n_epochs": epochs
            }
        )
        return response.id

    def get_job_status(self, job_id: str) -> Dict:
        """Check fine-tuning job status."""
        response = self.client.fine_tuning.jobs.retrieve(job_id)
        return {
            "status": response.status,
            "fine_tuned_model": response.fine_tuned_model,
            "trained_tokens": response.trained_tokens,
            "error": response.error
        }


class MonthlyLLMTrainingJob:
    """Scheduled job for monthly LLM fine-tuning."""

    MIN_EXAMPLES = 500  # Minimum examples for fine-tuning

    def __init__(self, db_connection, model_registry, config):
        self.db = db_connection
        self.registry = model_registry
        self.config = config
        self.tuner = LLMFineTuner(config.openai_api_key, db_connection)

    def run(self):
        """Execute monthly LLM training job."""
        job_id = str(uuid.uuid4())

        self.db.execute("""
            INSERT INTO training_jobs (id, training_type, model_type, status, created_at)
            VALUES (%s, 'llm', 'gpt-3.5-turbo', 'pending', NOW())
        """, (job_id,))

        try:
            # Get training data
            examples = self.tuner.get_training_data()

            if len(examples) < self.MIN_EXAMPLES:
                self._log_skip(job_id, f"Only {len(examples)} examples, need {self.MIN_EXAMPLES}")
                return

            # Human review sample (10%)
            sample_size = min(50, len(examples) // 10)
            self._queue_human_review(examples[:sample_size])

            # Prepare and upload training file
            file_path = self.tuner.prepare_training_file(examples)
            file_id = self.tuner.upload_training_file(file_path)

            # Start fine-tuning
            ft_job_id = self.tuner.start_fine_tuning(file_id)

            # Update job with external reference
            self.db.execute("""
                UPDATE training_jobs
                SET status = 'running', external_job_id = %s, started_at = NOW()
                WHERE id = %s
            """, (ft_job_id, job_id))

            # Poll for completion (or use webhook)
            self._wait_for_completion(job_id, ft_job_id)

        except Exception as e:
            self._log_failure(job_id, str(e))
            raise

    def _wait_for_completion(self, job_id: str, ft_job_id: str):
        """Poll OpenAI for job completion."""
        import time

        while True:
            status = self.tuner.get_job_status(ft_job_id)

            if status['status'] == 'succeeded':
                # Register new model
                self.registry.register(
                    model_type='generation',
                    external_model_id=status['fine_tuned_model'],
                    training_job_id=job_id
                )

                # Start gradual rollout at 10%
                self.registry.set_traffic(
                    status['fine_tuned_model'],
                    percentage=10
                )

                self._log_success(job_id, {"model": status['fine_tuned_model']})
                break

            elif status['status'] == 'failed':
                self._log_failure(job_id, status['error'])
                break

            time.sleep(60)  # Check every minute

    def _queue_human_review(self, samples: List[Dict]):
        """Queue samples for human review before training."""
        for sample in samples:
            self.db.execute("""
                INSERT INTO human_review_queue (id, content, review_type, created_at)
                VALUES (%s, %s, 'training_data', NOW())
            """, (str(uuid.uuid4()), json.dumps(sample)))
```

---

## Part 5: A/B Testing & Model Promotion

### A/B Testing Framework

```python
import random
from typing import Optional


class ModelRouter:
    """Route requests to different model versions for A/B testing."""

    def __init__(self, db_connection):
        self.db = db_connection
        self._cache = {}
        self._cache_ttl = 60  # Refresh every 60 seconds

    def get_model_version(self, model_type: str, user_id: Optional[str] = None) -> str:
        """Get model version for a request."""
        versions = self._get_active_versions(model_type)

        if not versions:
            raise ValueError(f"No active {model_type} models")

        # If only one version, return it
        if len(versions) == 1:
            return versions[0]['external_model_id'] or versions[0]['model_path']

        # Weighted random selection based on traffic percentage
        total_traffic = sum(v['traffic_percentage'] for v in versions)
        rand = random.uniform(0, total_traffic)

        cumulative = 0
        for version in versions:
            cumulative += version['traffic_percentage']
            if rand <= cumulative:
                return version['external_model_id'] or version['model_path']

        return versions[-1]['external_model_id'] or versions[-1]['model_path']

    def _get_active_versions(self, model_type: str) -> List[Dict]:
        """Get all active model versions."""
        return self.db.query("""
            SELECT id, model_path, external_model_id, traffic_percentage
            FROM model_versions
            WHERE model_type = %s AND is_active = TRUE
            ORDER BY traffic_percentage DESC
        """, (model_type,)).fetchall()


class ModelPromoter:
    """Gradually promote or rollback models based on metrics."""

    TRAFFIC_STAGES = [10, 25, 50, 75, 100]
    MIN_QUERIES_PER_STAGE = 100
    MIN_SATISFACTION_RATE = 0.80

    def __init__(self, db_connection, model_registry):
        self.db = db_connection
        self.registry = model_registry

    def check_and_promote(self, model_version_id: str):
        """Check if model should be promoted to next traffic stage."""
        version = self.registry.get(model_version_id)
        current_traffic = version['traffic_percentage']

        # Get performance metrics
        metrics = self._get_model_metrics(model_version_id)

        if metrics['query_count'] < self.MIN_QUERIES_PER_STAGE:
            return  # Not enough data yet

        if metrics['satisfaction_rate'] >= self.MIN_SATISFACTION_RATE:
            # Promote to next stage
            next_traffic = self._get_next_stage(current_traffic)
            if next_traffic:
                self.registry.set_traffic(model_version_id, next_traffic)

                if next_traffic == 100:
                    # Full promotion - demote old model
                    self._demote_previous_model(version['model_type'])

        elif metrics['satisfaction_rate'] < self.MIN_SATISFACTION_RATE - 0.10:
            # Significant regression - rollback
            self._rollback(model_version_id)

    def _get_model_metrics(self, model_version_id: str) -> Dict:
        """Get performance metrics for model version."""
        version = self.registry.get(model_version_id)

        # Get metrics since last traffic change
        row = self.db.query("""
            SELECT
                COUNT(*) as query_count,
                COUNT(CASE WHEN f.feedback_type = 'thumbs_up' THEN 1 END) as thumbs_up,
                COUNT(CASE WHEN f.feedback_type = 'thumbs_down' THEN 1 END) as thumbs_down
            FROM responses r
            LEFT JOIN feedback f ON r.id = f.response_id
            WHERE r.model_version = %s
            AND r.created_at > %s
        """, (version['version'], version['last_traffic_change'])).fetchone()

        total_feedback = row['thumbs_up'] + row['thumbs_down']
        satisfaction = row['thumbs_up'] / total_feedback if total_feedback > 0 else 0.5

        return {
            'query_count': row['query_count'],
            'satisfaction_rate': satisfaction,
            'thumbs_up': row['thumbs_up'],
            'thumbs_down': row['thumbs_down']
        }

    def _get_next_stage(self, current: int) -> Optional[int]:
        """Get next traffic stage."""
        for stage in self.TRAFFIC_STAGES:
            if stage > current:
                return stage
        return None

    def _rollback(self, model_version_id: str):
        """Rollback to previous stable model."""
        version = self.registry.get(model_version_id)

        # Deactivate this version
        self.registry.deactivate(model_version_id)

        # Ensure previous version gets 100% traffic
        previous = self.db.query("""
            SELECT id FROM model_versions
            WHERE model_type = %s AND id != %s AND is_active = TRUE
            ORDER BY activated_at DESC LIMIT 1
        """, (version['model_type'], model_version_id)).fetchone()

        if previous:
            self.registry.set_traffic(previous['id'], 100)

    def _demote_previous_model(self, model_type: str):
        """Demote previous model when new one reaches 100%."""
        self.db.execute("""
            UPDATE model_versions
            SET is_active = FALSE, deactivated_at = NOW()
            WHERE model_type = %s
            AND traffic_percentage < 100
            AND is_active = TRUE
        """, (model_type,))
```

---

## Part 6: Scheduled Jobs

### Celery Task Definitions

```python
from celery import Celery
from celery.schedules import crontab

app = Celery('training')


# Real-time tasks (triggered by feedback)
@app.task
def generate_training_example(feedback_id: str):
    """Generate training data from positive feedback."""
    generator = TrainingDataGenerator(get_db(), get_chunk_repo())
    generator.generate_from_positive_feedback(feedback_id)


@app.task
def process_correction(feedback_id: str):
    """Process user correction for training."""
    generator = TrainingDataGenerator(get_db(), get_chunk_repo())
    generator.generate_from_correction(feedback_id)


# Scheduled jobs
@app.task
def daily_feedback_aggregation():
    """Aggregate feedback metrics daily."""
    db = get_db()
    db.execute("""
        INSERT INTO feedback_analytics (date, total_queries, total_responses, ...)
        SELECT
            DATE(created_at),
            COUNT(DISTINCT q.id),
            COUNT(DISTINCT r.id),
            ...
        FROM queries q
        JOIN responses r ON ...
        WHERE DATE(q.created_at) = CURRENT_DATE - 1
        GROUP BY DATE(created_at)
    """)


@app.task
def weekly_embedding_training():
    """Weekly embedding fine-tuning."""
    job = WeeklyEmbeddingTrainingJob(get_db(), get_registry(), get_config())
    job.run()


@app.task
def monthly_llm_training():
    """Monthly LLM fine-tuning."""
    job = MonthlyLLMTrainingJob(get_db(), get_registry(), get_config())
    job.run()


@app.task
def hourly_model_promotion_check():
    """Check if models should be promoted/rolled back."""
    promoter = ModelPromoter(get_db(), get_registry())

    # Check all models in A/B test
    versions = get_db().query("""
        SELECT id FROM model_versions
        WHERE is_active = TRUE AND traffic_percentage < 100
    """).fetchall()

    for version in versions:
        promoter.check_and_promote(version['id'])


# Schedule configuration
app.conf.beat_schedule = {
    'daily-feedback-aggregation': {
        'task': 'tasks.daily_feedback_aggregation',
        'schedule': crontab(hour=1, minute=0),  # 1 AM daily
    },
    'weekly-embedding-training': {
        'task': 'tasks.weekly_embedding_training',
        'schedule': crontab(day_of_week=0, hour=2),  # Sunday 2 AM
    },
    'monthly-llm-training': {
        'task': 'tasks.monthly_llm_training',
        'schedule': crontab(day_of_month=1, hour=3),  # 1st of month, 3 AM
    },
    'hourly-promotion-check': {
        'task': 'tasks.hourly_model_promotion_check',
        'schedule': crontab(minute=0),  # Every hour
    },
}
```

---

## Part 7: Analytics Dashboard

### Key Metrics to Track

```python
class FeedbackAnalytics:
    """Analytics for feedback and model performance."""

    def get_daily_metrics(self, date: str) -> Dict:
        """Get daily feedback metrics."""
        return self.db.query("""
            SELECT
                total_queries,
                total_responses,
                total_feedback,
                thumbs_up_count,
                thumbs_down_count,
                satisfaction_rate,
                feedback_rate
            FROM feedback_analytics
            WHERE date = %s
        """, (date,)).fetchone()

    def get_model_comparison(self) -> List[Dict]:
        """Compare performance across model versions."""
        return self.db.query("""
            SELECT
                model_name,
                model_version,
                traffic_percentage,
                AVG(satisfaction_rate) as avg_satisfaction,
                COUNT(*) as response_count
            FROM v_model_performance
            WHERE date >= CURRENT_DATE - 7
            GROUP BY model_name, model_version, traffic_percentage
        """).fetchall()

    def get_training_data_growth(self) -> List[Dict]:
        """Track training data accumulation over time."""
        return self.db.query("""
            SELECT
                DATE(created_at) as date,
                training_type,
                COUNT(*) as examples_created,
                SUM(CASE WHEN validated THEN 1 ELSE 0 END) as validated_count
            FROM training_data
            WHERE created_at >= CURRENT_DATE - 30
            GROUP BY DATE(created_at), training_type
            ORDER BY date
        """).fetchall()

    def get_unanswered_queries(self) -> List[Dict]:
        """Find queries that couldn't be answered."""
        return self.db.query("""
            SELECT
                q.query_text,
                r.confidence_score,
                COUNT(*) as occurrence_count
            FROM queries q
            JOIN responses r ON q.id = r.query_id
            WHERE r.confidence_score < 0.5
            OR EXISTS (
                SELECT 1 FROM feedback f
                WHERE f.response_id = r.id
                AND f.feedback_type = 'thumbs_down'
            )
            GROUP BY q.query_text, r.confidence_score
            ORDER BY occurrence_count DESC
            LIMIT 50
        """).fetchall()
```

---

## Summary

This feedback and training system provides:

1. **Real-time feedback capture** - Thumbs up/down, corrections, reports
2. **Automatic training data generation** - From positive feedback and corrections
3. **Weekly embedding fine-tuning** - Improves retrieval accuracy
4. **Monthly LLM fine-tuning** - Improves response quality
5. **A/B testing with gradual rollout** - Safe model deployment
6. **Automatic rollback** - If new model performs worse
7. **Analytics dashboard** - Track improvement over time

The system creates a virtuous cycle: more customer feedback → better training data → improved models → happier customers → more feedback.
