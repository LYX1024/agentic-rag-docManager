"""ChineseRecursiveTextSplitter with Chinese-optimized separators."""
from typing import Optional
from langchain_text_splitters import RecursiveCharacterTextSplitter
from loguru import logger


class ChineseRecursiveTextSplitter(RecursiveCharacterTextSplitter):
    """Recursive text splitter with separators optimized for Chinese text.

    Default separators include Chinese punctuation marks for more natural
    chunk boundaries, descending from coarse (paragraph) to fine (character).
    """

    def __init__(
        self,
        chunk_size: int = 250,
        chunk_overlap: int = 50,
        separators: Optional[list[str]] = None,
        keep_separator: bool = True,
        is_separator_regex: bool = False,
    ):
        """Initialize the Chinese recursive text splitter.

        Args:
            chunk_size: Maximum chunk size in characters.
            chunk_overlap: Overlap between chunks in characters.
            separators: Custom separators. Defaults to the Chinese-optimized list.
            keep_separator: Keep separator in the chunk content.
            is_separator_regex: Whether separators are regex patterns.
        """
        if separators is None:
            separators = [
                "\n\n",
                "\n",
                "。",  # 。Chinese period
                "！",  # ！Chinese exclamation
                "？",  # ？Chinese question mark
                "，",  # ，Chinese comma
                " ",
                "",
            ]

        super().__init__(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=separators,
            keep_separator=keep_separator,
            is_separator_regex=is_separator_regex,
        )
        logger.debug(
            f"ChineseRecursiveTextSplitter initialized: "
            f"chunk_size={chunk_size}, chunk_overlap={chunk_overlap}"
        )
