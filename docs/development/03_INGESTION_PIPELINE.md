# Ingestion Pipeline Specification

## Overview

The ingestion pipeline transforms raw documents into searchable, embedable knowledge chunks. This document provides complete implementation specifications.

---

## Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         INGESTION PIPELINE                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────┐                                                                │
│  │ SOURCE  │  PDF, DOCX, MD, HTML, CSV, JSON                               │
│  │  FILES  │                                                                │
│  └────┬────┘                                                                │
│       │                                                                      │
│       ▼                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ STAGE 1: EXTRACTION                                                  │   │
│  │                                                                       │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │   │
│  │  │   PDF    │  │   DOCX   │  │ Markdown │  │   HTML   │            │   │
│  │  │  Parser  │  │  Parser  │  │  Parser  │  │  Parser  │            │   │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘            │   │
│  │       └─────────────┴─────────────┴─────────────┘                   │   │
│  │                           │                                          │   │
│  │                           ▼                                          │   │
│  │              ┌────────────────────────┐                              │   │
│  │              │   Unified Document     │                              │   │
│  │              │   { title, sections,   │                              │   │
│  │              │     tables, metadata } │                              │   │
│  │              └────────────────────────┘                              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                           │                                                  │
│                           ▼                                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ STAGE 2: CLASSIFICATION                                              │   │
│  │                                                                       │   │
│  │  Detect Type ──▶ Assign Category ──▶ Identify Audience              │   │
│  │  (doc/faq/      (product/policy/     (customer/employee/            │   │
│  │   workflow)      technical)           partner)                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                           │                                                  │
│                           ▼                                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ STAGE 3: CHUNKING                                                    │   │
│  │                                                                       │   │
│  │  ┌────────────────────────────────────────────────────────────────┐ │   │
│  │  │ Strategy Selection                                              │ │   │
│  │  │                                                                  │ │   │
│  │  │  Document ──▶ Semantic Chunking (by section)                   │ │   │
│  │  │  FAQ ──▶ Keep Q&A pairs intact                                 │ │   │
│  │  │  Workflow ──▶ Step-based chunking                              │ │   │
│  │  │  Table ──▶ Row-based with header context                       │ │   │
│  │  └────────────────────────────────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                           │                                                  │
│                           ▼                                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ STAGE 4: ENRICHMENT                                                  │   │
│  │                                                                       │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐    │   │
│  │  │  Generate  │  │  Extract   │  │  Generate  │  │   Link     │    │   │
│  │  │  Summary   │  │  Entities  │  │  Q&A Pairs │  │  Related   │    │   │
│  │  │   (LLM)    │  │  (NER)     │  │   (LLM)    │  │  Content   │    │   │
│  │  └────────────┘  └────────────┘  └────────────┘  └────────────┘    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                           │                                                  │
│                           ▼                                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ STAGE 5: EMBEDDING                                                   │   │
│  │                                                                       │   │
│  │  Sentence-Transformers (all-MiniLM-L6-v2 or fine-tuned)             │   │
│  │                                                                       │   │
│  │  Generate embeddings for:                                            │   │
│  │  • Chunk content                                                     │   │
│  │  • Chunk summary (if available)                                      │   │
│  │  • FAQ questions (for FAQ matcher)                                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                           │                                                  │
│                           ▼                                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ STAGE 6: INDEXING                                                    │   │
│  │                                                                       │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐    │   │
│  │  │  Vector    │  │   BM25     │  │    FAQ     │  │  Metadata  │    │   │
│  │  │   Store    │  │   Index    │  │   Index    │  │   Index    │    │   │
│  │  │ (Pinecone) │  │  (Elastic) │  │  (Vector)  │  │ (Postgres) │    │   │
│  │  └────────────┘  └────────────┘  └────────────┘  └────────────┘    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                           │                                                  │
│                           ▼                                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ STAGE 7: VALIDATION                                                  │   │
│  │                                                                       │   │
│  │  • Duplicate detection                                               │   │
│  │  • Link verification                                                 │   │
│  │  • Quality scoring                                                   │   │
│  │  • Freshness check                                                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Stage 1: Extraction

### Parser Interface

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime


@dataclass
class Section:
    """Represents a document section."""
    title: str
    content: str
    level: int  # Heading level (1-6)
    subsections: List['Section'] = None


@dataclass
class Table:
    """Represents a table in a document."""
    headers: List[str]
    rows: List[List[str]]
    caption: Optional[str] = None


@dataclass
class ExtractedDocument:
    """Unified output from all parsers."""
    # Content
    title: str
    content: str  # Full text content
    sections: List[Section]
    tables: List[Table]

    # Metadata
    source_file: str
    file_type: str
    author: Optional[str] = None
    created_date: Optional[datetime] = None
    modified_date: Optional[datetime] = None
    page_count: Optional[int] = None

    # Raw data
    raw_text: str = ""


