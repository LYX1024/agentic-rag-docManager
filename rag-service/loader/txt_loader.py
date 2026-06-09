"""Text loader for .txt, .md, .csv, and other plain text files."""
from langchain_core.documents import Document
from loguru import logger


def txt_loader(file_path: str) -> list[Document]:
    """Load a text file. For Markdown, splits into sections by headings.

    Used as the default fallback loader. Handles .txt, .md, .csv, .json, .py.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        if not content.strip():
            logger.warning(f"Text file {file_path} is empty.")
            return []
    except UnicodeDecodeError:
        for encoding in ["gbk", "gb2312", "latin-1"]:
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    content = f.read()
                break
            except UnicodeDecodeError:
                continue
        else:
            logger.error(f"Failed to decode text file {file_path}")
            raise ValueError(f"Cannot decode file: {file_path}")

    # Markdown: split by headings, each section gets correct hierarchy chain
    if file_path.lower().endswith('.md'):
        from loader.heading_utils import split_markdown_by_headings
        sections = split_markdown_by_headings(content)
        docs = []
        for sec in sections:
            if not sec["text"]:
                continue
            docs.append(Document(page_content=sec["text"], metadata={
                "source": file_path,
                "title": sec["title"],
                "hierarchy": sec["hierarchy"],
                "heading": sec["heading"],
            }))
        logger.info(f"MD loaded: {file_path} -> {len(docs)} sections")
        return docs if docs else [Document(page_content=content, metadata={"source": file_path})]

    # Other text: single Document
    document = Document(page_content=content, metadata={"source": file_path})
    logger.info(f"Text loaded: {file_path} -> {len(content)} chars")
    return [document]
