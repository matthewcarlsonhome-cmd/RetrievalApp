"""
Query Analytics Module.

=============================================================================
INNOVATION: DEEP INSIGHTS INTO RAG SYSTEM BEHAVIOR
=============================================================================

Production RAG systems generate vast amounts of operational data:
- Query patterns and frequencies
- Retrieval success/failure patterns
- Latency distributions
- User behavior signals

This module transforms that data into actionable insights:

1. QUERY PATTERN ANALYSIS
   - What queries are common?
   - What query types perform poorly?
   - Are there emerging query patterns?

2. RETRIEVAL QUALITY TRENDS
   - Is retrieval quality stable or drifting?
   - Which document categories have issues?
   - Where are the knowledge gaps?

3. PERFORMANCE ANALYTICS
   - Latency trends and anomalies
   - Cost optimization opportunities
   - Capacity planning data

4. USER BEHAVIOR INSIGHTS
   - Session patterns
   - Query refinement behavior
   - Satisfaction signals

=============================================================================
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
from collections import defaultdict
import json
import math


@dataclass
class QueryRecord:
    """Record of a single query."""
    query_id: str
    query: str
    timestamp: datetime
    latency_ms: float
    retrieval_count: int
    top_score: float
    confidence: float
    fallback_used: bool
    user_feedback: Optional[float] = None  # 0-1 if provided
    session_id: Optional[str] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class QueryCluster:
    """A cluster of similar queries."""
    cluster_id: str
    representative_query: str
    query_count: int
    avg_confidence: float
    avg_latency_ms: float
    success_rate: float
    example_queries: list[str]


@dataclass
class PerformanceTrend:
    """Trend analysis for a metric."""
    metric_name: str
    current_value: float
    previous_value: float
    change_percent: float
    trend: str  # "improving", "stable", "degrading"
    alert: bool


@dataclass
class KnowledgeGap:
    """Identified gap in knowledge base."""
    topic: str
    query_examples: list[str]
    frequency: int
    avg_confidence: float
    suggested_action: str


@dataclass
class AnalyticsReport:
    """Comprehensive analytics report."""
    period_start: datetime
    period_end: datetime
    total_queries: int

    # Query analysis
    unique_queries: int
    query_clusters: list[QueryCluster]
    top_queries: list[tuple[str, int]]

    # Performance
    avg_latency_ms: float
    p95_latency_ms: float
    avg_confidence: float
    fallback_rate: float

    # Trends
    performance_trends: list[PerformanceTrend]

    # Issues
    knowledge_gaps: list[KnowledgeGap]
    low_performing_patterns: list[dict]

    # Recommendations
    recommendations: list[str]

    def to_markdown(self) -> str:
        """Generate markdown report."""
        lines = [
            "# RAG Analytics Report",
            f"Period: {self.period_start.strftime('%Y-%m-%d')} to {self.period_end.strftime('%Y-%m-%d')}",
            "",
            "## Summary",
            f"- **Total Queries**: {self.total_queries:,}",
            f"- **Unique Queries**: {self.unique_queries:,}",
            f"- **Avg Latency**: {self.avg_latency_ms:.0f}ms",
            f"- **Avg Confidence**: {self.avg_confidence:.2%}",
            f"- **Fallback Rate**: {self.fallback_rate:.2%}",
            "",
        ]

        if self.performance_trends:
            lines.extend([
                "## Performance Trends",
                "",
            ])
            for trend in self.performance_trends:
                icon = {"improving": "📈", "stable": "➡️", "degrading": "📉"}[trend.trend]
                alert = " ⚠️" if trend.alert else ""
                lines.append(
                    f"- {icon} **{trend.metric_name}**: {trend.current_value:.2f} "
                    f"({trend.change_percent:+.1f}%){alert}"
                )
            lines.append("")

        if self.knowledge_gaps:
            lines.extend([
                "## Knowledge Gaps Detected",
                "",
            ])
            for gap in self.knowledge_gaps[:5]:
                lines.extend([
                    f"### {gap.topic}",
                    f"- Frequency: {gap.frequency} queries",
                    f"- Avg Confidence: {gap.avg_confidence:.2%}",
                    f"- Example: \"{gap.query_examples[0]}\"",
                    f"- Suggested: {gap.suggested_action}",
                    "",
                ])

        if self.recommendations:
            lines.extend([
                "## Recommendations",
                "",
            ])
            for i, rec in enumerate(self.recommendations, 1):
                lines.append(f"{i}. {rec}")
            lines.append("")

        return "\n".join(lines)


class QueryAnalytics:
    """
    Analytics engine for RAG query data.

    Usage:
        analytics = QueryAnalytics()

        # Record queries as they happen
        analytics.record_query(QueryRecord(...))

        # Or batch import from logs
        analytics.import_from_logs(log_records)

        # Generate reports
        report = analytics.generate_report(days=7)
        print(report.to_markdown())

        # Get specific insights
        gaps = analytics.find_knowledge_gaps()
        trends = analytics.analyze_trends(metric="confidence")
    """

    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = storage_path
        self._records: list[QueryRecord] = []
        self._query_counts: defaultdict = defaultdict(int)

        if storage_path:
            self._load()

    def record_query(self, record: QueryRecord) -> None:
        """Record a query for analytics."""
        self._records.append(record)
        self._query_counts[record.query.lower().strip()] += 1

        # Persist periodically
        if len(self._records) % 100 == 0 and self.storage_path:
            self._save()

    def import_from_logs(self, records: list[dict]) -> int:
        """Import query records from log data."""
        imported = 0
        for data in records:
            try:
                record = QueryRecord(
                    query_id=data.get("query_id", ""),
                    query=data["query"],
                    timestamp=datetime.fromisoformat(data["timestamp"]),
                    latency_ms=data.get("latency_ms", 0),
                    retrieval_count=data.get("retrieval_count", 0),
                    top_score=data.get("top_score", 0),
                    confidence=data.get("confidence", 0),
                    fallback_used=data.get("fallback_used", False),
                    user_feedback=data.get("user_feedback"),
                    session_id=data.get("session_id"),
                )
                self._records.append(record)
                imported += 1
            except (KeyError, ValueError):
                continue

        return imported

    def generate_report(
        self,
        days: int = 7,
        end_date: Optional[datetime] = None,
    ) -> AnalyticsReport:
        """Generate comprehensive analytics report."""
        end = end_date or datetime.utcnow()
        start = end - timedelta(days=days)

        # Filter to period
        period_records = [
            r for r in self._records
            if start <= r.timestamp <= end
        ]

        if not period_records:
            return self._empty_report(start, end)

        # Basic stats
        unique_queries = len(set(r.query.lower().strip() for r in period_records))
        avg_latency = sum(r.latency_ms for r in period_records) / len(period_records)
        latencies = sorted(r.latency_ms for r in period_records)
        p95_latency = latencies[int(len(latencies) * 0.95)] if latencies else 0
        avg_confidence = sum(r.confidence for r in period_records) / len(period_records)
        fallback_rate = sum(1 for r in period_records if r.fallback_used) / len(period_records)

        # Query clusters
        clusters = self._cluster_queries(period_records)

        # Top queries
        query_freq = defaultdict(int)
        for r in period_records:
            query_freq[r.query.lower().strip()] += 1
        top_queries = sorted(query_freq.items(), key=lambda x: -x[1])[:10]

        # Trends
        trends = self._analyze_trends(period_records, days)

        # Knowledge gaps
        gaps = self._find_knowledge_gaps(period_records)

        # Low performing patterns
        low_performing = self._find_low_performers(period_records)

        # Generate recommendations
        recommendations = self._generate_recommendations(
            avg_confidence, fallback_rate, gaps, trends
        )

        return AnalyticsReport(
            period_start=start,
            period_end=end,
            total_queries=len(period_records),
            unique_queries=unique_queries,
            query_clusters=clusters,
            top_queries=top_queries,
            avg_latency_ms=avg_latency,
            p95_latency_ms=p95_latency,
            avg_confidence=avg_confidence,
            fallback_rate=fallback_rate,
            performance_trends=trends,
            knowledge_gaps=gaps,
            low_performing_patterns=low_performing,
            recommendations=recommendations,
        )

    def find_knowledge_gaps(
        self,
        confidence_threshold: float = 0.5,
        min_frequency: int = 3,
    ) -> list[KnowledgeGap]:
        """Find topics where the system performs poorly."""
        # Group low-confidence queries by topic
        low_conf_queries = [
            r for r in self._records
            if r.confidence < confidence_threshold
        ]

        # Simple topic extraction (could use LLM for better results)
        topic_queries = defaultdict(list)
        for r in low_conf_queries:
            words = r.query.lower().split()
            # Use first significant word as topic proxy
            topic = next(
                (w for w in words if len(w) > 3 and w not in {
                    'what', 'how', 'why', 'when', 'where', 'which', 'does', 'can'
                }),
                'other'
            )
            topic_queries[topic].append(r)

        gaps = []
        for topic, queries in topic_queries.items():
            if len(queries) >= min_frequency:
                gaps.append(KnowledgeGap(
                    topic=topic,
                    query_examples=[q.query for q in queries[:3]],
                    frequency=len(queries),
                    avg_confidence=sum(q.confidence for q in queries) / len(queries),
                    suggested_action=f"Add content about '{topic}' to knowledge base"
                ))

        return sorted(gaps, key=lambda g: -g.frequency)[:10]

    def _cluster_queries(self, records: list[QueryRecord]) -> list[QueryCluster]:
        """Cluster similar queries together."""
        # Simple clustering by normalized query text
        clusters = defaultdict(list)

        for r in records:
            # Normalize query for clustering
            normalized = ' '.join(sorted(r.query.lower().split()))
            clusters[normalized].append(r)

        result = []
        for normalized, queries in clusters.items():
            if len(queries) >= 2:  # Only clusters with multiple queries
                result.append(QueryCluster(
                    cluster_id=normalized[:20],
                    representative_query=queries[0].query,
                    query_count=len(queries),
                    avg_confidence=sum(q.confidence for q in queries) / len(queries),
                    avg_latency_ms=sum(q.latency_ms for q in queries) / len(queries),
                    success_rate=sum(1 for q in queries if q.confidence > 0.5) / len(queries),
                    example_queries=[q.query for q in queries[:3]],
                ))

        return sorted(result, key=lambda c: -c.query_count)[:20]

    def _analyze_trends(
        self,
        records: list[QueryRecord],
        days: int,
    ) -> list[PerformanceTrend]:
        """Analyze performance trends over time."""
        if len(records) < 10:
            return []

        # Split into two periods
        mid = len(records) // 2
        first_half = records[:mid]
        second_half = records[mid:]

        trends = []

        # Confidence trend
        conf_first = sum(r.confidence for r in first_half) / len(first_half)
        conf_second = sum(r.confidence for r in second_half) / len(second_half)
        conf_change = ((conf_second - conf_first) / conf_first * 100) if conf_first > 0 else 0

        trends.append(PerformanceTrend(
            metric_name="Confidence",
            current_value=conf_second,
            previous_value=conf_first,
            change_percent=conf_change,
            trend="improving" if conf_change > 5 else ("degrading" if conf_change < -5 else "stable"),
            alert=conf_change < -10,
        ))

        # Latency trend
        lat_first = sum(r.latency_ms for r in first_half) / len(first_half)
        lat_second = sum(r.latency_ms for r in second_half) / len(second_half)
        lat_change = ((lat_second - lat_first) / lat_first * 100) if lat_first > 0 else 0

        trends.append(PerformanceTrend(
            metric_name="Latency (ms)",
            current_value=lat_second,
            previous_value=lat_first,
            change_percent=lat_change,
            trend="degrading" if lat_change > 10 else ("improving" if lat_change < -10 else "stable"),
            alert=lat_change > 25,
        ))

        # Fallback rate trend
        fb_first = sum(1 for r in first_half if r.fallback_used) / len(first_half)
        fb_second = sum(1 for r in second_half if r.fallback_used) / len(second_half)
        fb_change = ((fb_second - fb_first) / max(fb_first, 0.01) * 100)

        trends.append(PerformanceTrend(
            metric_name="Fallback Rate",
            current_value=fb_second,
            previous_value=fb_first,
            change_percent=fb_change,
            trend="degrading" if fb_change > 20 else ("improving" if fb_change < -20 else "stable"),
            alert=fb_second > 0.2,
        ))

        return trends

    def _find_low_performers(self, records: list[QueryRecord]) -> list[dict]:
        """Find query patterns that consistently perform poorly."""
        # Group by query pattern
        patterns = defaultdict(list)
        for r in records:
            # Extract pattern (first word + question type)
            words = r.query.lower().split()
            pattern = words[0] if words else "unknown"
            patterns[pattern].append(r)

        low_performers = []
        for pattern, queries in patterns.items():
            if len(queries) >= 5:
                avg_conf = sum(q.confidence for q in queries) / len(queries)
                if avg_conf < 0.5:
                    low_performers.append({
                        "pattern": pattern,
                        "count": len(queries),
                        "avg_confidence": avg_conf,
                        "examples": [q.query for q in queries[:2]],
                    })

        return sorted(low_performers, key=lambda x: x["avg_confidence"])[:5]

    def _generate_recommendations(
        self,
        avg_confidence: float,
        fallback_rate: float,
        gaps: list[KnowledgeGap],
        trends: list[PerformanceTrend],
    ) -> list[str]:
        """Generate actionable recommendations."""
        recs = []

        if avg_confidence < 0.6:
            recs.append(
                "Average confidence is low. Consider reviewing retrieval parameters "
                "or adding more comprehensive content to the knowledge base."
            )

        if fallback_rate > 0.15:
            recs.append(
                f"Fallback rate is {fallback_rate:.1%}. Many queries aren't finding "
                "relevant content. Review knowledge gaps and consider content expansion."
            )

        if gaps:
            top_gap = gaps[0]
            recs.append(
                f"Knowledge gap detected around '{top_gap.topic}' ({top_gap.frequency} queries). "
                f"Consider adding content about this topic."
            )

        for trend in trends:
            if trend.alert:
                recs.append(
                    f"Alert: {trend.metric_name} has changed significantly "
                    f"({trend.change_percent:+.1f}%). Investigate potential causes."
                )

        if not recs:
            recs.append("System is performing within normal parameters. Continue monitoring.")

        return recs

    def _empty_report(self, start: datetime, end: datetime) -> AnalyticsReport:
        """Generate empty report when no data available."""
        return AnalyticsReport(
            period_start=start,
            period_end=end,
            total_queries=0,
            unique_queries=0,
            query_clusters=[],
            top_queries=[],
            avg_latency_ms=0,
            p95_latency_ms=0,
            avg_confidence=0,
            fallback_rate=0,
            performance_trends=[],
            knowledge_gaps=[],
            low_performing_patterns=[],
            recommendations=["No query data available for analysis."],
        )

    def _save(self) -> None:
        """Persist records to storage."""
        if not self.storage_path:
            return

        from pathlib import Path
        path = Path(self.storage_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = [
            {
                "query_id": r.query_id,
                "query": r.query,
                "timestamp": r.timestamp.isoformat(),
                "latency_ms": r.latency_ms,
                "retrieval_count": r.retrieval_count,
                "top_score": r.top_score,
                "confidence": r.confidence,
                "fallback_used": r.fallback_used,
                "user_feedback": r.user_feedback,
                "session_id": r.session_id,
            }
            for r in self._records[-10000:]  # Keep last 10K
        ]

        with open(path, 'w') as f:
            json.dump(data, f)

    def _load(self) -> None:
        """Load records from storage."""
        if not self.storage_path:
            return

        from pathlib import Path
        path = Path(self.storage_path)

        if not path.exists():
            return

        try:
            with open(path, 'r') as f:
                data = json.load(f)
            self.import_from_logs(data)
        except (json.JSONDecodeError, IOError):
            pass