class BaseParser(ABC):
    """Base class for all document parsers."""

    @abstractmethod
    def parse(self, file_path: str) -> ExtractedDocument:
        """Parse a file and return ExtractedDocument."""
        pass

    @abstractmethod
    def supports(self, file_extension: str) -> bool:
        """Check if parser supports this file type."""
        pass
```

### PDF Parser

```python
import fitz  # PyMuPDF
from typing import List


class PDFParser(BaseParser):
    """Extract text and structure from PDF files."""

    def supports(self, file_extension: str) -> bool:
        return file_extension.lower() in ['.pdf']

    def parse(self, file_path: str) -> ExtractedDocument:
        doc = fitz.open(file_path)

        sections = []
        tables = []
        full_text = []

        for page_num, page in enumerate(doc):
            # Extract text blocks with formatting info
            blocks = page.get_text("dict")["blocks"]

            for block in blocks:
                if block["type"] == 0:  # Text block
                    for line in block.get("lines", []):
                        text = "".join(span["text"] for span in line["spans"])
                        font_size = line["spans"][0]["size"] if line["spans"] else 12

                        # Detect headings by font size
                        if font_size > 14:
                            sections.append(Section(
                                title=text.strip(),
                                content="",
                                level=1 if font_size > 18 else 2
                            ))
                        else:
                            full_text.append(text)

                            # Add to current section
                            if sections:
                                sections[-1].content += text + " "

            # Extract tables
            tables.extend(self._extract_tables(page))

        return ExtractedDocument(
            title=self._extract_title(doc),
            content="\n".join(full_text),
            sections=sections,
            tables=tables,
            source_file=file_path,
            file_type="pdf",
            page_count=len(doc),
            author=doc.metadata.get("author"),
            raw_text="\n".join(full_text)
        )

    def _extract_title(self, doc) -> str:
        """Extract title from metadata or first heading."""
        if doc.metadata.get("title"):
            return doc.metadata["title"]

        # Fallback: first large text on first page
        first_page = doc[0]
        blocks = first_page.get_text("dict")["blocks"]
        for block in blocks:
            if block["type"] == 0:
                for line in block.get("lines", []):
                    if line["spans"] and line["spans"][0]["size"] > 16:
                        return "".join(span["text"] for span in line["spans"]).strip()

        return "Untitled Document"

    def _extract_tables(self, page) -> List[Table]:
        """Extract tables from PDF page."""
        tables = []
        # Use tabula-py or camelot for better table extraction
        # This is a simplified version
        return tables
```

### Markdown Parser

```python
import re
from typing import List, Tuple


class MarkdownParser(BaseParser):
    """Parse Markdown files preserving structure."""

    def supports(self, file_extension: str) -> bool:
        return file_extension.lower() in ['.md', '.markdown']

    def parse(self, file_path: str) -> ExtractedDocument:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract title (first H1 or filename)
        title = self._extract_title(content, file_path)

        # Parse sections by headings
        sections = self._parse_sections(content)

        # Extract tables
        tables = self._extract_tables(content)

        return ExtractedDocument(
            title=title,
            content=self._strip_markdown(content),
            sections=sections,
            tables=tables,
            source_file=file_path,
            file_type="markdown",
            raw_text=content
        )

    def _extract_title(self, content: str, file_path: str) -> str:
        """Extract title from first H1 or filename."""
        h1_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if h1_match:
            return h1_match.group(1).strip()
        return file_path.split('/')[-1].replace('.md', '')

    def _parse_sections(self, content: str) -> List[Section]:
        """Parse markdown into sections by heading."""
        sections = []
        current_section = None

        for line in content.split('\n'):
            heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)

            if heading_match:
                level = len(heading_match.group(1))
                title = heading_match.group(2).strip()

                if current_section:
                    sections.append(current_section)

                current_section = Section(
                    title=title,
                    content="",
                    level=level
                )
            elif current_section:
                current_section.content += line + "\n"

        if current_section:
            sections.append(current_section)

        return sections

    def _extract_tables(self, content: str) -> List[Table]:
        """Extract markdown tables."""
        tables = []
        table_pattern = r'\|(.+)\|\n\|[-|\s]+\|\n((?:\|.+\|\n)+)'

        for match in re.finditer(table_pattern, content):
            headers = [h.strip() for h in match.group(1).split('|') if h.strip()]
            rows = []
            for row_line in match.group(2).strip().split('\n'):
                row = [cell.strip() for cell in row_line.split('|') if cell.strip()]
                rows.append(row)
            tables.append(Table(headers=headers, rows=rows))

        return tables

    def _strip_markdown(self, content: str) -> str:
        """Remove markdown formatting for plain text."""
        # Remove code blocks
        content = re.sub(r'```[\s\S]*?```', '', content)
        # Remove inline code
        content = re.sub(r'`[^`]+`', '', content)
        # Remove headers markers
        content = re.sub(r'^#{1,6}\s+', '', content, flags=re.MULTILINE)
        # Remove bold/italic
        content = re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', content)
        # Remove links, keep text
        content = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', content)
        return content
