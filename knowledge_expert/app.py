"""
Flask application for Company Knowledge Expert.
"""

import os
import logging
from datetime import datetime
from functools import wraps
from typing import Optional

from flask import (
    Flask, request, jsonify, render_template,
    send_from_directory, redirect, url_for, session
)
from werkzeug.utils import secure_filename

from .config import config, moderation_config
from .models import Database, KnowledgeItem, Chunk, Query, DirectQA
from .ingestion.parsers import parse_document, SUPPORTED_EXTENSIONS
from .ingestion.chunker import chunk_text, chunk_with_sections
from .ingestion.embedder import EmbeddingGenerator, is_embedding_available
from .retrieval.vector_store import get_vector_store, is_chromadb_available
from .retrieval.search import HybridSearch, SearchResult
from .generation.llm import get_llm_client, LLMClient, MockLLMClient
from .generation.prompts import PromptBuilder, PromptContext
from .generation.moderation import (
    ContentModerator, moderate_query, moderate_response,
    InputValidator, ModerationAction
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__,
            template_folder='templates',
            static_folder='static')

app.secret_key = config.SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = config.MAX_UPLOAD_SIZE_MB * 1024 * 1024

# Initialize components
db = Database()
embedder = None
vector_store = None
search = None
llm_client = None
prompt_builder = PromptBuilder()
moderator = ContentModerator()
validator = InputValidator()


def init_components():
    """Initialize all components."""
    global embedder, vector_store, search, llm_client

    logger.info("Initializing Knowledge Expert components...")

    # Initialize embedder
    if is_embedding_available():
        embedder = EmbeddingGenerator()
        logger.info("Embedding generator initialized")
    else:
        logger.warning("Embeddings not available - install sentence-transformers")

    # Initialize vector store
    if is_chromadb_available():
        vector_store = get_vector_store()
        logger.info("Vector store initialized")
    else:
        logger.warning("Vector store not available - install chromadb")

    # Initialize search
    if embedder and vector_store:
        search = HybridSearch()
        logger.info("Hybrid search initialized")

    # Initialize LLM client
    try:
        llm_client = get_llm_client()
        if llm_client.is_available():
            logger.info(f"LLM client initialized: {llm_client.provider}")
        else:
            llm_client = MockLLMClient()
            logger.warning("Using mock LLM client - set API key for production")
    except Exception as e:
        llm_client = MockLLMClient()
        logger.warning(f"LLM initialization failed, using mock: {e}")


# Initialize on import
with app.app_context():
    init_components()


# ============================================================================
# API Routes - Chat & Query
# ============================================================================

@app.route('/api/query', methods=['POST'])
def api_query():
    """
    Main Q&A endpoint.

    Accepts a query, retrieves relevant context, and generates a response.
    """
    data = request.get_json()
    if not data or 'query' not in data:
        return jsonify({'error': 'Query is required'}), 400

    query_text = data['query']
    conversation_id = data.get('conversation_id')

    # Validate input
    is_valid, error = validator.validate_query(query_text)
    if not is_valid:
        return jsonify({'error': error}), 400

    # Moderate query
    mod_result = moderate_query(query_text)
    if mod_result.is_blocked:
        return jsonify({
            'error': 'Query contains inappropriate content',
            'reason': mod_result.reason
        }), 400

    try:
        # Check LLM client is available
        if llm_client is None:
            logger.error("LLM client not initialized")
            return jsonify({'error': 'Service temporarily unavailable. LLM not configured.'}), 503

        # Search for relevant context
        search_results = []
        if search:
            try:
                search_results = search.get_context_for_query(query_text)
            except Exception as search_error:
                logger.warning(f"Search failed, continuing without context: {search_error}")

        # Build prompt
        context = PromptContext(
            query=query_text,
            search_results=search_results
        )

        messages = prompt_builder.build_messages(context)
        system_prompt = prompt_builder.build_system_prompt()

        # Generate response
        llm_response = llm_client.generate(
            messages=messages,
            system_prompt=system_prompt
        )

        response_text = llm_response.content

        # Moderate response
        resp_mod = moderate_response(response_text)
        if resp_mod.filtered_content:
            response_text = resp_mod.filtered_content

        # Store query in database (non-critical, don't fail on error)
        query_id = None
        try:
            query_record = Query(
                question=query_text,
                answer=response_text,
                sources=[r.to_dict() for r in search_results],
                model_used=llm_response.model,
                tokens_used=llm_response.usage.get('output_tokens', 0),
                conversation_id=conversation_id
            )
            query_id = db.add_query(query_record)
        except Exception as db_error:
            logger.warning(f"Failed to save query to database: {db_error}")
            query_id = "error"

        # Build citations
        citations = []
        for r in search_results:
            citations.append({
                'document': r.document_title,
                'section': r.section_title,
                'relevance': r.score
            })

        return jsonify({
            'query_id': query_id,
            'response': response_text,
            'citations': citations,
            'model': llm_response.model,
            'tokens_used': llm_response.usage
        })

    except Exception as e:
        logger.error(f"Query error: {e}", exc_info=True)
        error_msg = str(e) if app.debug else 'Failed to process query'
        return jsonify({'error': error_msg, 'details': str(type(e).__name__)}), 500


