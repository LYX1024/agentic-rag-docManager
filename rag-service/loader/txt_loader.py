"""Plain text loader for .txt, .md, .csv, .json, .py and other text files."""
import re
from langchain_core.documents import Document
from loguru import logger


def _extract_md_headings(content: str) -> dict:
    """Parse Markdown headings to extract title and hierarchy."""
    headings = []
    for line in content.split('\n'):
        stripped = line.strip()
        if stripped.startswith('# ') and not stripped.startswith('## '):
            headings.append(('h1', stripped[2:]))
        elif stripped.startswith('## ') and not stripped.startswith('### '):
            headings.append(('h2', stripped[3:]))
        elif stripped.startswith('### '):
            headings.append(('h3', stripped[4:]))

    if not headings:
        return {}

    meta = {}
    first = headings[0]
    meta["title"] = first[1]
    meta["heading"] = first[1]

    rest = [h[1] for h in headings[1:]]
    if rest:
        meta["hierarchy"] = rest

    return meta


def txt_loader(file_path: str) -> list[Document]:
    """Load a plain text file. For Markdown files, extracts heading metadata.

    Used as the default fallback loader for any unrecognized file extension.
    Handles .txt, .md, .csv, .json, .py, and similar text-based formats.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        if not content.strip():
            logger.warning(f"Text file {file_path} is empty.")
            return []

        metadata = {"source": file_path}

        # Extract Markdown headings if this is a .md file
        if file_path.lower().endswith('.md'):
            heading_meta = _extract_md_headings(content)
            if heading_meta:
                metadata.update(heading_meta)
                logger.debug(f"MD headings extracted: {list(heading_meta.keys())}")

        document = Document(page_content=content, metadata=metadata)
        logger.info(f"Text loaded: {file_path} -> {len(content)} chars")
        return [document]

    except UnicodeDecodeError:
        for encoding in ["gbk", "gb2312", "latin-1"]:
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    content = f.read()
                metadata = {"source": file_path}
                if file_path.lower().endswith('.md'):
                    heading_meta = _extract_md_headings(content)
                    if heading_meta:
                        metadata.update(heading_meta)
                logger.info(f"Text loaded with {encoding}: {file_path} -> {len(content)} chars")
                return [Document(page_content=content, metadata=metadata)]
            except UnicodeDecodeError:
                continue

        logger.error(f"Failed to decode text file {file_path} with any encoding.")
        raise ValueError(f"Cannot decode file: {file_path}")

    except Exception as e:
        logger.error(f"Failed to load text file {file_path}: {e}")
        raise