```

### DOCX Parser

```python
from docx import Document as DocxDocument
from docx.shared import Pt


class DOCXParser(BaseParser):
    """Parse Microsoft Word documents."""

    def supports(self, file_extension: str) -> bool:
        return file_extension.lower() in ['.docx', '.doc']

    def parse(self, file_path: str) -> ExtractedDocument:
        doc = DocxDocument(file_path)

        sections = []
        tables = []
        full_text = []
        current_section = None

        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue

            # Check if it's a heading
            if para.style.name.startswith('Heading'):
                level = int(para.style.name.replace('Heading ', '') or '1')

                if current_section:
                    sections.append(current_section)

                current_section = Section(
                    title=text,
                    content="",
                    level=level
                )
            else:
                full_text.append(text)
                if current_section:
                    current_section.content += text + "\n"

        if current_section:
            sections.append(current_section)

        # Extract tables
        for table in doc.tables:
            headers = [cell.text for cell in table.rows[0].cells]
            rows = [
                [cell.text for cell in row.cells]
                for row in table.rows[1:]
            ]
            tables.append(Table(headers=headers, rows=rows))

        return ExtractedDocument(
            title=sections[0].title if sections else "Untitled",
            content="\n".join(full_text),
            sections=sections,
            tables=tables,
            source_file=file_path,
            file_type="docx",
            raw_text="\n".join(full_text)
        )
```

### HTML Parser

```python
from bs4 import BeautifulSoup
import re


class HTMLParser(BaseParser):
    """Parse HTML documents."""

    def supports(self, file_extension: str) -> bool:
        return file_extension.lower() in ['.html', '.htm']

    def parse(self, file_path: str) -> ExtractedDocument:
        with open(file_path, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f.read(), 'html.parser')

        # Remove script and style elements
        for element in soup(['script', 'style', 'nav', 'footer', 'header']):
            element.decompose()

        # Extract title
        title = soup.title.string if soup.title else "Untitled"

        # Parse sections from headings
        sections = self._extract_sections(soup)

        # Extract tables
        tables = self._extract_tables(soup)

        # Get plain text
        text = soup.get_text(separator='\n', strip=True)

        return ExtractedDocument(
            title=title,
            content=text,
            sections=sections,
            tables=tables,
            source_file=file_path,
            file_type="html",
            raw_text=text
        )

    def _extract_sections(self, soup) -> List[Section]:
        """Extract sections based on heading tags."""
        sections = []
        current_section = None

        for element in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p']):
            if element.name.startswith('h'):
                level = int(element.name[1])

                if current_section:
                    sections.append(current_section)

                current_section = Section(
                    title=element.get_text(strip=True),
                    content="",
                    level=level
                )
            elif current_section and element.name == 'p':
                current_section.content += element.get_text(strip=True) + "\n"

        if current_section:
            sections.append(current_section)

        return sections

    def _extract_tables(self, soup) -> List[Table]:
        """Extract HTML tables."""
        tables = []

        for table in soup.find_all('table'):
            headers = []
            rows = []

            # Get headers from <th> or first row
            header_row = table.find('tr')
            if header_row:
                headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]

            # Get data rows
            for tr in table.find_all('tr')[1:]:
                row = [td.get_text(strip=True) for td in tr.find_all('td')]
                if row:
                    rows.append(row)

            if headers or rows:
                tables.append(Table(headers=headers, rows=rows))

        return tables
```

---

## Stage 2: Classification

### Document Classifier

```python
from enum import Enum
from typing import Tuple
import re


class KnowledgeType(Enum):
    DOCUMENT = "document"
    FAQ = "faq"
    WORKFLOW = "workflow"
    PRODUCT = "product"


class ContentCategory(Enum):
    PRODUCT = "product"
    TECHNICAL = "technical"
    POLICY = "policy"
    SUPPORT = "support"
    TRAINING = "training"


class Audience(Enum):
    CUSTOMER = "customer"
    EMPLOYEE = "employee"
    PARTNER = "partner"
    PUBLIC = "public"


