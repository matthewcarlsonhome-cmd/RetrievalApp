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
from .models import Database, KnowledgeItem, Chunk, Query, DirectQA, KnowledgeGap
from .ingestion.parsers import parse_document, SUPPORTED_EXTENSIONS
from .ingestion.chunker import chunk_text, chunk_with_sections, ChunkingStrategy
from .experiments import ExperimentManager, experiment_manager
from .ingestion.embedder import EmbeddingGenerator, is_embedding_available
from .retrieval.vector_store import get_vector_store, get_tenant_store, is_chromadb_available
from .retrieval.search import HybridSearch, SearchResult, get_tenant_search
from .generation.llm import get_llm_client, LLMClient, MockLLMClient
from .generation.prompts import PromptBuilder, PromptContext
from .generation.moderation import (
    ContentModerator, moderate_query, moderate_response,
    InputValidator, ModerationAction
)
from .generation.qa_generator import get_qa_generator, QAGenerator
from .caching import get_response_cache, ResponseCache

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

    # Check if we should skip heavy ML components (for free tier / low memory)
    skip_ml = os.environ.get("SKIP_ML_MODELS", "false").lower() == "true"

    if skip_ml:
        logger.info("SKIP_ML_MODELS=true - Running in lightweight mode (no embeddings/vector search)")
        embedder = None
        vector_store = None
        search = None
    else:
        # Initialize embedder
        if is_embedding_available():
            try:
                embedder = EmbeddingGenerator()
                logger.info("Embedding generator initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize embedder: {e}")
        else:
            logger.warning("Embeddings not available - install sentence-transformers")

        # Initialize vector store
        if is_chromadb_available():
            try:
                vector_store = get_vector_store()
                logger.info("Vector store initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize vector store: {e}")
        else:
            logger.warning("Vector store not available - install chromadb")

        # Initialize search
        if embedder and vector_store:
            try:
                search = HybridSearch()
                logger.info("Hybrid search initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize search: {e}")

    # Initialize LLM client (lightweight, always load)
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
# Authentication Helpers
# ============================================================================

def login_required(f):
    """Decorator to require authentication for a route."""
    from functools import wraps

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({'error': 'Authentication required'}), 401
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function


def get_current_user():
    """Get the currently logged in user."""
    user_id = session.get('user_id')
    if user_id:
        return db.get_user(user_id)
    return None


# ============================================================================
# Tenant Context Helpers
# ============================================================================

def get_tenant_context():
    """
    Get the current tenant (organization) context.

    Determines organization from (in priority order):
    1. API key in Authorization header
    2. Session organization_id
    3. Default organization

    Returns:
        tuple: (organization_id, user_id) or (default_org_id, None)
    """
    organization_id = None
    user_id = None

    # Check for API key authentication
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        api_key = auth_header[7:]
        user = db.get_user_by_api_key(api_key)
        if user:
            organization_id = user.organization_id
            user_id = user.id

    # Check session
    if not organization_id:
        organization_id = session.get('organization_id')
        user_id = session.get('user_id')

    # Fall back to default organization
    if not organization_id:
        default_org = db.get_default_organization()
        if default_org:
            organization_id = default_org.id

    return organization_id, user_id


def get_tenant_vector_store(organization_id: str = None):
    """Get tenant-isolated vector store."""
    if organization_id is None:
        organization_id, _ = get_tenant_context()

    if organization_id:
        return get_tenant_store(organization_id)
    return vector_store


def get_tenant_hybrid_search(organization_id: str = None):
    """Get tenant-isolated search instance."""
    if organization_id is None:
        organization_id, _ = get_tenant_context()

    if organization_id:
        return get_tenant_search(organization_id)
    return search


# ============================================================================
# API Routes - Authentication
# ============================================================================

