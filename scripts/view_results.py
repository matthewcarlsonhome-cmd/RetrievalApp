#!/usr/bin/env python3
"""
View and analyze resume matching results.
"""

import json
import sys
from pathlib import Path
import argparse


def load_results(results_path: Path) -> dict:
    """Load results from JSON file."""
    with open(results_path) as f:
        return json.load(f)


def print_summary(results: dict):
    """Print high-level summary of results."""
    job_matches = results.get("job_matches", [])

    print("=" * 70)
    print("MATCHING RESULTS SUMMARY")
    print("=" * 70)
    print(f"\nGenerated: {results.get('generated_at', 'Unknown')}")
    print(f"Configuration:")
    config = results.get("config", {})
    print(f"  - Top K candidates: {config.get('top_k', 'N/A')}")
    print(f"  - Semantic weight: {config.get('semantic_weight', 'N/A')}")
    print(f"  - Lexical weight: {config.get('lexical_weight', 'N/A')}")

    print(f"\nTotal jobs matched: {len(job_matches)}")

    if job_matches:
        avg_score = sum(
            jm["top_candidates"][0]["match_score"]
            for jm in job_matches
            if jm["top_candidates"]
        ) / len(job_matches)
        print(f"Average top candidate score: {avg_score:.3f}")


def print_detailed_results(results: dict, limit: int = None):
    """Print detailed matching results for each job."""
    job_matches = results.get("job_matches", [])

    if limit:
        job_matches = job_matches[:limit]

    for job in job_matches:
        print(f"\n{'=' * 70}")
        print(f"JOB: {job['job_title']}")
        print(f"Employer: {job['employer']}")
        print(f"Job ID: {job['job_id']}")
        print(f"Processing time: {job['processing_time_ms']:.1f}ms")
        print(f"{'=' * 70}")

        for candidate in job["top_candidates"]:
            print(f"\n  #{candidate['rank']}: {candidate['candidate_name']}")
            print(f"      Resume ID: {candidate['resume_id']}")
            print(f"      Match Score: {candidate['match_score']:.4f}")

            breakdown = candidate.get("score_breakdown", {})
            if breakdown:
                print(f"      Score Breakdown:")
                for key, value in breakdown.items():
                    print(f"        - {key}: {value:.4f}")

            highlights = candidate.get("match_highlights", [])
            if highlights:
                print(f"      Match Highlights:")
                for h in highlights:
                    print(f"        ✓ {h}")


def print_ehr_analysis(results: dict):
    """Analyze EHR system matching patterns."""
    job_matches = results.get("job_matches", [])

    # Count EHR matches in highlights
    ehr_matches = {}
    for job in job_matches:
        for candidate in job["top_candidates"]:
            for highlight in candidate.get("match_highlights", []):
                if "EHR" in highlight or "Epic" in highlight or "Cerner" in highlight:
                    ehr_matches[highlight] = ehr_matches.get(highlight, 0) + 1

    print("\n" + "=" * 70)
    print("EHR SYSTEM MATCHING ANALYSIS")
    print("=" * 70)

    for highlight, count in sorted(ehr_matches.items(), key=lambda x: -x[1])[:10]:
        print(f"  {count:3d}x - {highlight}")


def print_score_distribution(results: dict):
    """Analyze score distribution."""
    job_matches = results.get("job_matches", [])

    all_scores = []
    for job in job_matches:
        for candidate in job["top_candidates"]:
            all_scores.append(candidate["match_score"])

    if not all_scores:
        return

    print("\n" + "=" * 70)
    print("SCORE DISTRIBUTION")
    print("=" * 70)

    # Calculate statistics
    all_scores.sort(reverse=True)
    avg = sum(all_scores) / len(all_scores)
    median = all_scores[len(all_scores) // 2]
    top_10_pct = all_scores[len(all_scores) // 10] if len(all_scores) >= 10 else all_scores[0]

    print(f"\n  Total matches analyzed: {len(all_scores)}")
    print(f"  Average score: {avg:.4f}")
    print(f"  Median score: {median:.4f}")
    print(f"  Top 10% threshold: {top_10_pct:.4f}")
    print(f"  Highest score: {all_scores[0]:.4f}")
    print(f"  Lowest score: {all_scores[-1]:.4f}")

    # Score buckets
    buckets = {"0.8+": 0, "0.6-0.8": 0, "0.4-0.6": 0, "0.2-0.4": 0, "<0.2": 0}
    for score in all_scores:
        if score >= 0.8:
            buckets["0.8+"] += 1
        elif score >= 0.6:
            buckets["0.6-0.8"] += 1
        elif score >= 0.4:
            buckets["0.4-0.6"] += 1
        elif score >= 0.2:
            buckets["0.2-0.4"] += 1
        else:
            buckets["<0.2"] += 1

    print(f"\n  Score Distribution:")
    for bucket, count in buckets.items():
        pct = (count / len(all_scores)) * 100
        bar = "█" * int(pct / 2)
        print(f"    {bucket:>8}: {count:4d} ({pct:5.1f}%) {bar}")


def main():
    parser = argparse.ArgumentParser(description="View resume matching results")
    parser.add_argument("--results", type=str, default="results/matches.json", help="Path to results JSON file")
    parser.add_argument("--limit", type=int, help="Limit number of jobs to display")
    parser.add_argument("--summary-only", action="store_true", help="Only show summary")
    parser.add_argument("--analyze", action="store_true", help="Show detailed analysis")
    args = parser.parse_args()

    base_dir = Path(__file__).parent.parent
    results_path = base_dir / args.results

    if not results_path.exists():
        print(f"ERROR: Results file not found: {results_path}")
        print("Run match_resumes.py first to generate results.")
        sys.exit(1)

    results = load_results(results_path)

    print_summary(results)

    if not args.summary_only:
        print_detailed_results(results, limit=args.limit)

    if args.analyze:
        print_ehr_analysis(results)
        print_score_distribution(results)

    print("\n")


if __name__ == "__main__":
    main()