class DocumentClassifier:
    """Classify documents by type, category, and audience."""

    # Patterns for detection
    FAQ_PATTERNS = [
        r'\bQ:\s*.+\nA:\s*.+',
        r'\bQuestion:\s*.+\nAnswer:\s*.+',
        r'^\s*\d+\.\s+.+\?',  # Numbered questions
        r'^\s*[-•]\s+.+\?',   # Bulleted questions
    ]

    WORKFLOW_PATTERNS = [
        r'\bStep\s+\d+:',
        r'^\s*\d+\.\s+',      # Numbered steps
        r'\bProcedure:',
        r'\bProcess:',
        r'flowchart|diagram',
    ]

    CATEGORY_KEYWORDS = {
        ContentCategory.PRODUCT: ['feature', 'product', 'release', 'version', 'pricing', 'plan'],
        ContentCategory.TECHNICAL: ['api', 'endpoint', 'integration', 'code', 'sdk', 'developer'],
        ContentCategory.POLICY: ['policy', 'procedure', 'compliance', 'regulation', 'guideline'],
        ContentCategory.SUPPORT: ['troubleshoot', 'issue', 'error', 'fix', 'resolve', 'help'],
        ContentCategory.TRAINING: ['training', 'tutorial', 'learn', 'course', 'onboarding'],
    }

    AUDIENCE_KEYWORDS = {
        Audience.CUSTOMER: ['customer', 'user', 'client', 'subscriber'],
        Audience.EMPLOYEE: ['employee', 'staff', 'internal', 'team', 'hr'],
        Audience.PARTNER: ['partner', 'reseller', 'affiliate', 'vendor'],
    }

    def classify(self, document: ExtractedDocument) -> Tuple[KnowledgeType, ContentCategory, Audience]:
        """Classify a document."""
        knowledge_type = self._detect_type(document)
        category = self._detect_category(document)
        audience = self._detect_audience(document)

        return knowledge_type, category, audience

    def _detect_type(self, document: ExtractedDocument) -> KnowledgeType:
        """Detect document type."""
        content = document.content.lower()

        # Check for FAQ patterns
        for pattern in self.FAQ_PATTERNS:
            if re.search(pattern, document.raw_text, re.MULTILINE | re.IGNORECASE):
                return KnowledgeType.FAQ

        # Check for workflow patterns
        for pattern in self.WORKFLOW_PATTERNS:
            if re.search(pattern, document.raw_text, re.MULTILINE | re.IGNORECASE):
                return KnowledgeType.WORKFLOW

        # Check for product info
        if any(kw in content for kw in ['pricing', 'features', 'compare', 'vs']):
            return KnowledgeType.PRODUCT

        return KnowledgeType.DOCUMENT

    def _detect_category(self, document: ExtractedDocument) -> ContentCategory:
        """Detect content category."""
        content = (document.title + " " + document.content).lower()

        scores = {}
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in content)
            scores[category] = score

        if max(scores.values()) > 0:
            return max(scores, key=scores.get)

        return ContentCategory.PRODUCT  # Default

    def _detect_audience(self, document: ExtractedDocument) -> Audience:
        """Detect target audience."""
        content = (document.title + " " + document.content).lower()

        # Check file path for hints
        path = document.source_file.lower()
        if 'internal' in path or 'employee' in path:
            return Audience.EMPLOYEE
        if 'partner' in path:
            return Audience.PARTNER

        # Check content
        for audience, keywords in self.AUDIENCE_KEYWORDS.items():
            if any(kw in content for kw in keywords):
                return audience

        return Audience.PUBLIC  # Default
