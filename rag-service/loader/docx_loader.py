"""DOCX loader using python-docx."""
from langchain_core.documents import Document
from loguru import logger


def docx_loader(file_path: str) -> list[Document]:
    """Load a DOCX file and return a single Document with all paragraph text.

    Args:
        file_path: Path to the .docx or .doc file.

    Returns:
        List containing a single langchain.schema.Document.
    """
    try:
        from docx import Document as DocxDocument

        doc = DocxDocument(file_path)

        paragraphs = []
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                paragraphs.append(text)

        full_text = "\n".join(paragraphs)

        if not full_text:
            logger.warning(f"DOCX file {file_path} produced no text content.")
            return []

        document = Document(
            page_content=full_text,
            metadata={"source": file_path},
        )

        logger.info(f"DOCX loaded: {file_path} -> {len(paragraphs)} paragraphs, {len(full_text)} chars")
        return [document]

    except Exception as e:
        logger.error(f"Failed to load DOCX {file_path}: {e}")
        raise
