"""PPTX loader using python-pptx."""
from langchain_core.documents import Document
from loguru import logger


def pptx_loader(file_path: str) -> list[Document]:
    """Load a PPTX/PPT file and extract text + slide title hierarchy.

    Args:
        file_path: Path to the .pptx or .ppt file.

    Returns:
        List containing a single Document with hierarchy metadata.
    """
    try:
        from pptx import Presentation

        prs = Presentation(file_path)

        slides_text = []
        slide_titles = []
        for slide_num, slide in enumerate(prs.slides):
            slide_parts = []

            # Extract slide title for hierarchy metadata
            if slide.shapes.title and slide.shapes.title.text.strip():
                slide_titles.append(slide.shapes.title.text.strip())

            for shape in slide.shapes:
                if shape.has_text_frame:
                    for paragraph in shape.text_frame.paragraphs:
                        text = paragraph.text.strip()
                        if text:
                            slide_parts.append(text)

            slide_content = "\n".join(slide_parts)
            if slide_content:
                slides_text.append(f"[Slide {slide_num + 1}]\n{slide_content}")

        full_text = "\n\n".join(slides_text)
        if not full_text:
            logger.warning(f"PPTX file {file_path} produced no text content.")
            return []

        metadata = {
            "source": file_path,
            "total_slides": len(prs.slides),
        }
        if slide_titles:
            metadata["title"] = slide_titles[0]
            metadata["heading"] = slide_titles[0]
            if len(slide_titles) > 1:
                metadata["hierarchy"] = slide_titles[1:]
            logger.debug(f"PPTX slide titles: {len(slide_titles)} found")

        document = Document(page_content=full_text, metadata=metadata)
        logger.info(f"PPTX loaded: {file_path} -> {len(slides_text)} slides, {len(full_text)} chars")
        return [document]

    except Exception as e:
        logger.error(f"Failed to load PPTX {file_path}: {e}")
        raise
