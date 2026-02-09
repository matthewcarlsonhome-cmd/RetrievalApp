#!/usr/bin/env python3
"""
Seed script to initialize the Knowledge Expert with mock data.

Usage:
    python -m knowledge_expert.scripts.seed_data
"""

import os
import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from knowledge_expert.models import Database, KnowledgeItem, DirectQA
from knowledge_expert.ingestion.parsers import parse_document
from knowledge_expert.ingestion.chunker import chunk_with_sections
from knowledge_expert.ingestion.embedder import EmbeddingGenerator, is_embedding_available
from knowledge_expert.retrieval.vector_store import get_vector_store, is_chromadb_available
from knowledge_expert.config import config


def seed_documents():
    """Seed the database with mock documents."""
    print("Seeding documents...")

    db = Database()
    embedder = EmbeddingGenerator() if is_embedding_available() else None
    vector_store = get_vector_store() if is_chromadb_available() else None

    mock_dir = Path(__file__).parent.parent / "data" / "mock"

    if not mock_dir.exists():
        print(f"Mock data directory not found: {mock_dir}")
        return

    # Process each markdown file
    for md_file in mock_dir.glob("*.md"):
        print(f"  Processing: {md_file.name}")

        try:
            # Parse document
            doc_data = parse_document(str(md_file))

            # Create knowledge item
            item = KnowledgeItem(
                title=doc_data.get('title', md_file.stem),
                content=doc_data['content'],
                source=md_file.name,
                file_type='.md',
                metadata={'seeded': True},
                status='processing'
            )
            item_id = db.add_knowledge_item(item)

            # Chunk the content
            chunks = chunk_with_sections(doc_data['content'])

            if not chunks:
                db.update_knowledge_item_status(item_id, 'empty')
                continue

            # Generate embeddings if available
            if embedder and vector_store:
                texts = [c.content for c in chunks]
                embeddings = embedder.embed(texts)

                # Prepare for vector store
                chunk_ids = []
                metadatas = []

                for i, chunk in enumerate(chunks):
                    chunk_id = f"{item_id}_chunk_{i}"
                    chunk_ids.append(chunk_id)
                    metadatas.append({
                        'document_id': item_id,
                        'document_title': item.title,
                        'section_title': chunk.section_title or '',
                        'chunk_index': i
                    })

                # Add to vector store
                vector_store.add_chunks(chunk_ids, embeddings, texts, metadatas)

            db.update_knowledge_item_status(item_id, 'indexed', len(chunks))
            print(f"    Added: {item.title} ({len(chunks)} chunks)")

        except Exception as e:
            print(f"    Error processing {md_file.name}: {e}")


def seed_qa_pairs():
    """Seed the database with Q&A pairs."""
    print("Seeding Q&A pairs...")

    db = Database()

    qa_file = Path(__file__).parent.parent / "data" / "mock" / "seed_qa.json"

    if not qa_file.exists():
        print(f"Q&A seed file not found: {qa_file}")
        return

    try:
        with open(qa_file, 'r') as f:
            data = json.load(f)

        for qa in data.get('qa_pairs', []):
            qa_obj = DirectQA(
                question=qa['question'],
                answer=qa['answer'],
                category=qa.get('category', 'General')
            )
            db.add_direct_qa(qa_obj)
            print(f"    Added: {qa['question'][:50]}...")

        print(f"  Total Q&A pairs added: {len(data.get('qa_pairs', []))}")

    except Exception as e:
        print(f"Error seeding Q&A pairs: {e}")


def main():
    """Main entry point."""
    print("=" * 50)
    print("Knowledge Expert - Data Seeding")
    print("=" * 50)
    print()

    # Check dependencies
    print("Checking dependencies...")
    print(f"  Embeddings available: {is_embedding_available()}")
    print(f"  Vector store available: {is_chromadb_available()}")
    print()

    # Seed data
    seed_documents()
    print()
    seed_qa_pairs()
    print()

    # Show stats
    db = Database()
    stats = db.get_stats()
    print("=" * 50)
    print("Seeding Complete!")
    print(f"  Documents: {stats.get('total_documents', 0)}")
    print(f"  Chunks: {stats.get('total_chunks', 0)}")
    print(f"  Q&A Pairs: {stats.get('total_qa_pairs', 0)}")
    print("=" * 50)


if __name__ == "__main__":
    main()