@app.route('/api/feedback', methods=['POST'])
def api_feedback():
    """Submit feedback for a query response."""
    data = request.get_json()
    if not data or 'query_id' not in data:
        return jsonify({'error': 'query_id is required'}), 400

    query_id = data['query_id']
    feedback = data.get('feedback', 'positive')  # positive/negative
    feedback_text = data.get('feedback_text', '')

    # Validate feedback text
    is_valid, error = validator.validate_feedback(feedback_text)
    if not is_valid:
        return jsonify({'error': error}), 400

    try:
        db.update_query_feedback(query_id, feedback, feedback_text)
        return jsonify({'status': 'success'})
    except Exception as e:
        logger.error(f"Feedback error: {e}")
        return jsonify({'error': 'Failed to save feedback'}), 500


# ============================================================================
# API Routes - Document Upload
# ============================================================================

@app.route('/api/documents', methods=['GET'])
def api_list_documents():
    """List all documents in the knowledge base."""
    try:
        documents = db.get_all_knowledge_items()
        return jsonify({
            'documents': [
                {
                    'id': doc.id,
                    'title': doc.title,
                    'file_type': doc.file_type,
                    'source': doc.source,
                    'chunk_count': doc.chunk_count,
                    'status': doc.status,
                    'created_at': doc.created_at.isoformat() if doc.created_at else None
                }
                for doc in documents
            ]
        })
    except Exception as e:
        logger.error(f"List documents error: {e}")
        return jsonify({'error': 'Failed to list documents'}), 500