```

---

## Stage 3: Chunking

### Chunking Strategies

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List
import tiktoken


@dataclass
class Chunk:
    """Represents a chunk of text."""
    content: str
    chunk_index: int
    start_char: int
    end_char: int
    section_title: str = None
    token_count: int = 0
    metadata: dict = None


class BaseChunker(ABC):
    """Base class for chunking strategies."""

    def __init__(self, max_tokens: int = 500, overlap_tokens: int = 50):
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        return len(self.tokenizer.encode(text))

    @abstractmethod
    def chunk(self, document: ExtractedDocument) -> List[Chunk]:
        pass


class SemanticChunker(BaseChunker):
    """Chunk by semantic sections (headings)."""

    def chunk(self, document: ExtractedDocument) -> List[Chunk]:
        chunks = []
        chunk_index = 0

        for section in document.sections:
            section_chunks = self._chunk_section(section, chunk_index)
            chunks.extend(section_chunks)
            chunk_index += len(section_chunks)

        # Handle content not in sections
        if not document.sections:
            chunks = self._chunk_text(document.content, 0)

        return chunks

    def _chunk_section(self, section: Section, start_index: int) -> List[Chunk]:
        """Chunk a single section."""
        chunks = []
        content = f"{section.title}\n\n{section.content}"

        if self.count_tokens(content) <= self.max_tokens:
            # Section fits in one chunk
            chunks.append(Chunk(
                content=content,
                chunk_index=start_index,
                start_char=0,
                end_char=len(content),
                section_title=section.title,
                token_count=self.count_tokens(content)
            ))
        else:
            # Split section content
            sub_chunks = self._chunk_text(
                section.content,
                start_index,
                prefix=f"{section.title}\n\n"
            )
            for chunk in sub_chunks:
                chunk.section_title = section.title
            chunks.extend(sub_chunks)

        return chunks

    def _chunk_text(self, text: str, start_index: int, prefix: str = "") -> List[Chunk]:
        """Split text into chunks with overlap."""
        chunks = []
        sentences = self._split_into_sentences(text)

        current_chunk = prefix
        current_start = 0
        chunk_index = start_index

        for sentence in sentences:
            # Check if adding this sentence exceeds limit
            test_chunk = current_chunk + sentence
            if self.count_tokens(test_chunk) > self.max_tokens and current_chunk != prefix:
                # Save current chunk
                chunks.append(Chunk(
                    content=current_chunk.strip(),
                    chunk_index=chunk_index,
                    start_char=current_start,
                    end_char=current_start + len(current_chunk),
                    token_count=self.count_tokens(current_chunk)
                ))
                chunk_index += 1

                # Start new chunk with overlap
                overlap_text = self._get_overlap(current_chunk)
                current_chunk = prefix + overlap_text + sentence
                current_start += len(current_chunk) - len(overlap_text) - len(sentence)
            else:
                current_chunk = test_chunk

        # Don't forget the last chunk
        if current_chunk.strip() and current_chunk != prefix:
            chunks.append(Chunk(
                content=current_chunk.strip(),
                chunk_index=chunk_index,
                start_char=current_start,
                end_char=current_start + len(current_chunk),
                token_count=self.count_tokens(current_chunk)
            ))

        return chunks

    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        import re
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() + " " for s in sentences if s.strip()]

    def _get_overlap(self, text: str) -> str:
        """Get overlap text from end of chunk."""
        sentences = self._split_into_sentences(text)
        overlap = ""
        for sentence in reversed(sentences):
            if self.count_tokens(overlap + sentence) <= self.overlap_tokens:
                overlap = sentence + overlap
            else:
                break
        return overlap


class FAQChunker(BaseChunker):
    """Keep FAQ pairs together."""

    def chunk(self, document: ExtractedDocument) -> List[Chunk]:
        chunks = []
        qa_pairs = self._extract_qa_pairs(document.raw_text)

        for i, (question, answer) in enumerate(qa_pairs):
            content = f"Q: {question}\nA: {answer}"
            chunks.append(Chunk(
                content=content,
                chunk_index=i,
                start_char=0,
                end_char=len(content),
                token_count=self.count_tokens(content),
                metadata={"question": question, "answer": answer}
            ))

        return chunks

    def _extract_qa_pairs(self, text: str) -> List[Tuple[str, str]]:
        """Extract Q&A pairs from text."""
        import re
        pairs = []

        # Pattern: Q: ... A: ...
        pattern = r'Q:\s*(.+?)\s*A:\s*(.+?)(?=Q:|$)'
        matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)

        for question, answer in matches:
            pairs.append((question.strip(), answer.strip()))

        # Pattern: Question: ... Answer: ...
        pattern = r'Question:\s*(.+?)\s*Answer:\s*(.+?)(?=Question:|$)'
        matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)

        for question, answer in matches:
            pairs.append((question.strip(), answer.strip()))

        return pairs


class WorkflowChunker(BaseChunker):
    """Chunk by workflow steps."""

    def chunk(self, document: ExtractedDocument) -> List[Chunk]:
        chunks = []
        steps = self._extract_steps(document.raw_text)

        for i, step in enumerate(steps):
            # Include previous step for context
            context = ""
            if i > 0:
                context = f"Previous: {steps[i-1][:100]}...\n\n"

            content = context + step
            chunks.append(Chunk(
                content=content,
                chunk_index=i,
                start_char=0,
                end_char=len(content),
                token_count=self.count_tokens(content),
                metadata={"step_number": i + 1}
            ))

        return chunks

    def _extract_steps(self, text: str) -> List[str]:
        """Extract steps from workflow text."""
        import re
        steps = []

        # Pattern: Step N: ...
        pattern = r'Step\s+\d+[:.]\s*(.+?)(?=Step\s+\d+|$)'
        matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
        steps.extend([m.strip() for m in matches])

        # Pattern: 1. ... 2. ...
        if not steps:
            pattern = r'^\s*(\d+)\.\s+(.+?)(?=^\s*\d+\.|$)'
            matches = re.findall(pattern, text, re.MULTILINE | re.DOTALL)
            steps.extend([f"Step {num}: {content.strip()}" for num, content in matches])

        return steps


class TableChunker(BaseChunker):
    """Chunk tables row by row with header context."""

    def chunk(self, document: ExtractedDocument) -> List[Chunk]:
        chunks = []
        chunk_index = 0

        for table in document.tables:
            header_text = " | ".join(table.headers)

            for row in table.rows:
                row_text = " | ".join(row)
                content = f"Table: {table.caption or 'Data'}\n"
                content += f"Headers: {header_text}\n"
                content += f"Row: {row_text}"

                chunks.append(Chunk(
                    content=content,
                    chunk_index=chunk_index,
                    start_char=0,
                    end_char=len(content),
                    token_count=self.count_tokens(content)
                ))
                chunk_index += 1

        return chunks


class ChunkingPipeline:
    """Select and apply appropriate chunking strategy."""

    def __init__(self, max_tokens: int = 500, overlap_tokens: int = 50):
        self.semantic_chunker = SemanticChunker(max_tokens, overlap_tokens)
        self.faq_chunker = FAQChunker(max_tokens, overlap_tokens)
        self.workflow_chunker = WorkflowChunker(max_tokens, overlap_tokens)
        self.table_chunker = TableChunker(max_tokens, overlap_tokens)

    def chunk(self, document: ExtractedDocument, knowledge_type: KnowledgeType) -> List[Chunk]:
        """Chunk document based on its type."""
        chunks = []

        # Main content chunking
        if knowledge_type == KnowledgeType.FAQ:
            chunks.extend(self.faq_chunker.chunk(document))
        elif knowledge_type == KnowledgeType.WORKFLOW:
            chunks.extend(self.workflow_chunker.chunk(document))
        else:
            chunks.extend(self.semantic_chunker.chunk(document))

        # Table chunking (for all types)
        if document.tables:
            table_chunks = self.table_chunker.chunk(document)
            # Offset indices
            max_index = max(c.chunk_index for c in chunks) if chunks else -1
            for tc in table_chunks:
                tc.chunk_index = max_index + 1 + tc.chunk_index
            chunks.extend(table_chunks)

        return chunks
```

