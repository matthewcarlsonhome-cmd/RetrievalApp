"""
Document parsers for various file formats.
Extracts text from PDF, DOCX, Markdown, Excel, PowerPoint, Email, and more.
"""

import re
import os
import json
import email
import logging
from pathlib import Path
from typing import Optional, Tuple, Union, List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# Supported file extensions
SUPPORTED_EXTENSIONS = {
    # Documents
    ".pdf", ".docx", ".doc", ".md", ".txt", ".html", ".htm",
    # Spreadsheets
    ".xlsx", ".xls", ".csv",
    # Presentations
    ".pptx", ".ppt",
    # Email
    ".eml", ".mbox",
    # Exports
    ".json",  # Confluence/Notion exports
    # Audio (requires Whisper)
    ".mp3", ".wav", ".m4a", ".ogg", ".flac", ".webm"
}

# Categories for file types
FILE_CATEGORIES = {
    "document": {".pdf", ".docx", ".doc", ".md", ".txt", ".html", ".htm"},
    "spreadsheet": {".xlsx", ".xls", ".csv"},
    "presentation": {".pptx", ".ppt"},
    "email": {".eml", ".mbox"},
    "export": {".json"},
    "audio": {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".webm"}
}


def get_file_category(file_path: Union[str, Path]) -> str:
    """Get the category of a file based on extension."""
    if isinstance(file_path, str):
        file_path = Path(file_path)
    suffix = file_path.suffix.lower()

    for category, extensions in FILE_CATEGORIES.items():
        if suffix in extensions:
            return category
    return "unknown"


def extract_text(file_path: Union[str, Path], content: bytes = None) -> Tuple[str, str]:
    """
    Extract text from a file.

    Args:
        file_path: Path to the file (string or Path object)
        content: Optional file content bytes (if already read)

    Returns:
        Tuple of (extracted_text, title)
    """
    # Convert string to Path if needed
    if isinstance(file_path, str):
        file_path = Path(file_path)

    suffix = file_path.suffix.lower()

    # Documents
    if suffix == ".pdf":
        return extract_pdf(file_path, content)
    elif suffix in [".docx", ".doc"]:
        return extract_docx(file_path, content)
    elif suffix == ".md":
        return extract_markdown(file_path, content)
    elif suffix in [".txt", ".text"]:
        return extract_text_file(file_path, content)
    elif suffix in [".html", ".htm"]:
        return extract_html(file_path, content)

    # Spreadsheets
    elif suffix in [".xlsx", ".xls"]:
        return extract_excel(file_path, content)
    elif suffix == ".csv":
        return extract_csv(file_path, content)

    # Presentations
    elif suffix in [".pptx", ".ppt"]:
        return extract_powerpoint(file_path, content)

    # Email
    elif suffix == ".eml":
        return extract_eml(file_path, content)
    elif suffix == ".mbox":
        return extract_mbox(file_path, content)

    # Exports (Confluence/Notion)
    elif suffix == ".json":
        return extract_json_export(file_path, content)

    # Audio
    elif suffix in [".mp3", ".wav", ".m4a", ".ogg", ".flac", ".webm"]:
        return extract_audio(file_path, content)

    else:
        raise ValueError(f"Unsupported file type: {suffix}")


def parse_document(file_path: Union[str, Path], content: bytes = None) -> dict:
    """
    Parse a document and return structured data.

    Args:
        file_path: Path to the file (string or Path object)
        content: Optional file content bytes

    Returns:
        Dictionary with title, content, and metadata
    """
    # Convert string to Path if needed
    if isinstance(file_path, str):
        file_path = Path(file_path)

    text, title = extract_text(file_path, content)

    # Clean up the text
    text = clean_text(text)

    return {
        "title": title or file_path.stem,
        "content": text,
        "source_file": str(file_path.name),
        "file_type": file_path.suffix.lower(),
        "category": get_file_category(file_path)
    }


# =============================================================================
# DOCUMENT EXTRACTORS
# =============================================================================