@app.route('/api/documents/upload', methods=['POST'])
def api_upload_document():
    """
    Upload and process a document.

    Accepts multipart form with 'file' field.
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    # Check file extension
    filename = secure_filename(file.filename)
    ext = os.path.splitext(filename)[1].lower()

    if ext not in SUPPORTED_EXTENSIONS:
        return jsonify({
            'error': f'Unsupported file type. Supported: {", ".join(SUPPORTED_EXTENSIONS)}'
        }), 400

    try:
        # Save file
        upload_path = config.UPLOAD_PATH / filename
        file.save(str(upload_path))

        # Parse document
        doc_data = parse_document(str(upload_path))

        # Create knowledge item
        item = KnowledgeItem(
            title=doc_data.get('title', filename),
            content=doc_data['content'],
            source=filename,
            file_type=ext,
            metadata=doc_data.get('metadata', {}),
            status='processing'
        )
        item_id = db.add_knowledge_item(item)

        # Chunk the content
        chunks = chunk_with_sections(doc_data['content'])

        if not chunks:
            db.update_knowledge_item_status(item_id, 'empty')
            return jsonify({
                'error': 'Document appears to be empty',
                'document_id': item_id
            }), 400

        # Generate embeddings
        if embedder:
            texts = [c.content for c in chunks]
            embeddings = embedder.embed(texts)

            # Store in vector database
            chunk_ids = []
            chunk_records = []
            metadatas = []

            for i, chunk in enumerate(chunks):
                chunk_id = f"{item_id}_chunk_{i}"
                chunk_ids.append(chunk_id)

                chunk_records.append(Chunk(
                    id=chunk_id,
                    document_id=item_id,
                    content=chunk.content,
                    chunk_index=i,
                    section_title=chunk.section_title,
                    token_count=chunk.token_count
                ))

                metadatas.append({
                    'document_id': item_id,
                    'document_title': item.title,
                    'section_title': chunk.section_title or '',
                    'chunk_index': i
                })

            # Add to vector store
            vector_store.add_chunks(chunk_ids, embeddings, texts, metadatas)

            # Save chunk records
            db.add_chunks(chunk_records)

        # Update status
        db.update_knowledge_item_status(item_id, 'indexed', len(chunks))

        return jsonify({
            'status': 'success',
            'document_id': item_id,
            'title': item.title,
            'chunks': len(chunks)
        })

    except Exception as e:
        logger.error(f"Upload error: {e}", exc_info=True)
        return jsonify({'error': f'Failed to process document: {str(e)}'}), 500


@app.route('/api/documents/<document_id>', methods=['DELETE'])
def api_delete_document(document_id):
    """Delete a document and its chunks."""
    try:
        # Delete from vector store
        if vector_store:
            vector_store.delete_by_document(document_id)

        # Delete from database
        db.delete_knowledge_item(document_id)

        return jsonify({'status': 'success'})
    except Exception as e:
        logger.error(f"Delete error: {e}")
        return jsonify({'error': 'Failed to delete document'}), 500


# ============================================================================
# API Routes - Direct Q&A
# ============================================================================

@app.route('/api/qa', methods=['GET'])
def api_list_qa():
    """List all direct Q&A pairs."""
    try:
        qa_pairs = db.get_all_direct_qa()
        return jsonify({
            'qa_pairs': [
                {
                    'id': qa.id,
                    'question': qa.question,
                    'answer': qa.answer,
                    'category': qa.category,
                    'created_at': qa.created_at.isoformat() if qa.created_at else None
                }
                for qa in qa_pairs
            ]
        })
    except Exception as e:
        logger.error(f"List Q&A error: {e}")
        return jsonify({'error': 'Failed to list Q&A pairs'}), 500


@app.route('/api/qa', methods=['POST'])
def api_add_qa():
    """Add a direct Q&A pair."""
    data = request.get_json()
    if not data or 'question' not in data or 'answer' not in data:
        return jsonify({'error': 'Question and answer are required'}), 400

    try:
        qa = DirectQA(
            question=data['question'],
            answer=data['answer'],
            category=data.get('category', 'General')
        )
        qa_id = db.add_direct_qa(qa)

        return jsonify({
            'status': 'success',
            'qa_id': qa_id
        })
    except Exception as e:
        logger.error(f"Add Q&A error: {e}")
        return jsonify({'error': 'Failed to add Q&A pair'}), 500


@app.route('/api/qa/<qa_id>', methods=['DELETE'])
def api_delete_qa(qa_id):
    """Delete a Q&A pair."""
    try:
        db.delete_direct_qa(qa_id)
        return jsonify({'status': 'success'})
    except Exception as e:
        logger.error(f"Delete Q&A error: {e}")
        return jsonify({'error': 'Failed to delete Q&A pair'}), 500


# ============================================================================
# API Routes - Admin & Stats
# ============================================================================

@app.route('/api/stats', methods=['GET'])
def api_stats():
    """Get system statistics."""
    try:
        stats = db.get_stats()

        # Add vector store stats
        if vector_store:
            stats['vector_count'] = vector_store.count()

        # Add component status
        stats['components'] = {
            'embeddings': embedder is not None,
            'vector_store': vector_store is not None,
            'search': search is not None,
            'llm': llm_client.is_available() if llm_client else False,
            'llm_provider': llm_client.provider if llm_client else 'none'
        }

        return jsonify(stats)
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return jsonify({'error': 'Failed to get stats'}), 500


@app.route('/api/health', methods=['GET'])
def api_health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0'
    })


# ============================================================================
# Web Routes - UI Pages
# ============================================================================

@app.route('/')
def index():
    """Main chat interface."""
    return render_template('chat.html')


@app.route('/upload')
def upload_page():
    """Document upload page."""
    return render_template('upload.html')


@app.route('/admin')
def admin_page():
    """Admin dashboard."""
    stats = db.get_stats()
    if vector_store:
        stats['vector_count'] = vector_store.count()
    return render_template('admin.html', stats=stats)


@app.route('/qa')
def qa_page():
    """Q&A management page."""
    return render_template('qa.html')


# ============================================================================
# Static Files
# ============================================================================

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files."""
    return send_from_directory(app.static_folder, filename)


# ============================================================================
# Error Handlers
# ============================================================================

@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors."""
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Not found'}), 404
    return render_template('404.html'), 404


@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors."""
    logger.error(f"Server error: {e}")
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Internal server error'}), 500
    return render_template('500.html'), 500


@app.errorhandler(413)
def file_too_large(e):
    """Handle file too large errors."""
    return jsonify({
        'error': f'File too large. Maximum size is {config.MAX_UPLOAD_SIZE_MB}MB'
    }), 413


# ============================================================================
# CLI Commands
# ============================================================================

@app.cli.command('init-db')
def init_db_command():
    """Initialize the database."""
    db.init_db()
    print("Database initialized.")


@app.cli.command('reset-vectors')
def reset_vectors_command():
    """Reset the vector store."""
    if vector_store:
        vector_store.reset()
        print("Vector store reset.")
    else:
        print("Vector store not available.")


@app.cli.command('stats')
def stats_command():
    """Show system statistics."""
    stats = db.get_stats()
    if vector_store:
        stats['vector_count'] = vector_store.count()

    print("\n=== Knowledge Expert Stats ===")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    print()


# ============================================================================
# Main Entry Point
# ============================================================================

def create_app():
    """Application factory."""
    return app


if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000)),
        debug=os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    )
