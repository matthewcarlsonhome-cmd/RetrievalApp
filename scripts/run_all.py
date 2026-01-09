#!/usr/bin/env python3
"""
One-command quick start script.

Generates test data, runs matching, and displays results.
"""

import subprocess
import sys
import time
from pathlib import Path


def run_script(script_name: str, args: list = None) -> bool:
    """Run a Python script and return success status."""
    script_path = Path(__file__).parent / script_name
    cmd = [sys.executable, str(script_path)] + (args or [])

    print(f"\n{'─' * 60}")
    print(f"Running: {script_name}")
    print(f"{'─' * 60}\n")

    result = subprocess.run(cmd, cwd=Path(__file__).parent.parent)
    return result.returncode == 0


def main():
    print("=" * 60)
    print("HEALTHCARE RESUME MATCHING - QUICK START")
    print("=" * 60)

    start_time = time.time()

    # Step 1: Generate test data
    print("\n[1/3] Generating test data...")
    if not run_script("generate_test_data.py"):
        print("ERROR: Failed to generate test data")
        sys.exit(1)

    # Step 2: Run matching
    print("\n[2/3] Running resume-job matching...")
    if not run_script("match_resumes.py"):
        print("ERROR: Failed to run matching")
        sys.exit(1)

    # Step 3: View results
    print("\n[3/3] Displaying results...")
    if not run_script("view_results.py", ["--limit", "5", "--analyze"]):
        print("WARNING: Failed to display results, but matching may have succeeded")

    total_time = time.time() - start_time

    print("\n" + "=" * 60)
    print("QUICK START COMPLETE")
    print("=" * 60)
    print(f"\nTotal time: {total_time:.1f} seconds")
    print("\nGenerated files:")
    print("  - test_data/resumes/      (100 resume JSON files)")
    print("  - test_data/job_descriptions/  (20 job JSON files)")
    print("  - results/matches.json    (matching results)")
    print("\nNext steps:")
    print("  - View full results: python scripts/view_results.py")
    print("  - Adjust matching: edit TOP_K, SEMANTIC_WEIGHT in match_resumes.py")
    print("  - Generate more data: python scripts/generate_test_data.py --resumes 500")


if __name__ == "__main__":
    main()