def extract_pdf(file_path: Path, content: bytes = None) -> Tuple[str, str]:
    """Extract text from PDF."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.warning("PyMuPDF not installed. PDF parsing limited.")
        return "", file_path.stem

    try:
        if content:
            doc = fitz.open(stream=content, filetype="pdf")
        else:
            doc = fitz.open(str(file_path))

        text_parts = []
        for page in doc:
            text_parts.append(page.get_text())

        text = "\n".join(text_parts)

        # Try to get title from metadata or first line
        title = doc.metadata.get("title", "") or file_path.stem

        doc.close()
        return text, title

    except Exception as e:
        logger.error(f"Error parsing PDF {file_path}: {e}")
        return "", file_path.stem


def extract_docx(file_path: Path, content: bytes = None) -> Tuple[str, str]:
    """Extract text from DOCX."""
    try:
        from docx import Document
    except ImportError:
        logger.warning("python-docx not installed. DOCX parsing limited.")
        return "", file_path.stem

    try:
        if content:
            from io import BytesIO
            doc = Document(BytesIO(content))
        else:
            doc = Document(str(file_path))

        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        text = "\n\n".join(paragraphs)

        # Title is usually the first heading or paragraph
        title = paragraphs[0] if paragraphs else file_path.stem

        return text, title

    except Exception as e:
        logger.error(f"Error parsing DOCX {file_path}: {e}")
        return "", file_path.stem


def extract_markdown(file_path: Path, content: bytes = None) -> Tuple[str, str]:
    """Extract text from Markdown."""
    try:
        if content:
            text = content.decode("utf-8")
        else:
            text = file_path.read_text(encoding="utf-8")

        # Extract title from first H1
        title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        title = title_match.group(1) if title_match else file_path.stem

        # Strip markdown formatting for plain text
        text = strip_markdown(text)

        return text, title

    except Exception as e:
        logger.error(f"Error parsing Markdown {file_path}: {e}")
        return "", file_path.stem


def extract_text_file(file_path: Path, content: bytes = None) -> Tuple[str, str]:
    """Extract text from plain text file."""
    try:
        if content:
            text = content.decode("utf-8")
        else:
            text = file_path.read_text(encoding="utf-8")

        # Title is first non-empty line or filename
        lines = text.strip().split("\n")
        title = next((line.strip() for line in lines if line.strip()), file_path.stem)

        return text, title

    except Exception as e:
        logger.error(f"Error parsing text file {file_path}: {e}")
        return "", file_path.stem


def extract_html(file_path: Path, content: bytes = None) -> Tuple[str, str]:
    """Extract text from HTML."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        logger.warning("BeautifulSoup not installed. HTML parsing limited.")
        # Fallback: strip HTML tags with regex
        if content:
            text = content.decode("utf-8")
        else:
            text = file_path.read_text(encoding="utf-8")
        text = re.sub(r"<[^>]+>", " ", text)
        return text, file_path.stem

    try:
        if content:
            html = content.decode("utf-8")
        else:
            html = file_path.read_text(encoding="utf-8")

        soup = BeautifulSoup(html, "html.parser")

        # Remove script and style elements
        for element in soup(["script", "style", "nav", "footer", "header"]):
            element.decompose()

        # Get title
        title = soup.title.string if soup.title else file_path.stem

        # Get text
        text = soup.get_text(separator="\n", strip=True)

        return text, title

    except Exception as e:
        logger.error(f"Error parsing HTML {file_path}: {e}")
        return "", file_path.stem


# =============================================================================
# SPREADSHEET EXTRACTORS
# =============================================================================

def extract_excel(file_path: Path, content: bytes = None) -> Tuple[str, str]:
    """Extract text from Excel files (.xlsx, .xls)."""
    try:
        import openpyxl
    except ImportError:
        logger.warning("openpyxl not installed. Excel parsing unavailable.")
        return "", file_path.stem

    try:
        if content:
            from io import BytesIO
            workbook = openpyxl.load_workbook(BytesIO(content), data_only=True)
        else:
            workbook = openpyxl.load_workbook(str(file_path), data_only=True)

        text_parts = []

        for sheet_name in workbook.sheetnames:
            sheet = workbook[sheet_name]
            text_parts.append(f"\n## Sheet: {sheet_name}\n")

            # Get all rows
            rows = []
            for row in sheet.iter_rows(values_only=True):
                # Filter out completely empty rows
                if any(cell is not None for cell in row):
                    row_text = " | ".join(str(cell) if cell is not None else "" for cell in row)
                    rows.append(row_text)

            # First row as header if it looks like headers
            if rows:
                text_parts.append("Headers: " + rows[0])
                text_parts.append("\nData:")
                text_parts.extend(rows[1:])

        workbook.close()
        text = "\n".join(text_parts)
        title = file_path.stem

        return text, title

    except Exception as e:
        logger.error(f"Error parsing Excel {file_path}: {e}")
        return "", file_path.stem


