"""Split document content into sections based on heading markers."""


def split_markdown_by_headings(content: str) -> list[dict]:
    """Parse Markdown content into sections, each with correct heading chain.

    Returns list of dicts:
        {"title": str, "hierarchy": [str], "heading": str, "text": str}
    """
    lines = content.split('\n')
    sections = []

    # Build a flat list of (level, heading_text, start_line, end_line)
    heading_stack: list[tuple[int, str]] = []  # (level, text)
    current_section_start = 0
    current_heading = None

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Detect heading level
        level = 0
        heading_text = ""
        if line.startswith('# ') and not line.startswith('## '):
            level = 1
            heading_text = line[2:]
        elif line.startswith('## ') and not line.startswith('### '):
            level = 2
            heading_text = line[3:]
        elif line.startswith('### '):
            level = 3
            heading_text = line[4:]

        if level > 0:
            # Save previous section
            if current_section_start < i:
                body = '\n'.join(lines[current_section_start:i]).strip()
                if body:
                    # Build hierarchy chain for this section
                    title = heading_stack[0][1] if heading_stack else heading_text
                    parent_chain = [h[1] for h in heading_stack[1:]] if len(heading_stack) > 1 else []
                    sections.append({
                        "title": title,
                        "hierarchy": parent_chain,
                        "heading": current_heading or heading_text,
                        "text": body,
                    })

            # Update heading stack
            while heading_stack and heading_stack[-1][0] >= level:
                heading_stack.pop()
            heading_stack.append((level, heading_text))
            current_heading = heading_text
            current_section_start = i + 1

        i += 1

    # Save last section
    if current_section_start < len(lines):
        body = '\n'.join(lines[current_section_start:]).strip()
        if body:
            title = heading_stack[0][1] if heading_stack else ""
            parent_chain = [h[1] for h in heading_stack[1:]] if len(heading_stack) > 1 else []
            sections.append({
                "title": title,
                "hierarchy": parent_chain,
                "heading": current_heading or (heading_stack[-1][1] if heading_stack else ""),
                "text": body,
            })

    # If no headings found, return entire document as one section
    if not sections:
        sections.append({"title": "", "hierarchy": [], "heading": "", "text": content.strip()})

    return sections


def split_docx_by_headings(paragraphs: list[tuple[int, str]]) -> list[dict]:
    """Split DOCX paragraphs into sections based on Heading styles.

    Args:
        paragraphs: List of (level, text) tuples where level 1-3 is a heading,
                    level 0 is body text.

    Returns list of dicts with same format as split_markdown_by_headings.
    """
    sections = []
    heading_stack: list[tuple[int, str]] = []
    current_text: list[str] = []
    current_heading = ""

    for level, text in paragraphs:
        if level > 0:
            # Save previous section
            body = '\n'.join(current_text).strip()
            if body:
                title = heading_stack[0][1] if heading_stack else text
                parent_chain = [h[1] for h in heading_stack[1:]] if len(heading_stack) > 1 else []
                sections.append({
                    "title": title,
                    "hierarchy": parent_chain,
                    "heading": current_heading or text,
                    "text": body,
                })

            # Update heading stack
            while heading_stack and heading_stack[-1][0] >= level:
                heading_stack.pop()
            heading_stack.append((level, text))
            current_heading = text
            current_text = []
        else:
            current_text.append(text)

    # Save last section
    body = '\n'.join(current_text).strip()
    if body:
        title = heading_stack[0][1] if heading_stack else ""
        parent_chain = [h[1] for h in heading_stack[1:]] if len(heading_stack) > 1 else []
        sections.append({
            "title": title,
            "hierarchy": parent_chain,
            "heading": current_heading,
            "text": body,
        })

    if not sections:
        sections.append({"title": "", "hierarchy": [], "heading": "", "text": '\n'.join(t for _, t in paragraphs).strip()})

    return sections
