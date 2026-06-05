"""Plain text loader for .txt, .md, .csv, .json, .py and other text files."""
from langchain_core.documents import Document
from loguru import logger


def txt_loader(file_path: str) -> list[Document]:
    """Load a plain text file with UTF-8 encoding.

    Used as the default fallback loader for any unrecognized file extension.
    Handles .txt, .md, .csv, .json, .py, and similar text-based formats.

    Args:
        file_path: Path to the text file.

    Returns:
        List containing a single langchain.schema.Document.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        if not content.strip():
            logger.warning(f"Text file {file_path} is empty.")
            return []

        document = Document(
            page_content=content,
            metadata={"source": file_path},
        )

        logger.info(f"Text loaded: {file_path} -> {len(content)} chars")
        return [document]

    except UnicodeDecodeError:
        # Try with other common encodings
        for encoding in ["gbk", "gb2312", "latin-1"]:
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    content = f.read()
                logger.info(f"Text loaded with {encoding}: {file_path} -> {len(content)} chars")
                return [Document(page_content=content, metadata={"source": file_path})]
            except UnicodeDecodeError:
                continue

        logger.error(f"Failed to decode text file {file_path} with any encoding.")
        raise ValueError(f"Cannot decode file: {file_path}")

    except Exception as e:
        logger.error(f"Failed to load text file {file_path}: {e}")
        raise