def extract_csv(file_path: Path, content: bytes = None) -> Tuple[str, str]:
    """Extract text from CSV files."""
    import csv
    from io import StringIO

    try:
        if content:
            text_content = content.decode("utf-8")
        else:
            text_content = file_path.read_text(encoding="utf-8")

        reader = csv.reader(StringIO(text_content))
        rows = list(reader)

        if not rows:
            return "", file_path.stem

        text_parts = []

        # First row as headers
        headers = rows[0]
        text_parts.append("Headers: " + " | ".join(headers))
        text_parts.append("\nData:")

        # Data rows
        for row in rows[1:]:
            # Create key-value pairs for better semantic understanding
            row_text = ", ".join(f"{headers[i]}: {row[i]}" for i in range(min(len(headers), len(row))))
            text_parts.append(row_text)

        text = "\n".join(text_parts)
        title = file_path.stem

        return text, title

    except Exception as e:
        logger.error(f"Error parsing CSV {file_path}: {e}")
        return "", file_path.stem


# =============================================================================
# PRESENTATION EXTRACTORS
# =============================================================================

def extract_powerpoint(file_path: Path, content: bytes = None) -> Tuple[str, str]:
    """Extract text from PowerPoint files (.pptx)."""
    try:
        from pptx import Presentation
    except ImportError:
        logger.warning("python-pptx not installed. PowerPoint parsing unavailable.")
        return "", file_path.stem

    try:
        if content:
            from io import BytesIO
            prs = Presentation(BytesIO(content))
        else:
            prs = Presentation(str(file_path))

        text_parts = []
        title = file_path.stem

        for slide_num, slide in enumerate(prs.slides, 1):
            slide_text = []
            slide_text.append(f"\n## Slide {slide_num}\n")

            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text.strip():
                    slide_text.append(shape.text)

                # Handle tables
                if shape.has_table:
                    table = shape.table
                    for row in table.rows:
                        row_text = " | ".join(cell.text for cell in row.cells)
                        slide_text.append(row_text)

            text_parts.extend(slide_text)

            # First slide title is often the document title
            if slide_num == 1 and slide_text:
                title = slide_text[1] if len(slide_text) > 1 else file_path.stem

        text = "\n".join(text_parts)
        return text, title

    except Exception as e:
        logger.error(f"Error parsing PowerPoint {file_path}: {e}")
        return "", file_path.stem


# =============================================================================
# EMAIL EXTRACTORS
# =============================================================================

def extract_eml(file_path: Path, content: bytes = None) -> Tuple[str, str]:
    """Extract text from .eml email files."""
    try:
        if content:
            msg = email.message_from_bytes(content)
        else:
            with open(file_path, 'rb') as f:
                msg = email.message_from_bytes(f.read())

        # Extract headers
        subject = msg.get('Subject', 'No Subject')
        from_addr = msg.get('From', 'Unknown')
        to_addr = msg.get('To', 'Unknown')
        date = msg.get('Date', 'Unknown')

        text_parts = [
            f"Subject: {subject}",
            f"From: {from_addr}",
            f"To: {to_addr}",
            f"Date: {date}",
            "\n--- Email Body ---\n"
        ]

        # Extract body
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        text_parts.append(payload.decode('utf-8', errors='ignore'))
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                text_parts.append(payload.decode('utf-8', errors='ignore'))

        text = "\n".join(text_parts)
        title = subject

        return text, title

    except Exception as e:
        logger.error(f"Error parsing EML {file_path}: {e}")
        return "", file_path.stem


def extract_mbox(file_path: Path, content: bytes = None) -> Tuple[str, str]:
    """Extract text from .mbox email archive files."""
    import mailbox

    try:
        # mbox requires file path, not bytes
        if content:
            # Write to temp file
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mbox') as tmp:
                tmp.write(content)
                tmp_path = tmp.name
            mbox = mailbox.mbox(tmp_path)
        else:
            mbox = mailbox.mbox(str(file_path))

        text_parts = []
        email_count = 0

        for message in mbox:
            email_count += 1
            subject = message.get('Subject', 'No Subject')
            from_addr = message.get('From', 'Unknown')
            date = message.get('Date', 'Unknown')

            text_parts.append(f"\n--- Email {email_count} ---")
            text_parts.append(f"Subject: {subject}")
            text_parts.append(f"From: {from_addr}")
            text_parts.append(f"Date: {date}")

            # Get body
            if message.is_multipart():
                for part in message.walk():
                    if part.get_content_type() == "text/plain":
                        payload = part.get_payload(decode=True)
                        if payload:
                            text_parts.append(payload.decode('utf-8', errors='ignore'))
            else:
                payload = message.get_payload(decode=True)
                if payload:
                    text_parts.append(payload.decode('utf-8', errors='ignore'))

        mbox.close()

        # Clean up temp file if created
        if content:
            os.unlink(tmp_path)

        text = "\n".join(text_parts)
        title = f"Email Archive ({email_count} emails)"

        return text, title

    except Exception as e:
        logger.error(f"Error parsing MBOX {file_path}: {e}")
        return "", file_path.stem


