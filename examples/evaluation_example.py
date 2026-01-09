#!/usr/bin/env python3
"""
Evaluation Example for the RAG Pipeline.

Demonstrates how to:
1. Create and manage truth sets
2. Evaluate retrieval quality
3. Analyze feedback
4. Track improvements over time
"""

from retrieval_app import RAGPipeline
from retrieval_app.data_prep.truth_sets import TruthSetManager


def main():
    # Initialize pipeline
    pipeline = RAGPipeline(use_mock_llm=True)

    # Sample documents
    documents = [
        (
            "python_basics",
            """
            Python is a high-level, interpreted programming language known for
            its clear syntax and readability. Key features include:

            - Dynamic typing
            - Automatic memory management
            - Extensive standard library
            - Support for multiple programming paradigms

            Python is commonly used for web development, data science, machine
            learning, automation, and scientific computing.
            """,
            {"source": "python_docs", "category": "programming"}
        ),
        (
            "python_functions",
            """
            Functions in Python are defined using the 'def' keyword. A function
            can take parameters and return values.

            Example:
            def greet(name):
                return f"Hello, {name}!"

            Python supports default parameters, keyword arguments, *args for
            variable positional arguments, and **kwargs for variable keyword
            arguments.
            """,
            {"source": "python_docs", "category": "programming"}
        ),
    ]

    # Ingest documents
    print("Ingesting documents...")
    pipeline.ingest_documents(documents)

    # Create a truth set for evaluation
    print("\nCreating truth set...")
    truth_manager = TruthSetManager(storage_path="./evaluation/truth_sets")

    truth_manager.create_truth_set("python_qa")

    # Add test cases with known correct answers
    truth_manager.add_entry(
        truth_set_name="python_qa",
        query="What are the key features of Python?",
        expected_answer="Dynamic typing, automatic memory management, extensive standard library, support for multiple paradigms",
        relevant_chunk_ids=["python_basics"],  # Would be actual chunk IDs
        tags=["basics", "features"],
        difficulty="easy"
    )

    truth_manager.add_entry(
        truth_set_name="python_qa",
        query="How do you define a function in Python?",
        expected_answer="Functions are defined using the 'def' keyword",
        relevant_chunk_ids=["python_functions"],
        tags=["functions", "syntax"],
        difficulty="easy"
    )

    # Evaluate retrieval quality
    print("\nEvaluating retrieval quality...")

    # Create a retrieval function for evaluation
    def retrieve_chunks(query: str) -> list[str]:
        result = pipeline.retriever.retrieve(query, top_k=5)
        return [r.chunk.id for r in result.results]

    evaluation = truth_manager.evaluate_retrieval(
        truth_set_name="python_qa",
        retrieval_fn=retrieve_chunks,
        k_values=[1, 3, 5]
    )

    print(f"\nEvaluation Results:")
    print(f"  Total queries: {evaluation.total_queries}")
    print(f"  Mean Precision: {evaluation.mean_precision:.2%}")
    print(f"  Mean Recall: {evaluation.mean_recall:.2%}")
    print(f"  Mean F1: {evaluation.mean_f1:.2%}")
    print(f"  Mean Reciprocal Rank: {evaluation.mean_reciprocal_rank:.2f}")
    print(f"  Recall@1: {evaluation.recall_at_k.get(1, 0):.2%}")
    print(f"  Recall@3: {evaluation.recall_at_k.get(3, 0):.2%}")
    print(f"  Recall@5: {evaluation.recall_at_k.get(5, 0):.2%}")

    # Simulate user feedback
    print("\n\nSimulating user feedback...")

    # Positive feedback
    pipeline.feedback.record_thumbs(
        query_id="q001",
        query="What is Python?",
        answer="Python is a high-level programming language...",
        is_positive=True,
        comment="Great answer!"
    )

    # Negative feedback with correction
    pipeline.feedback.record_correction(
        query_id="q002",
        query="What year was Python created?",
        wrong_answer="Python was created in 1995.",
        correct_answer="Python was created in 1991 by Guido van Rossum."
    )

    # Rating
    pipeline.feedback.record_rating(
        query_id="q003",
        query="How do I install Python?",
        answer="You can download Python from python.org...",
        rating=0.8
    )

    # Analyze feedback
    print("\nFeedback Analysis:")
    analysis = pipeline.feedback.analyze()
    print(f"  Total feedback: {analysis.total_feedback}")
    print(f"  Positive rate: {analysis.positive_rate:.2%}")
    print(f"  Negative rate: {analysis.negative_rate:.2%}")
    if analysis.average_rating:
        print(f"  Average rating: {analysis.average_rating:.2f}")
    print(f"  Queries needing review: {len(analysis.queries_needing_review)}")

    # Export corrections for truth set updates
    corrections = pipeline.feedback.get_corrections_for_truth_set()
    if corrections:
        print(f"\n  Corrections available for truth set: {len(corrections)}")
        for c in corrections:
            print(f"    - Query: {c['query'][:50]}...")


if __name__ == "__main__":
    main()
