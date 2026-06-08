"""RAG prompt templates and builders."""

RAG_SYSTEM_PROMPT = (
    "你是一个知识库助手。请基于以下参考资料回答用户的问题。"
    "如果参考资料中没有相关信息，请如实告知。\n\n"
    "参考资料：\n"
    "{context}"
)


def build_rag_prompt(query: str, context_text: str) -> str:
    """Build the user prompt with retrieved context."""
    return RAG_SYSTEM_PROMPT.format(context=context_text)