---

## Stage 4: Enrichment

### Entity Extraction

```python
from typing import List, Dict
import spacy


class EntityExtractor:
    """Extract named entities from text."""

    def __init__(self):
        self.nlp = spacy.load("en_core_web_sm")
        # Add custom patterns for domain entities
        self.custom_patterns = []

    def extract(self, text: str) -> List[Dict]:
        """Extract entities from text."""
        doc = self.nlp(text)

        entities = []
        for ent in doc.ents:
            entities.append({
                "text": ent.text,
                "type": ent.label_,
                "start": ent.start_char,
                "end": ent.end_char
            })

        # Custom entity extraction (products, features)
        entities.extend(self._extract_custom_entities(text))

        return entities

    def _extract_custom_entities(self, text: str) -> List[Dict]:
        """Extract domain-specific entities."""
        entities = []

        # Add product names, feature names, etc.
        # This should be customized per company

        return entities
```

### Summary Generation

```python
from typing import Optional


class SummaryGenerator:
    """Generate summaries using LLM."""

    def __init__(self, llm_client):
        self.llm = llm_client

    def generate(self, content: str, max_length: int = 200) -> str:
        """Generate a summary of the content."""
        prompt = f"""
Summarize the following content in {max_length} words or less.
Focus on the key information that would help someone decide if this content
answers their question.

Content:
{content[:3000]}  # Limit input length

Summary:"""

        response = self.llm.generate(prompt, max_tokens=max_length)
        return response.strip()


class QAGenerator:
    """Generate Q&A pairs from documents."""

    def __init__(self, llm_client):
        self.llm = llm_client

    def generate(self, content: str, num_pairs: int = 5) -> List[Tuple[str, str]]:
        """Generate Q&A pairs from content."""
        prompt = f"""
Based on the following content, generate {num_pairs} question-answer pairs.
Questions should be natural queries a user might ask.
Answers should be concise and directly from the content.

Content:
{content[:3000]}

Format your response as:
Q1: [question]
A1: [answer]

Q2: [question]
A2: [answer]
...
"""

        response = self.llm.generate(prompt, max_tokens=1000)
        return self._parse_qa_pairs(response)

    def _parse_qa_pairs(self, response: str) -> List[Tuple[str, str]]:
        """Parse Q&A pairs from LLM response."""
        import re
        pairs = []

        pattern = r'Q\d+:\s*(.+?)\s*A\d+:\s*(.+?)(?=Q\d+:|$)'
        matches = re.findall(pattern, response, re.DOTALL)

        for question, answer in matches:
            pairs.append((question.strip(), answer.strip()))

        return pairs
```

---

## Stage 5: Embedding

### Embedding Generator

```python
from sentence_transformers import SentenceTransformer
from typing import List, Optional
import numpy as np


class EmbeddingGenerator:
    """Generate embeddings for text."""

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        fine_tuned_path: Optional[str] = None
    ):
        if fine_tuned_path:
            self.model = SentenceTransformer(fine_tuned_path)
        else:
            self.model = SentenceTransformer(model_name)

        self.model_name = model_name
        self.dimension = self.model.get_sentence_embedding_dimension()

    def embed(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """Generate embeddings for a list of texts."""
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=True,
            convert_to_numpy=True
        )
        return embeddings

    def embed_single(self, text: str) -> np.ndarray:
        """Generate embedding for a single text."""
        return self.model.encode(text, convert_to_numpy=True)
```

---

## Stage 6: Indexing

### Vector Store Integration

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import numpy as np


class VectorStore(ABC):
    """Abstract vector store interface."""

    @abstractmethod
    def add(self, ids: List[str], embeddings: np.ndarray, metadata: List[Dict]):
        pass

    @abstractmethod
    def search(self, query_embedding: np.ndarray, top_k: int = 10) -> List[Dict]:
        pass

    @abstractmethod
    def delete(self, ids: List[str]):
        pass