@app.route('/api/auth/signup', methods=['POST'])
def api_signup():
    """
    Register a new user account.

    Creates a new user and optionally a new organization.
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body required'}), 400

    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    name = data.get('name', '').strip()
    organization_name = data.get('organization_name', '').strip()

    # Validation
    if not email or '@' not in email:
        return jsonify({'error': 'Valid email is required'}), 400
    if len(password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400
    if not name:
        return jsonify({'error': 'Name is required'}), 400

    # Check if email already exists
    existing = db.get_user_by_email(email)
    if existing:
        return jsonify({'error': 'Email already registered'}), 400

    try:
        # Create organization if name provided, otherwise use default
        if organization_name:
            from .models import Organization
            import re
            slug = re.sub(r'[^a-z0-9]+', '-', organization_name.lower()).strip('-')
            org = Organization(name=organization_name, slug=slug)
            db.create_organization(org)
            organization_id = org.id
        else:
            default_org = db.get_default_organization()
            organization_id = default_org.id if default_org else None

        # Create user
        from .models import User
        user = User(
            email=email,
            name=name,
            organization_id=organization_id,
            role='admin' if organization_name else 'member',
            password_hash=User.hash_password(password)
        )
        db.create_user(user)

        # Auto-login
        session['user_id'] = user.id
        session['organization_id'] = user.organization_id
        session.permanent = True

        return jsonify({
            'status': 'success',
            'user': {
                'id': user.id,
                'email': user.email,
                'name': user.name,
                'organization_id': user.organization_id,
                'role': user.role
            }
        })

    except Exception as e:
        logger.error(f"Signup error: {e}")
        return jsonify({'error': 'Failed to create account'}), 500


@app.route('/api/auth/login', methods=['POST'])
def api_login():
    """
    Login with email and password.
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body required'}), 400

    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400

    # Find user
    user = db.get_user_by_email(email)
    if not user:
        return jsonify({'error': 'Invalid email or password'}), 401

    # Verify password
    if not user.verify_password(password):
        return jsonify({'error': 'Invalid email or password'}), 401

    # Update last login
    try:
        with db.get_connection() as conn:
            conn.execute(
                "UPDATE users SET last_login = ? WHERE id = ?",
                (datetime.utcnow().isoformat(), user.id)
            )
    except Exception:
        pass

    # Set session
    session['user_id'] = user.id
    session['organization_id'] = user.organization_id
    session.permanent = True

    return jsonify({
        'status': 'success',
        'user': {
            'id': user.id,
            'email': user.email,
            'name': user.name,
            'organization_id': user.organization_id,
            'role': user.role
        }
    })


@app.route('/api/auth/logout', methods=['POST'])
def api_logout():
    """Logout the current user."""
    session.clear()
    return jsonify({'status': 'success'})


@app.route('/api/auth/me', methods=['GET'])
def api_current_user():
    """Get the current logged-in user."""
    user = get_current_user()
    if not user:
        return jsonify({'authenticated': False}), 200

    # Get organization info
    org = db.get_organization(user.organization_id) if user.organization_id else None

    return jsonify({
        'authenticated': True,
        'user': {
            'id': user.id,
            'email': user.email,
            'name': user.name,
            'organization_id': user.organization_id,
            'role': user.role,
            'api_key': user.api_key
        },
        'organization': {
            'id': org.id,
            'name': org.name,
            'slug': org.slug
        } if org else None
    })


@app.route('/api/auth/api-key', methods=['POST'])
def api_regenerate_key():
    """Regenerate API key for current user."""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        import secrets
        new_key = secrets.token_urlsafe(32)

        with db.get_connection() as conn:
            conn.execute(
                "UPDATE users SET api_key = ? WHERE id = ?",
                (new_key, user.id)
            )

        return jsonify({
            'status': 'success',
            'api_key': new_key
        })
    except Exception as e:
        logger.error(f"API key regeneration error: {e}")
        return jsonify({'error': 'Failed to regenerate API key'}), 500


# ============================================================================
# API Routes - Chat & Query
# ============================================================================

