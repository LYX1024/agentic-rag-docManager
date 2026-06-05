"""PPTX loader using python-pptx."""
from langchain.schema import Document
from loguru import logger


def pptx_loader(file_path: str) -> list[Document]:
    """Load a PPTX/PPT file and extract text from all slides.

    Args:
        file_path: Path to the .pptx or .ppt file.

    Returns:
        List containing a single langchain.schema.Document with all slide text.
    """
    try:
        from pptx import Presentation

        prs = Presentation(file_path)

        slides_text = []
        for slide_num, slide in enumerate(prs.slides):
            slide_parts = []
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

        document = Document(
            page_content=full_text,
            metadata={
                "source": file_path,
                "total_slides": len(prs.slides),
            },
        )

        logger.info(f"PPTX loaded: {file_path} -> {len(slides_text)} slides, {len(full_text)} chars")
        return [document]

    except Exception as e:
        logger.error(f"Failed to load PPTX {file_path}: {e}")
        raise