class ChromaDBStore(VectorStore):
    """ChromaDB implementation for local development."""

    def __init__(self, collection_name: str, persist_directory: str = "./chroma_db"):
        import chromadb

        self.client = chromadb.PersistentClient(path=persist_directory)
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )

    def add(self, ids: List[str], embeddings: np.ndarray, metadata: List[Dict]):
        self.collection.add(
            ids=ids,
            embeddings=embeddings.tolist(),
            metadatas=metadata
        )

    def search(self, query_embedding: np.ndarray, top_k: int = 10, filters: Dict = None) -> List[Dict]:
        results = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=top_k,
            where=filters
        )

        return [
            {
                "id": id,
                "score": 1 - distance,  # Convert distance to similarity
                "metadata": meta
            }
            for id, distance, meta in zip(
                results["ids"][0],
                results["distances"][0],
                results["metadatas"][0]
            )
        ]

    def delete(self, ids: List[str]):
        self.collection.delete(ids=ids)


class PineconeStore(VectorStore):
    """Pinecone implementation for production."""

    def __init__(self, index_name: str, api_key: str, environment: str):
        import pinecone

        pinecone.init(api_key=api_key, environment=environment)
        self.index = pinecone.Index(index_name)

    def add(self, ids: List[str], embeddings: np.ndarray, metadata: List[Dict]):
        vectors = [
            (id, emb.tolist(), meta)
            for id, emb, meta in zip(ids, embeddings, metadata)
        ]
        self.index.upsert(vectors=vectors)

    def search(self, query_embedding: np.ndarray, top_k: int = 10, filters: Dict = None) -> List[Dict]:
        results = self.index.query(
            vector=query_embedding.tolist(),
            top_k=top_k,
            include_metadata=True,
            filter=filters
        )

        return [
            {
                "id": match.id,
                "score": match.score,
                "metadata": match.metadata
            }
            for match in results.matches
        ]

    def delete(self, ids: List[str]):
        self.index.delete(ids=ids)
```

---

## Pipeline Orchestration

```python
from dataclasses import dataclass
from typing import List, Optional
import uuid
from pathlib import Path


@dataclass
class IngestionResult:
    """Result of ingesting a document."""
    knowledge_item_id: str
    chunk_count: int
    entity_count: int
    qa_pairs_generated: int
    errors: List[str]


class IngestionPipeline:
    """Orchestrate the full ingestion pipeline."""

    def __init__(
        self,
        db_connection,
        vector_store: VectorStore,
        embedding_generator: EmbeddingGenerator,
        llm_client,
        bm25_index
    ):
        self.db = db_connection
        self.vector_store = vector_store
        self.embedder = embedding_generator
        self.llm = llm_client
        self.bm25 = bm25_index

        # Initialize components
        self.parsers = {
            '.pdf': PDFParser(),
            '.md': MarkdownParser(),
            '.docx': DOCXParser(),
            '.html': HTMLParser()
        }
        self.classifier = DocumentClassifier()
        self.chunking_pipeline = ChunkingPipeline()
        self.entity_extractor = EntityExtractor()
        self.summary_generator = SummaryGenerator(llm_client)
        self.qa_generator = QAGenerator(llm_client)

    def ingest(self, file_path: str) -> IngestionResult:
        """Ingest a single document."""
        errors = []

        # 1. Parse
        ext = Path(file_path).suffix.lower()
        parser = self.parsers.get(ext)
        if not parser:
            raise ValueError(f"Unsupported file type: {ext}")

        document = parser.parse(file_path)

        # 2. Classify
        knowledge_type, category, audience = self.classifier.classify(document)

        # 3. Create knowledge item in DB
        knowledge_item_id = str(uuid.uuid4())
        self.db.execute("""
            INSERT INTO knowledge_items (id, type, category, title, content, source_file, audience)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            knowledge_item_id,
            knowledge_type.value,
            category.value,
            document.title,
            document.content,
            file_path,
            [audience.value]
        ))

        # 4. Chunk
        chunks = self.chunking_pipeline.chunk(document, knowledge_type)

        # 5. Generate embeddings
        chunk_texts = [c.content for c in chunks]
        embeddings = self.embedder.embed(chunk_texts)

        # 6. Store chunks and embeddings
        chunk_ids = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_id = str(uuid.uuid4())
            chunk_ids.append(chunk_id)

            # Store chunk in DB
            self.db.execute("""
                INSERT INTO chunks (id, knowledge_item_id, content, chunk_index, section_title, token_count)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (chunk_id, knowledge_item_id, chunk.content, i, chunk.section_title, chunk.token_count))

            # Store embedding in DB
            self.db.execute("""
                INSERT INTO embeddings (id, chunk_id, model_name, model_version, embedding)
                VALUES (%s, %s, %s, %s, %s)
            """, (str(uuid.uuid4()), chunk_id, self.embedder.model_name, "1.0", embedding.tolist()))

        # 7. Index in vector store
        metadata = [
            {
                "knowledge_item_id": knowledge_item_id,
                "chunk_index": c.chunk_index,
                "section_title": c.section_title or "",
                "type": knowledge_type.value,
                "category": category.value
            }
            for c in chunks
        ]
        self.vector_store.add(chunk_ids, embeddings, metadata)

        # 8. Index in BM25
        for chunk_id, chunk in zip(chunk_ids, chunks):
            self.bm25.add_document(chunk_id, chunk.content)

        # 9. Extract entities
        entities = self.entity_extractor.extract(document.content)
        for entity in entities:
            self.db.execute("""
                INSERT INTO entities (id, knowledge_item_id, entity_type, entity_value)
                VALUES (%s, %s, %s, %s)
            """, (str(uuid.uuid4()), knowledge_item_id, entity["type"], entity["text"]))

        # 10. Generate Q&A pairs (for non-FAQ documents)
        qa_count = 0
        if knowledge_type != KnowledgeType.FAQ:
            try:
                qa_pairs = self.qa_generator.generate(document.content)
                for question, answer in qa_pairs:
                    # Store as separate FAQ knowledge item
                    qa_id = str(uuid.uuid4())
                    self.db.execute("""
                        INSERT INTO knowledge_items (id, type, category, title, question, answer, source_file)
                        VALUES (%s, 'faq', %s, %s, %s, %s, %s)
                    """, (qa_id, category.value, question, question, answer, file_path))
                    qa_count += 1
            except Exception as e:
                errors.append(f"Q&A generation failed: {str(e)}")

        # 11. Generate summary
        try:
            summary = self.summary_generator.generate(document.content)
            self.db.execute("""
                UPDATE knowledge_items SET summary = %s WHERE id = %s
            """, (summary, knowledge_item_id))
        except Exception as e:
            errors.append(f"Summary generation failed: {str(e)}")

        self.db.commit()

        return IngestionResult(
            knowledge_item_id=knowledge_item_id,
            chunk_count=len(chunks),
            entity_count=len(entities),
            qa_pairs_generated=qa_count,
            errors=errors
        )

    def ingest_directory(self, directory: str) -> List[IngestionResult]:
        """Ingest all supported files in a directory."""
        results = []
        path = Path(directory)

        for file_path in path.rglob("*"):
            if file_path.suffix.lower() in self.parsers:
                try:
                    result = self.ingest(str(file_path))
                    results.append(result)
                    print(f"Ingested: {file_path} ({result.chunk_count} chunks)")
                except Exception as e:
                    print(f"Failed to ingest {file_path}: {str(e)}")

        return results
