"""
Observability Module.

"The most ignored part: observability. Logging misses, tracking latency,
measuring answer quality over time and building feedback loops so the
system actually learns instead of rotting silently."
"""

from retrieval_app.observability.logger import RAGLogger
from retrieval_app.observability.metrics import MetricsCollector
from retrieval_app.observability.feedback import FeedbackCollector

__all__ = ["RAGLogger", "MetricsCollector", "FeedbackCollector"]
