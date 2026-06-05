"""PDF loader using PyMuPDF (fitz)."""
from langchain.schema import Document
from loguru import logger


def pdf_loader(file_path: str) -> list[Document]:
    """Load a PDF file and return a list of Document objects, one per page.

    Args:
        file_path: Path to the PDF file.

    Returns:
        List of langchain.schema.Document, each with page_content set to the
        extracted text of one page and metadata including page_number.
    """
    import fitz  # PyMuPDF

    documents = []
    try:
        doc = fitz.open(file_path)
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text()

            text = text.strip()
            if len(text) < 50:
                logger.debug(
                    f"PDF page {page_num + 1} has very little text ({len(text)} chars). "
                    f"OCR would be needed for scanned content."
                )

            if text:
                documents.append(
                    Document(
                        page_content=text,
                        metadata={
                            "source": file_path,
                            "page_number": page_num + 1,
                            "total_pages": len(doc),
                        },
                    )
                )

        doc.close()
        logger.info(f"PDF loaded: {file_path} -> {len(documents)} pages")
    except Exception as e:
        logger.error(f"Failed to load PDF {file_path}: {e}")
        raise

    return documents
