"""Title enhancement: prepend hierarchical context to chunk text.

When documents pass through a loader/splitter pipeline with hierarchical
metadata (e.g., document title -> section heading -> subsection), each
chunk gets prepended with its full path for better standalone context.

Adapted from LangChain-Chatchat.
"""
from langchain_core.documents import Document
from loguru import logger


def zh_title_enhance(docs: list[Document]) -> list[Document]:
    """Enhance each Document chunk by prepending its title hierarchy.

    If a Document's metadata contains "title" or "hierarchy" keys, the
    corresponding values are prepended to the page_content so that each
    chunk carries its context when used for retrieval / Q&A.

    Args:
        docs: List of Document objects, possibly with title/hierarchy metadata.

    Returns:
        The same list of Documents with enhanced page_content. Documents
        without title/hierarchy metadata are returned unchanged.
    """
    if not docs:
        return docs

    enhanced_count = 0
    for doc in docs:
        hierarchy_parts = []
        metadata = doc.metadata or {}

        # Check for title metadata key
        title = metadata.get("title")
        if title:
            hierarchy_parts.append(str(title))

        # Check for hierarchy metadata (list of titles from parent sections)
        hierarchy = metadata.get("hierarchy")
        if hierarchy:
            if isinstance(hierarchy, list):
                hierarchy_parts.extend(str(h) for h in hierarchy if h)
            elif isinstance(hierarchy, str):
                hierarchy_parts.append(hierarchy)

        # Check for section or heading metadata
        section = metadata.get("section") or metadata.get("heading")
        if section:
            hierarchy_parts.append(str(section))

        if hierarchy_parts:
            prefix = " > ".join(hierarchy_parts)
            # Only prepend if not already present
            if not doc.page_content.startswith(prefix):
                doc.page_content = f"[{prefix}] {doc.page_content}"
                enhanced_count += 1

    if enhanced_count:
        logger.debug(f"zh_title_enhance: enhanced {enhanced_count}/{len(docs)} chunks")

    return docs
