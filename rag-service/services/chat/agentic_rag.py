"""
Agentic RAG with OpenAI function calling schema.
LLM decides: search / rewrite / answer via native tool_calls.
"""
import json
from loguru import logger

from services.chat.llm_client import LLMClient
from services.chat.context_builder import build_context_and_sources

MAX_ROUNDS = 5

# 工具：搜索和重写搜索请求  由llm自主调用，实现agenticRAG
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search",
            "description": "Search the knowledge base for relevant document chunks. Use this when you need information to answer a question.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query string"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "rewrite",
            "description": "Rewrite a broad question into 2-3 search queries covering different dimensions (categories, types, platforms). Do NOT assume specific product names.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "The original question to decompose"}
                },
                "required": ["question"]
            }
        }
    }
]


async def agentic_rag_stream(
    query: str,
    retriever,
    llm_client: LLMClient,
    llm_model: str,
    temperature: float = 0.7,
    history_messages: list | None = None,
):
    """Async generator: yields ('thinking', str) | ('answer', str) | ('sources', list).

    Uses OpenAI function calling. LLM receives tools: search, rewrite.
    history_messages: previous conversation turns from ChatHistoryManager.
    """
    all_sources = []
    messages = list(history_messages) if history_messages else []
    messages.append({"role": "system", "content": "You are a research assistant. Use the provided tools to search the knowledge base. Answer in the user's language. Be concise."})
    messages.append({"role": "user", "content": query})

    # agent循环最大5轮
    for round_num in range(1, MAX_ROUNDS + 1):
        logger.info(f"Agent round {round_num}/{MAX_ROUNDS}")

        resp = await llm_client.create_with_tools(
            model=llm_model, messages=messages, tools=TOOLS, temperature=temperature)

        choice = resp.choices[0]
        msg = choice.message

        # Final answer (no tool call)
        if not msg.tool_calls and msg.content:
            logger.info(f"Agent answered after {round_num} rounds")
            yield ("sources", all_sources)
            yield ("answer", msg.content)
            return

        # Tool call
        if msg.tool_calls:
            messages.append({"role": "assistant", "tool_calls": [
                {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in msg.tool_calls
            ]})

            for tc in msg.tool_calls:
                name = tc.function.name
                args = json.loads(tc.function.arguments)

                if name == "search":
                    search_query = args["query"]
                    yield ("thinking", f"Searching: {search_query}")
                    results = await retriever.retrieve(
                        query=search_query, top_k=5, score_threshold=0.0)
                    if results:
                        context, sources = build_context_and_sources(results)
                        all_sources.extend(sources)
                        obs = f"'{search_query}' returned {len(results)} results:\n{context}"
                    else:
                        obs = f"'{search_query}' returned nothing."
                    messages.append({"role": "tool", "tool_call_id": tc.id, "content": obs})

                elif name == "rewrite":
                    question = args["question"]
                    yield ("thinking", f"Rewriting: {question}")
                    results, (context, sources) = await _rewrite_and_search(
                        question, retriever, llm_client, llm_model)
                    all_sources.extend(sources)
                    obs = f"Rewrite+search returned {len(results)} results:\n{context}" if results else f"Rewrite+search for '{question}' returned nothing."
                    messages.append({"role": "tool", "tool_call_id": tc.id, "content": obs})

        if round_num == MAX_ROUNDS:
            # Force final answer
            messages.append({"role": "user", "content": "Please provide your final answer based on the information gathered."})
            resp = await llm_client.create_with_tools(
                model=llm_model, messages=messages, tools=[], temperature=temperature)
            final = resp.choices[0].message.content or "Sorry, couldn't find enough information."
            yield ("sources", all_sources)
            yield ("answer", final)
            return

    yield ("sources", all_sources)
    yield ("answer", "Sorry, search didn't return enough information.")


async def _rewrite_and_search(query: str, retriever, llm_client: LLMClient, llm_model: str):
    """LLM decomposes query into sub-queries, search each, merge deduped results."""

    prompt = (
        f"Break this question into 2-3 search queries covering different dimensions "
        f"(e.g. categories, types, technical approaches, platforms). "
        f"Do NOT assume specific product names unless mentioned in the question. "
        f"Output one query per line:\n\n"
        f"Question: {query}\n\n"
        f"Queries:"
    )

    resp = await llm_client.create_with_tools(
        model=llm_model,
        messages=[{"role": "user", "content": prompt}],
        tools=[], temperature=0.3)
    text = resp.choices[0].message.content or ""

    sub_queries = [line.strip().lstrip('-0123456789. ') for line in text.split('\n')
                   if line.strip() and len(line.strip()) > 3]
    sub_queries = sub_queries[:3]
    if not sub_queries:
        results = await retriever.retrieve(query=query, top_k=5, score_threshold=0.0)
        return results, build_context_and_sources(results)

    logger.info(f"Rewrite: '{query[:50]}...' → {sub_queries}")
    all_retrieved, seen = [], set()
    for sq in sub_queries:
        for r in await retriever.retrieve(query=sq, top_k=3, score_threshold=0.0):
            if r["id"] not in seen:
                seen.add(r["id"])
                all_retrieved.append(r)
    all_retrieved.sort(key=lambda r: r.get("score", 0), reverse=True)
    return all_retrieved[:10], build_context_and_sources(all_retrieved[:10])