# =============================================================================
# EXPORT EXTRACTORS (Confluence/Notion)
# =============================================================================

def extract_json_export(file_path: Path, content: bytes = None) -> Tuple[str, str]:
    """
    Extract text from JSON exports (Confluence, Notion, etc.).

    Supports:
    - Confluence space exports
    - Notion database exports
    - Generic JSON with text fields
    """
    try:
        if content:
            data = json.loads(content.decode('utf-8'))
        else:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

        text_parts = []
        title = file_path.stem

        # Detect export type and extract accordingly
        if isinstance(data, dict):
            # Confluence-style export
            if 'results' in data and isinstance(data['results'], list):
                text, title = _extract_confluence_export(data)
                return text, title

            # Notion-style export
            if 'pages' in data or 'blocks' in data:
                text, title = _extract_notion_export(data)
                return text, title

            # Generic dict - extract all text values
            text = _extract_json_text(data)
            if 'title' in data:
                title = str(data['title'])
            elif 'name' in data:
                title = str(data['name'])

        elif isinstance(data, list):
            # List of items (like Notion database export)
            for i, item in enumerate(data):
                if isinstance(item, dict):
                    item_text = _extract_json_text(item)
                    if item_text.strip():
                        text_parts.append(f"\n--- Item {i+1} ---\n{item_text}")
            text = "\n".join(text_parts)
            title = f"Export ({len(data)} items)"
        else:
            text = str(data)

        return text, title

    except Exception as e:
        logger.error(f"Error parsing JSON export {file_path}: {e}")
        return "", file_path.stem


def _extract_confluence_export(data: dict) -> Tuple[str, str]:
    """Extract text from Confluence space export."""
    text_parts = []
    title = data.get('title', data.get('name', 'Confluence Export'))

    results = data.get('results', [])
    for page in results:
        page_title = page.get('title', 'Untitled')
        text_parts.append(f"\n## {page_title}\n")

        # Get body content
        body = page.get('body', {})
        if 'storage' in body:
            # HTML content - strip tags
            html_content = body['storage'].get('value', '')
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            text_parts.append(soup.get_text(separator='\n', strip=True))
        elif 'view' in body:
            html_content = body['view'].get('value', '')
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            text_parts.append(soup.get_text(separator='\n', strip=True))

    return "\n".join(text_parts), title


def _extract_notion_export(data: dict) -> Tuple[str, str]:
    """Extract text from Notion export."""
    text_parts = []
    title = data.get('title', data.get('name', 'Notion Export'))

    # Handle pages
    pages = data.get('pages', [])
    for page in pages:
        page_title = page.get('title', page.get('name', 'Untitled'))
        text_parts.append(f"\n## {page_title}\n")

        # Extract content from blocks
        blocks = page.get('blocks', page.get('content', []))
        for block in blocks:
            block_text = _extract_notion_block(block)
            if block_text:
                text_parts.append(block_text)

    # Handle blocks at root level
    blocks = data.get('blocks', [])
    for block in blocks:
        block_text = _extract_notion_block(block)
        if block_text:
            text_parts.append(block_text)

    return "\n".join(text_parts), title


def _extract_notion_block(block: dict) -> str:
    """Extract text from a Notion block."""
    block_type = block.get('type', '')

    # Text content
    if 'text' in block:
        if isinstance(block['text'], list):
            return " ".join(t.get('plain_text', '') for t in block['text'])
        return str(block['text'])

    # Rich text
    if 'rich_text' in block:
        if isinstance(block['rich_text'], list):
            return " ".join(t.get('plain_text', '') for t in block['rich_text'])

    # Paragraph, heading, etc.
    if block_type in block:
        type_content = block[block_type]
        if isinstance(type_content, dict) and 'rich_text' in type_content:
            return " ".join(t.get('plain_text', '') for t in type_content['rich_text'])

    return ""


