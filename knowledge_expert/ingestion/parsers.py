"""
Document parsers for various file formats.
Extracts text from PDF, DOCX, Markdown, and plain text files.
"""

import re
from pathlib import Path
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


def extract_text(file_path: Path, content: bytes = None) -> Tuple[str, str]:
    """
    Extract text from a file.

    Args:
        file_path: Path to the file
        content: Optional file content bytes (if already read)

    Returns:
        Tuple of (extracted_text, title)
    """
    suffix = file_path.suffix.lower()

    if suffix == ".pdf":
        return extract_pdf(file_path, content)
    elif suffix == ".docx":
        return extract_docx(file_path, content)
    elif suffix == ".md":
        return extract_markdown(file_path, content)
    elif suffix in [".txt", ".text"]:
        return extract_text_file(file_path, content)
    elif suffix in [".html", ".htm"]:
        return extract_html(file_path, content)
    else:
        raise ValueError(f"Unsupported file type: {suffix}")


def parse_document(file_path: Path, content: bytes = None) -> dict:
    """
    Parse a document and return structured data.

    Args:
        file_path: Path to the file
        content: Optional file content bytes

    Returns:
        Dictionary with title, content, and metadata
    """
    text, title = extract_text(file_path, content)

    # Clean up the text
    text = clean_text(text)

    return {
        "title": title or file_path.stem,
        "content": text,
        "source_file": str(file_path.name),
        "file_type": file_path.suffix.lower()
    }


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
