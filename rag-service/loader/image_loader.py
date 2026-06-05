"""Image OCR loader using RapidOCR via rapidocr_onnxruntime."""
from langchain.schema import Document
from loguru import logger


def image_loader(file_path: str) -> list[Document]:
    """Load an image file and extract text via RapidOCR.

    Args:
        file_path: Path to the image file (.png, .jpg, .jpeg, .bmp).

    Returns:
        List containing a single langchain.schema.Document with OCR-extracted text.
        Returns an empty string page_content if OCR fails.
    """
    try:
        from rapidocr_onnxruntime import RapidOCR

        ocr = RapidOCR()
        result, elapse = ocr(file_path)

        if not result:
            logger.warning(f"RapidOCR returned no text for image: {file_path}")
            return [Document(page_content="", metadata={"source": file_path})]

        # result is a list of [bbox, text, confidence] for each detected text region
        texts = []
        for item in result:
            # item format: [[x1,y1,x2,y2], "text", confidence]
            if len(item) >= 2 and item[1]:
                texts.append(item[1])

        full_text = "\n".join(texts)

        logger.info(f"Image OCR loaded: {file_path} -> {len(texts)} text regions, "
                     f"{len(full_text)} chars, elapsed={elapse:.2f}s")

        return [Document(page_content=full_text, metadata={"source": file_path})]

    except ImportError as e:
        logger.error(f"RapidOCR not available for {file_path}: {e}")
        return [Document(page_content="", metadata={"source": file_path})]

    except Exception as e:
        logger.error(f"OCR failed for image {file_path}: {e}")
        return [Document(page_content="", metadata={"source": file_path})]
