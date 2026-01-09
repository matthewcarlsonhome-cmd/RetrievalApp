#!/usr/bin/env python3
"""
Basic Usage Example for the RAG Pipeline.

Demonstrates the core workflow:
1. Initialize the pipeline
2. Ingest documents
3. Query the system
4. Collect feedback
5. Monitor metrics
"""

from retrieval_app import RAGPipeline, RAGConfig
from retrieval_app.core.config import RetrievalMode, ChunkingStrategy


def main():
    # Initialize with default config (uses mock LLM for demo)
    print("Initializing RAG Pipeline...")
    pipeline = RAGPipeline(use_mock_llm=True)

    # Sample documents to ingest
    documents = [
        (
            "doc_001",
            """
            Machine Learning Fundamentals

            Machine learning is a subset of artificial intelligence that enables
            systems to learn and improve from experience without being explicitly
            programmed. The three main types of machine learning are:

            1. Supervised Learning: The algorithm learns from labeled training data,
               making predictions based on that data. Examples include classification
               and regression tasks.

            2. Unsupervised Learning: The algorithm finds patterns in unlabeled data.
               Clustering and dimensionality reduction are common applications.

            3. Reinforcement Learning: The algorithm learns by interacting with an
               environment, receiving rewards or penalties for actions taken.
            """,
            {"source": "ml_textbook.pdf", "category": "fundamentals", "year": 2024}
        ),
        (
            "doc_002",
            """
            Neural Networks and Deep Learning

            Neural networks are computing systems inspired by biological neural networks.
            A neural network consists of layers of interconnected nodes (neurons):

            - Input Layer: Receives the initial data
            - Hidden Layers: Process the data through weighted connections
            - Output Layer: Produces the final result

            Deep learning refers to neural networks with many hidden layers. Popular
            architectures include:

            - Convolutional Neural Networks (CNNs): Best for image processing
            - Recurrent Neural Networks (RNNs): Best for sequential data
            - Transformers: State-of-the-art for natural language processing
            """,
            {"source": "deep_learning_guide.pdf", "category": "neural_networks", "year": 2024}
        ),
        (
            "doc_003",
            """
            Retrieval-Augmented Generation (RAG)

            RAG is a technique that combines retrieval systems with generative models.
            Instead of relying solely on the model's training data, RAG:

            1. Retrieves relevant documents from a knowledge base
            2. Uses those documents as context for generation
            3. Produces answers grounded in actual sources

            Benefits of RAG:
            - Reduces hallucinations by grounding responses in facts
            - Allows easy updates to knowledge without retraining
            - Provides source attribution for answers
            - Handles domain-specific knowledge effectively

            Key challenges include chunking strategies, retrieval quality, and
            prompt engineering for effective context usage.
            """,
            {"source": "rag_overview.pdf", "category": "architecture", "year": 2024}
        ),
    ]

    # Ingest documents
    print("\nIngesting documents...")
    stats = pipeline.ingest_documents(documents)
    print(f"Ingestion stats: {stats}")

    # Example queries
    queries = [
        "What are the three types of machine learning?",
        "How do neural networks work?",
        "What are the benefits of RAG?",
        "Compare CNNs and RNNs",
    ]

    print("\n" + "=" * 60)
    print("Processing queries...")
    print("=" * 60)

    for query in queries:
        print(f"\nQuery: {query}")
        print("-" * 40)

        response = pipeline.query(query)

        print(f"Answer: {response.answer[:200]}...")
        print(f"Confidence: {response.confidence:.2f}")
        print(f"Sources: {response.sources}")
        print(f"Latency: {response.latency_ms:.1f}ms")
        print(f"Routing: {response.routing_decision}")

    # Show metrics
    print("\n" + "=" * 60)
    print("Pipeline Metrics")
    print("=" * 60)
    metrics = pipeline.get_metrics_summary()
    for key, value in metrics.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.2f}")
        else:
            print(f"  {key}: {value}")


def advanced_example():
    """Example with custom configuration."""

    # High-precision configuration
    config = RAGConfig.for_high_precision()
    config.chunking.strategy = ChunkingStrategy.SEMANTIC
    config.retrieval.mode = RetrievalMode.HYBRID

    pipeline = RAGPipeline(config=config, use_mock_llm=True)

    # ... rest of usage similar to main()


if __name__ == "__main__":
    main()