```

---

## Configuration

```python
# config/ingestion.yaml

ingestion:
  # Chunking settings
  chunking:
    max_tokens: 500
    overlap_tokens: 50

  # Embedding settings
  embedding:
    model_name: "all-MiniLM-L6-v2"
    batch_size: 32
    fine_tuned_path: null  # Set to path after fine-tuning

  # Enrichment settings
  enrichment:
    generate_summaries: true
    generate_qa_pairs: true
    max_qa_pairs_per_doc: 5
    extract_entities: true

  # Vector store
  vector_store:
    type: "chromadb"  # or "pinecone"
    collection_name: "knowledge_base"
    persist_directory: "./data/chroma_db"

  # For Pinecone (production)
  pinecone:
    api_key: "${PINECONE_API_KEY}"
    environment: "us-east-1"
    index_name: "company-knowledge"

  # Supported file types
  supported_extensions:
    - ".pdf"
    - ".md"
    - ".docx"
    - ".html"
    - ".htm"
```

---

## Usage Example

```python
# scripts/ingest_documents.py

from src.ingestion.pipeline import IngestionPipeline
from src.vectorstore.chromadb import ChromaDBStore
from src.embeddings.sentence_transformer import EmbeddingGenerator
from src.db.connection import get_db_connection
import argparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", required=True, help="Directory to ingest")
    parser.add_argument("--config", default="config/ingestion.yaml")
    args = parser.parse_args()

    # Initialize components
    db = get_db_connection()
    vector_store = ChromaDBStore("knowledge_base")
    embedder = EmbeddingGenerator()
    llm_client = get_llm_client()  # Your LLM client
    bm25_index = get_bm25_index()  # Your BM25 index

    # Create pipeline
    pipeline = IngestionPipeline(
        db_connection=db,
        vector_store=vector_store,
        embedding_generator=embedder,
        llm_client=llm_client,
        bm25_index=bm25_index
    )

    # Ingest documents
    results = pipeline.ingest_directory(args.directory)

    # Summary
    total_chunks = sum(r.chunk_count for r in results)
    total_qa = sum(r.qa_pairs_generated for r in results)

    print(f"\nIngestion Complete:")
    print(f"  Documents: {len(results)}")
    print(f"  Chunks: {total_chunks}")
    print(f"  Q&A Pairs Generated: {total_qa}")


if __name__ == "__main__":
    main()
```
