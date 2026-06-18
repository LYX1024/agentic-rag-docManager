"""Loader dictionary mapping file extensions to loader functions."""

from .pdf_loader import pdf_loader
from .docx_loader import docx_loader
from .pptx_loader import pptx_loader
from .image_loader import image_loader
from .txt_loader import txt_loader

LOADER_DICT: dict = {
    ".pdf": pdf_loader,
    ".docx": docx_loader,
    ".doc": docx_loader,
    ".pptx": pptx_loader,
    ".ppt": pptx_loader,
    ".png": image_loader,
    ".jpg": image_loader,
    ".jpeg": image_loader,
    ".bmp": image_loader,
    ".md": txt_loader,
    ".txt": txt_loader,
    ".csv": txt_loader,
    ".json": txt_loader,
    ".py": txt_loader,
}


def get_loader(file_ext: str):
    """Get the loader function for a given file extension. Returns None if unsupported."""
    return LOADER_DICT.get(file_ext.lower())