def _extract_json_text(obj: Any, max_depth: int = 5) -> str:
    """Recursively extract text from JSON object."""
    if max_depth <= 0:
        return ""

    if isinstance(obj, str):
        return obj
    elif isinstance(obj, (int, float, bool)):
        return str(obj)
    elif isinstance(obj, list):
        texts = [_extract_json_text(item, max_depth - 1) for item in obj]
        return "\n".join(t for t in texts if t.strip())
    elif isinstance(obj, dict):
        texts = []
        for key, value in obj.items():
            if key.lower() in ['id', 'created', 'modified', 'version', 'revision']:
                continue  # Skip metadata fields
            extracted = _extract_json_text(value, max_depth - 1)
            if extracted.strip():
                texts.append(f"{key}: {extracted}")
        return "\n".join(texts)
    return ""


# =============================================================================
# AUDIO EXTRACTORS (Whisper)
# =============================================================================

def extract_audio(file_path: Path, content: bytes = None) -> Tuple[str, str]:
    """
    Extract text from audio files using OpenAI Whisper.

    Requires: openai-whisper or whisper API
    """
    # Try local Whisper first
    try:
        import whisper
        return _extract_audio_whisper_local(file_path, content)
    except ImportError:
        pass

    # Try OpenAI Whisper API
    try:
        import openai
        return _extract_audio_whisper_api(file_path, content)
    except ImportError:
        pass

    logger.warning("Neither whisper nor openai is installed. Audio transcription unavailable.")
    return "", file_path.stem


def _extract_audio_whisper_local(file_path: Path, content: bytes = None) -> Tuple[str, str]:
    """Transcribe audio using local Whisper model."""
    import whisper
    import tempfile

    try:
        # Whisper needs a file path
        if content:
            suffix = file_path.suffix
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(content)
                tmp_path = tmp.name
            audio_path = tmp_path
        else:
            audio_path = str(file_path)

        # Load model (use base for speed, can use larger for accuracy)
        model_name = os.environ.get("WHISPER_MODEL", "base")
        model = whisper.load_model(model_name)

        # Transcribe
        result = model.transcribe(audio_path)
        text = result["text"]

        # Clean up temp file
        if content:
            os.unlink(tmp_path)

        title = f"Transcript: {file_path.stem}"
        return text, title

    except Exception as e:
        logger.error(f"Error transcribing audio {file_path}: {e}")
        return "", file_path.stem


def _extract_audio_whisper_api(file_path: Path, content: bytes = None) -> Tuple[str, str]:
    """Transcribe audio using OpenAI Whisper API."""
    import openai
    import tempfile

    try:
        client = openai.OpenAI()

        if content:
            suffix = file_path.suffix
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(content)
                tmp_path = tmp.name
            audio_file = open(tmp_path, "rb")
        else:
            audio_file = open(file_path, "rb")

        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file
        )
        audio_file.close()

        # Clean up temp file
        if content:
            os.unlink(tmp_path)

        title = f"Transcript: {file_path.stem}"
        return transcript.text, title

    except Exception as e:
        logger.error(f"Error transcribing audio via API {file_path}: {e}")
        return "", file_path.stem


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def strip_markdown(text: str) -> str:
    """Remove markdown formatting for plain text."""
    # Remove code blocks
    text = re.sub(r"```[\s\S]*?```", "", text)
    # Remove inline code
    text = re.sub(r"`[^`]+`", "", text)
    # Remove header markers
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # Remove bold/italic
    text = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", text)
    text = re.sub(r"_{1,2}([^_]+)_{1,2}", r"\1", text)
    # Remove links, keep text
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # Remove images
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text)
    return text


def clean_text(text: str) -> str:
    """Clean and normalize text."""
    # Normalize whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    # Remove control characters
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    return text.strip()


def is_supported_file(file_path: Union[str, Path]) -> bool:
    """Check if a file type is supported."""
    if isinstance(file_path, str):
        file_path = Path(file_path)
    return file_path.suffix.lower() in SUPPORTED_EXTENSIONS


def get_parser_requirements() -> Dict[str, List[str]]:
    """Get required packages for each file type."""
    return {
        "pdf": ["pymupdf (fitz)"],
        "docx": ["python-docx"],
        "html": ["beautifulsoup4"],
        "xlsx": ["openpyxl"],
        "csv": [],  # Built-in
        "pptx": ["python-pptx"],
        "eml": [],  # Built-in
        "mbox": [],  # Built-in
        "json": [],  # Built-in
        "audio": ["openai-whisper OR openai (for API)"],
    }