@app.route('/api/query', methods=['POST'])
def api_query():
    """
    Main Q&A endpoint.

    Accepts a query, retrieves relevant context, and generates a response.
    Uses tenant isolation to ensure users only search their own documents.
    """
    data = request.get_json()
    if not data or 'query' not in data:
        return jsonify({'error': 'Query is required'}), 400

    query_text = data['query']
    conversation_id = data.get('conversation_id')

    # Get tenant context for isolation
    organization_id, user_id = get_tenant_context()

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
        # Check for cached response first
        cache = get_response_cache()
        skip_cache = data.get('skip_cache', False)

        if not skip_cache:
            cached = cache.get(query_text, organization_id)
            if cached:
                response_text, _ = cached
                logger.info(f"Cache hit for query: {query_text[:50]}...")
                return jsonify({
                    'query_id': 'cached',
                    'response': response_text,
                    'citations': [],
                    'model': 'cached',
                    'tokens_used': {'cached': True},
                    'cached': True
                })

        # Check LLM client is available
        if llm_client is None:
            logger.error("LLM client not initialized")
            return jsonify({'error': 'Service temporarily unavailable. LLM not configured.'}), 503

        # Search for relevant context using tenant-isolated search
        search_results = []
        tenant_search = get_tenant_hybrid_search(organization_id)
        if tenant_search:
            try:
                search_results = tenant_search.get_context_for_query(query_text)
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
                conversation_id=conversation_id,
                organization_id=organization_id,
                user_id=user_id,
                chunks_used=[r.chunk_id for r in search_results],
                chunk_scores=[r.score for r in search_results]
            )
            query_id = db.add_query(query_record)
        except Exception as db_error:
            logger.warning(f"Failed to save query to database: {db_error}")
            query_id = "error"

        # Build enhanced citations with links and position info
        citations = []
        for r in search_results:
            citation = {
                'document': r.document_title,
                'section': r.section_title,
                'relevance': r.score,
                'chunk_id': r.chunk_id,
                'document_id': r.document_id,
                'start_char': r.start_char,
                'end_char': r.end_char
            }

            # Add page number if available
            if r.page_number:
                citation['page_number'] = r.page_number

            # Get source URL if document has one
            try:
                doc = db.get_knowledge_item(r.document_id)
                if doc and doc.source_url:
                    citation['source_url'] = doc.source_url
            except Exception:
                pass

            citations.append(citation)

        # Cache the response
        if not skip_cache and response_text:
            cache.set(
                query=query_text,
                response=response_text,
                organization_id=organization_id,
                metadata={'model': llm_response.model, 'query_id': query_id}
            )

        return jsonify({
            'query_id': query_id,
            'response': response_text,
            'citations': citations,
            'model': llm_response.model,
            'tokens_used': llm_response.usage,
            'cached': False
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
    """List documents in the knowledge base (tenant-isolated)."""
    try:
        # Get tenant context for isolation
        organization_id, _ = get_tenant_context()

        # Get documents filtered by organization
        documents = db.get_all_knowledge_items(organization_id=organization_id)
        return jsonify({
            'documents': [
                {
                    'id': doc.id,
                    'title': doc.title,
                    'file_type': doc.file_type,
                    'source': doc.source_file,
                    'chunk_count': doc.chunk_count,
                    'access_level': doc.access_level,
                    'created_at': doc.created_at if doc.created_at else None
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
    Uses tenant isolation to store documents in organization-specific collections.
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    # Get tenant context for isolation
    organization_id, user_id = get_tenant_context()

    # Check file extension
    filename = secure_filename(file.filename)
    ext = os.path.splitext(filename)[1].lower()

    if ext not in SUPPORTED_EXTENSIONS:
        return jsonify({
            'error': f'Unsupported file type. Supported: {", ".join(SUPPORTED_EXTENSIONS)}'
        }), 400

    try:
        # Save file to org-specific directory for additional isolation
        org_upload_path = config.UPLOAD_PATH / (organization_id or 'default')
        org_upload_path.mkdir(parents=True, exist_ok=True)
        upload_path = org_upload_path / filename
        file.save(str(upload_path))

        # Parse document
        doc_data = parse_document(str(upload_path))

        # Create knowledge item with organization context
        item = KnowledgeItem(
            title=doc_data.get('title', filename),
            content=doc_data['content'],
            source_file=filename,
            file_type=ext,
            metadata=doc_data.get('metadata', {}),
            organization_id=organization_id,
            created_by=user_id
        )
        item_id = db.add_knowledge_item(item)

        # Chunk the content
        chunks = chunk_with_sections(doc_data['content'])

        if not chunks:
            db.update_knowledge_item_chunks(item_id, 0)
            return jsonify({
                'error': 'Document appears to be empty',
                'document_id': item_id
            }), 400

        # Get tenant-isolated vector store
        tenant_vs = get_tenant_vector_store(organization_id)

        # Generate embeddings
        if embedder and tenant_vs:
            texts = [c.content for c in chunks]
            embeddings = embedder.embed(texts)

            # Store in vector database with tenant isolation
            chunk_ids = []
            chunk_records = []
            metadatas = []

            for i, chunk in enumerate(chunks):
                chunk_id = f"{item_id}_chunk_{i}"
                chunk_ids.append(chunk_id)

                chunk_records.append(Chunk(
                    id=chunk_id,
                    document_id=item_id,
                    organization_id=organization_id,
                    content=chunk.content,
                    chunk_index=i,
                    section_title=chunk.section_title,
                    token_count=chunk.token_count,
                    start_char=getattr(chunk, 'start_char', 0),
                    end_char=getattr(chunk, 'end_char', 0)
                ))

                metadatas.append({
                    'document_id': item_id,
                    'document_title': item.title,
                    'section_title': chunk.section_title or '',
                    'chunk_index': i,
                    'organization_id': organization_id or '',
                    'start_char': getattr(chunk, 'start_char', 0),
                    'end_char': getattr(chunk, 'end_char', 0)
                })

            # Add to tenant-isolated vector store
            tenant_vs.add_chunks(chunk_ids, embeddings, texts, metadatas)

            # Save chunk records
            db.add_chunks(chunk_records)

        # Update status
        db.update_knowledge_item_chunks(item_id, len(chunks))

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
    """Delete a document and its chunks (tenant-isolated)."""
    try:
        # Get tenant context
        organization_id, _ = get_tenant_context()

        # Verify document belongs to this tenant
        item = db.get_knowledge_item(document_id)
        if item and item.organization_id and item.organization_id != organization_id:
            return jsonify({'error': 'Document not found'}), 404

        # Delete from tenant-isolated vector store
        tenant_vs = get_tenant_vector_store(organization_id)
        if tenant_vs:
            tenant_vs.delete_by_document(document_id)

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
    """List direct Q&A pairs (tenant-isolated)."""
    try:
        # Get tenant context for isolation
        organization_id, _ = get_tenant_context()

        qa_pairs = db.get_all_direct_qa(organization_id=organization_id)
        return jsonify({
            'qa_pairs': [
                {
                    'id': qa.id,
                    'question': qa.question,
                    'answer': qa.answer,
                    'category': qa.category,
                    'use_count': qa.use_count,
                    'created_at': qa.created_at if qa.created_at else None
                }
                for qa in qa_pairs
            ]
        })
    except Exception as e:
        logger.error(f"List Q&A error: {e}")
        return jsonify({'error': 'Failed to list Q&A pairs'}), 500


@app.route('/api/qa', methods=['POST'])
def api_add_qa():
    """Add a direct Q&A pair (tenant-isolated)."""
    data = request.get_json()
    if not data or 'question' not in data or 'answer' not in data:
        return jsonify({'error': 'Question and answer are required'}), 400

    try:
        # Get tenant context
        organization_id, user_id = get_tenant_context()

        qa = DirectQA(
            question=data['question'],
            answer=data['answer'],
            category=data.get('category', 'General'),
            organization_id=organization_id,
            created_by=user_id
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
    """Get system statistics (tenant-isolated)."""
    try:
        # Get tenant context
        organization_id, _ = get_tenant_context()

        stats = db.get_stats(organization_id=organization_id)

        # Add vector store stats for tenant
        tenant_vs = get_tenant_vector_store(organization_id)
        if tenant_vs:
            stats['vector_count'] = tenant_vs.count()

        # Add component status
        stats['components'] = {
            'embeddings': embedder is not None,
            'vector_store': tenant_vs is not None,
            'search': True,  # Always available with tenant search
            'llm': llm_client.is_available() if llm_client else False,
            'llm_provider': llm_client.provider if llm_client else 'none'
        }

        # Include organization info
        stats['organization_id'] = organization_id

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


@app.route('/analytics')
def analytics_page():
    """Analytics dashboard."""
    return render_template('analytics.html')


@app.route('/login')
def login_page():
    """Login page."""
    if get_current_user():
        return redirect(url_for('index'))
    return render_template('login.html')


@app.route('/signup')
def signup_page():
    """Signup page."""
    if get_current_user():
        return redirect(url_for('index'))
    return render_template('signup.html')


@app.route('/account')
@login_required
def account_page():
    """Account settings page."""
    return render_template('account.html')


@app.route('/widget')
def widget_page():
    """Widget integration page."""
    return render_template('widget.html')


# ============================================================================
# API Routes - Analytics
# ============================================================================

@app.route('/api/analytics/gaps', methods=['GET'])
def api_get_knowledge_gaps():
    """Get knowledge gaps (tenant-isolated)."""
    try:
        # Get tenant context
        organization_id, _ = get_tenant_context()

        resolved = request.args.get('resolved', 'false').lower() == 'true'
        format_type = request.args.get('format', 'list')

        gaps = db.get_knowledge_gaps(organization_id=organization_id, resolved=resolved, limit=50)

        gaps_data = [
            {
                'id': gap.id,
                'query_text': gap.query_text,
                'failure_reason': gap.failure_reason,
                'occurrence_count': gap.occurrence_count,
                'resolved': gap.resolved,
                'created_at': gap.created_at
            }
            for gap in gaps
        ]

        if format_type == 'json':
            import json
            return json.dumps(gaps_data, indent=2), 200, {'Content-Type': 'application/json'}

        return jsonify(gaps_data)
    except Exception as e:
        logger.error(f"Get knowledge gaps error: {e}")
        return jsonify({'error': 'Failed to get knowledge gaps'}), 500


@app.route('/api/analytics/gaps/<gap_id>/resolve', methods=['POST'])
def api_resolve_gap(gap_id):
    """Mark a knowledge gap as resolved."""
    try:
        db.resolve_knowledge_gap(gap_id)
        return jsonify({'status': 'success'})
    except Exception as e:
        logger.error(f"Resolve gap error: {e}")
        return jsonify({'error': 'Failed to resolve gap'}), 500


@app.route('/api/analytics/strategies', methods=['GET'])
def api_get_strategies():
    """Get chunking strategy performance metrics."""
    try:
        performance = experiment_manager.get_chunk_performance_by_strategy()
        return jsonify(performance)
    except Exception as e:
        logger.error(f"Get strategies error: {e}")
        return jsonify({'error': 'Failed to get strategy data'}), 500


@app.route('/api/analytics/experiments', methods=['GET'])
def api_get_experiments():
    """Get all experiments with their stats."""
    try:
        experiments = experiment_manager.get_all_experiments()
        result = []

        for exp in experiments:
            stats = experiment_manager.get_experiment_stats(exp.id)
            result.append({
                'id': exp.id,
                'name': exp.name,
                'description': exp.description,
                'chunking_strategy': exp.chunking_strategy,
                'chunk_size': exp.chunk_size,
                'chunk_overlap': exp.chunk_overlap,
                'semantic_weight': exp.semantic_weight,
                'keyword_weight': exp.keyword_weight,
                'qa_weight': exp.qa_weight,
                'top_k': exp.top_k,
                'is_active': exp.is_active,
                'is_control': exp.is_control,
                'created_at': exp.created_at,
                'total_queries': stats.get('total_queries', 0),
                'positive_rate': stats.get('positive_rate', 0)
            })

        return jsonify(result)
    except Exception as e:
        logger.error(f"Get experiments error: {e}")
        return jsonify({'error': 'Failed to get experiments'}), 500


@app.route('/api/analytics/experiments', methods=['POST'])
def api_create_experiment():
    """Create a new experiment."""
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({'error': 'Name is required'}), 400

    try:
        exp = experiment_manager.create_experiment(
            name=data['name'],
            description=data.get('description', ''),
            strategy=data.get('strategy', 'sentence'),
            chunk_size=data.get('chunk_size', 500),
            chunk_overlap=data.get('chunk_overlap', 50),
            semantic_weight=data.get('semantic_weight', 0.7),
            keyword_weight=data.get('keyword_weight', 0.2),
            qa_weight=data.get('qa_weight', 0.1),
            top_k=data.get('top_k', 5),
            is_control=data.get('is_control', False)
        )

        return jsonify({
            'status': 'success',
            'experiment_id': exp.id,
            'name': exp.name
        })
    except Exception as e:
        logger.error(f"Create experiment error: {e}")
        return jsonify({'error': 'Failed to create experiment'}), 500


@app.route('/api/analytics/export', methods=['GET'])
def api_export_training_data():
    """Export training data for fine-tuning (tenant-isolated)."""
    try:
        # Get tenant context
        organization_id, _ = get_tenant_context()

        format_type = request.args.get('format', 'jsonl')
        filter_type = request.args.get('filter', 'positive')

        positive_only = filter_type in ('positive', 'good')

        # Try experiment manager first
        try:
            data = experiment_manager.export_training_data(
                positive_only=positive_only,
                format=format_type
            )
        except Exception:
            # Fall back to database export (with tenant filter)
            data_list = db.export_training_data(organization_id=organization_id, positive_only=positive_only)

            if format_type == 'jsonl':
                import json
                lines = [json.dumps(entry) for entry in data_list]
                data = '\n'.join(lines)
            elif format_type == 'json':
                import json
                data = json.dumps(data_list, indent=2)
            elif format_type == 'csv':
                import csv
                from io import StringIO
                output = StringIO()
                writer = csv.writer(output)
                writer.writerow(['query', 'response', 'feedback'])
                for entry in data_list:
                    messages = entry.get('messages', [])
                    query = messages[0]['content'] if messages else ''
                    response = messages[1]['content'] if len(messages) > 1 else ''
                    writer.writerow([query, response, entry.get('feedback', '')])
                data = output.getvalue()
            else:
                data = ''

        content_type = 'text/plain'
        if format_type == 'json':
            content_type = 'application/json'
        elif format_type == 'csv':
            content_type = 'text/csv'

        return data, 200, {'Content-Type': content_type}
    except Exception as e:
        logger.error(f"Export training data error: {e}")
        return jsonify({'error': 'Failed to export training data'}), 500


@app.route('/api/analytics/report', methods=['GET'])
def api_get_report():
    """Get comprehensive experiment report."""
    try:
        report = experiment_manager.generate_report()
        return jsonify(report)
    except Exception as e:
        logger.error(f"Get report error: {e}")
        return jsonify({'error': 'Failed to generate report'}), 500


# ============================================================================
# API Routes - Auto Q&A Generation
# ============================================================================

@app.route('/api/qa/generate', methods=['POST'])
def api_generate_qa():
    """
    Generate Q&A pairs from a document or all documents.

    Request body:
    {
        "document_id": "optional - specific document to generate from",
        "num_pairs": 10,  // Number of Q&A pairs to generate
        "strategy": "mixed",  // factual, conceptual, procedural, faq, or mixed
        "auto_save": true  // Whether to save generated pairs automatically
    }
    """
    data = request.get_json() or {}

    # Get tenant context
    organization_id, user_id = get_tenant_context()

    document_id = data.get('document_id')
    num_pairs = min(data.get('num_pairs', 10), 50)  # Cap at 50
    strategy = data.get('strategy', 'mixed')
    auto_save = data.get('auto_save', False)

    try:
        qa_generator = get_qa_generator()

        if not qa_generator.llm_client or not qa_generator.llm_client.is_available():
            return jsonify({'error': 'LLM not configured for Q&A generation'}), 503

        generated_pairs = []

        if document_id:
            # Verify document belongs to this tenant
            doc = db.get_knowledge_item(document_id)
            if not doc:
                return jsonify({'error': 'Document not found'}), 404
            if doc.organization_id and doc.organization_id != organization_id:
                return jsonify({'error': 'Document not found'}), 404

            # Generate from specific document
            generated_pairs = qa_generator.generate_from_document(
                document_id=document_id,
                db=db,
                num_pairs=num_pairs,
                strategy=strategy
            )
        else:
            # Generate from all documents (limit to recent ones)
            documents = db.get_all_knowledge_items(organization_id=organization_id)[:5]

            pairs_per_doc = max(1, num_pairs // len(documents)) if documents else 0

            for doc in documents:
                doc_pairs = qa_generator.generate_from_document(
                    document_id=doc.id,
                    db=db,
                    num_pairs=pairs_per_doc,
                    strategy=strategy
                )
                generated_pairs.extend(doc_pairs)

                if len(generated_pairs) >= num_pairs:
                    break

        # Format results
        results = []
        for qa in generated_pairs[:num_pairs]:
            results.append({
                'question': qa.question,
                'answer': qa.answer,
                'category': qa.category,
                'confidence': qa.confidence,
                'tags': qa.tags,
                'source_document_id': qa.source_document_id,
                'source_chunk_id': qa.source_chunk_id
            })

        saved_ids = []
        if auto_save and results:
            saved_ids = qa_generator.save_generated_qa(
                qa_pairs=generated_pairs[:num_pairs],
                db=db,
                organization_id=organization_id,
                created_by=user_id
            )

        return jsonify({
            'status': 'success',
            'generated': len(results),
            'qa_pairs': results,
            'saved_ids': saved_ids if auto_save else None
        })

    except Exception as e:
        logger.error(f"Q&A generation error: {e}", exc_info=True)
        return jsonify({'error': f'Failed to generate Q&A: {str(e)}'}), 500


@app.route('/api/qa/generate/<document_id>', methods=['POST'])
def api_generate_qa_for_document(document_id):
    """Generate Q&A pairs for a specific document."""
    data = request.get_json() or {}
    data['document_id'] = document_id
    return api_generate_qa()


@app.route('/api/qa/bulk-save', methods=['POST'])
def api_bulk_save_qa():
    """
    Save multiple generated Q&A pairs.

    Request body:
    {
        "qa_pairs": [
            {"question": "...", "answer": "...", "category": "...", "tags": []},
            ...
        ]
    }
    """
    data = request.get_json()
    if not data or 'qa_pairs' not in data:
        return jsonify({'error': 'qa_pairs is required'}), 400

    # Get tenant context
    organization_id, user_id = get_tenant_context()

    try:
        saved_ids = []
        for qa_data in data['qa_pairs']:
            if not qa_data.get('question') or not qa_data.get('answer'):
                continue

            qa = DirectQA(
                question=qa_data['question'],
                answer=qa_data['answer'],
                category=qa_data.get('category', 'Generated'),
                tags=qa_data.get('tags', []),
                organization_id=organization_id,
                created_by=user_id
            )
            qa_id = db.add_direct_qa(qa)
            saved_ids.append(qa_id)

        return jsonify({
            'status': 'success',
            'saved': len(saved_ids),
            'qa_ids': saved_ids
        })

    except Exception as e:
        logger.error(f"Bulk save Q&A error: {e}")
        return jsonify({'error': 'Failed to save Q&A pairs'}), 500


@app.route('/api/qa/suggestions', methods=['GET'])
def api_get_qa_suggestions():
    """
    Get suggested Q&A pairs based on knowledge gaps and common queries.

    Returns suggestions for Q&A pairs that could improve the knowledge base.
    """
    organization_id, _ = get_tenant_context()

    try:
        suggestions = []

        # Get knowledge gaps (unanswered questions)
        gaps = db.get_knowledge_gaps(organization_id=organization_id, resolved=False, limit=10)
        for gap in gaps:
            suggestions.append({
                'type': 'knowledge_gap',
                'question': gap.query_text,
                'reason': f'Asked {gap.occurrence_count} times without good answer',
                'gap_id': gap.id
            })

        # Get recent negative feedback queries
        queries = db.get_queries(organization_id=organization_id, limit=50)
        negative_queries = [q for q in queries if q.feedback == 'negative'][:5]

        for query in negative_queries:
            suggestions.append({
                'type': 'negative_feedback',
                'question': query.question,
                'current_answer': query.answer,
                'reason': 'Received negative feedback',
                'query_id': query.id
            })

        return jsonify({
            'suggestions': suggestions,
            'total': len(suggestions)
        })

    except Exception as e:
        logger.error(f"Get Q&A suggestions error: {e}")
        return jsonify({'error': 'Failed to get suggestions'}), 500


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
