"""DOCX loader using python-docx."""
from langchain_core.documents import Document
from loguru import logger


def docx_loader(file_path: str) -> list[Document]:
    """Load a DOCX file and extract text + heading hierarchy metadata.

    Args:
        file_path: Path to the .docx or .doc file.

    Returns:
        List containing a single Document with heading metadata.
    """
    try:
        from docx import Document as DocxDocument

        doc = DocxDocument(file_path)

        paragraphs = []
        headings = []
        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue
            paragraphs.append(text)

            # Detect Word heading styles for title/hierarchy
            style_name = para.style.name if para.style else ""
            if style_name.startswith('Heading'):
                try:
                    level = int(style_name.replace('Heading', '').strip()) if style_name.replace('Heading', '').strip().isdigit() else 1
                except ValueError:
                    level = 1
                headings.append((level, text))

        full_text = "\n".join(paragraphs)
        if not full_text:
            logger.warning(f"DOCX file {file_path} produced no text content.")
            return []

        metadata = {"source": file_path}

        # Set title from first H1, hierarchy from rest
        if headings:
            h1 = [h for h in headings if h[0] == 1]
            if h1:
                metadata["title"] = h1[0][1]
                metadata["heading"] = h1[0][1]
            rest = [h[1] for h in headings if not (h[0] == 1 and h == (h1[0] if h1 else None))]
            if rest:
                metadata["hierarchy"] = rest
            logger.debug(f"DOCX headings: {len(headings)} found")

        document = Document(page_content=full_text, metadata=metadata)
        logger.info(f"DOCX loaded: {file_path} -> {len(paragraphs)} paragraphs, {len(full_text)} chars")
        return [document]

    except Exception as e:
        logger.error(f"Failed to load DOCX {file_path}: {e}")
        raise
