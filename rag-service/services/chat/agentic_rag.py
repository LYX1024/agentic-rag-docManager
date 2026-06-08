"""
Agentic RAG: ReAct 范式，search + rewrite 双工具 function calling。
LLM 自主决定：直接搜索 / 重写查询后多路搜索 / 最终回答。
Max rounds: 5 (每轮可调用一个工具).
"""
import asyncio
import re
from loguru import logger

from services.chat.llm_client import LLMClient
from services.chat.context_builder import build_context_and_sources

MAX_ROUNDS = 5

_REACT_PROMPT = """你是一个研究助手。用提问者语言简短回答。

工具：
- search("查询") — 搜索知识库
- rewrite("模糊问题") — 将模糊问题拆成多个精确查询，仅当原始搜索效果不好时使用

格式（每次只执行一个 Action）：
Thought: <推理>
Action: search("查询")  或  Action: rewrite("问题")  或  Final Answer: <答案>

规则：
- 先尝试直接搜索，检索结果不好时才用 rewrite 拆解
- 不要所有问题都用 rewrite，多数问题直接搜索即可
- 信息充分后给出 Final Answer"""


def _parse_action(text: str) -> tuple[str | None, str | None, str | None]:
    """Returns (action_type, action_arg, final_answer). Exactly one non-None."""
    # Final Answer
    m = re.search(r'Final\s*Answer\s*[:：]\s*(.*)', text, re.DOTALL | re.IGNORECASE)
    if m:
        return None, None, m.group(1).strip()
    # rewrite("...")
    m = re.search(r'rewrite\s*\(\s*["\'](.+?)["\']\s*\)', text, re.DOTALL | re.IGNORECASE)
    if m:
        return "rewrite", m.group(1).strip(), None
    # search("...")
    m = re.search(r'search\s*\(\s*["\'](.+?)["\']\s*\)', text, re.DOTALL | re.IGNORECASE)
    if m:
        return "search", m.group(1).strip(), None
    return None, None, text.strip()


async def _rewrite_and_search(query: str, retriever, llm_client: LLMClient, llm_model: str):
    """Call LLM to rewrite query into sub-queries, search each, merge results."""
    prompt = (
        f"将以下问题拆解为2-3个更精确的搜索查询，每行一个：\n\n{query}\n\n搜索查询："
    )
    sub_queries_text = ""
    try:
        async for token in llm_client.stream(
                model=llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3):
            sub_queries_text += token
    except Exception as e:
        logger.error(f"Rewrite LLM call failed: {e}")
        return [], build_context_and_sources([])

    # Parse sub-queries (each non-empty line)
    sub_queries = [line.strip().lstrip('-0123456789. ') for line in sub_queries_text.split('\n')
                   if line.strip() and len(line.strip()) > 3]
    sub_queries = sub_queries[:3]

    if not sub_queries:
        # Fallback: search original query
        results = await asyncio.to_thread(
            retriever.retrieve, query=query, top_k=5, score_threshold=0.0)
        return results, build_context_and_sources(results)

    logger.info(f"Rewrite: '{query[:50]}...' → {sub_queries}")

    # Search each sub-query, deduplicate by doc_id
    all_retrieved = []
    seen_ids = set()
    for sq in sub_queries:
        results = await asyncio.to_thread(
            retriever.retrieve, query=sq, top_k=3, score_threshold=0.0)
        for r in results:
            if r["id"] not in seen_ids:
                seen_ids.add(r["id"])
                all_retrieved.append(r)

    all_retrieved.sort(key=lambda r: r.get("score", 0), reverse=True)
    all_retrieved = all_retrieved[:10]
    return all_retrieved, build_context_and_sources(all_retrieved)


async def agentic_rag_stream(
    query: str,
    retriever,
    llm_client: LLMClient,
    llm_model: str,
    temperature: float = 0.7,
):
    """Async generator: yields ('thinking', str) | ('answer', str) | ('sources', list)."""
    all_sources = []
    messages = [
        {"role": "system", "content": _REACT_PROMPT},
        {"role": "user", "content": query},
    ]

    for round_num in range(1, MAX_ROUNDS + 1):
        logger.info(f"ReAct round {round_num}/{MAX_ROUNDS}")

        full_text = ""
        async for token in llm_client.stream(
                model=llm_model, messages=messages, temperature=temperature):
            full_text += token

        action_type, action_arg, answer = _parse_action(full_text)

        if answer:
            logger.info(f"ReAct: answered after {round_num} rounds")
            yield ("sources", all_sources)
            yield ("answer", answer)
            return

        if action_type == "search":
            yield ("thinking", f"Searching: {action_arg}")
            results = await asyncio.to_thread(
                retriever.retrieve, query=action_arg, top_k=5, score_threshold=0.0)
            if results:
                context, sources = build_context_and_sources(results)
                all_sources.extend(sources)
                observation = f"Observation: search '{action_arg}' returned {len(results)} results.\n{context}"
            else:
                observation = f"Observation: search '{action_arg}' returned nothing."
            messages.append({"role": "assistant", "content": full_text})
            messages.append({"role": "user", "content": observation})
            continue

        if action_type == "rewrite":
            yield ("thinking", f"Rewriting: {action_arg}")
            results, (context, sources) = await _rewrite_and_search(
                action_arg, retriever, llm_client, llm_model)
            all_sources.extend(sources)
            if results:
                observation = f"Observation: rewrite+search returned {len(results)} merged results.\n{context}"
            else:
                observation = f"Observation: rewrite+search for '{action_arg}' returned nothing."
            messages.append({"role": "assistant", "content": full_text})
            messages.append({"role": "user", "content": observation})
            continue

        if round_num == MAX_ROUNDS:
            yield ("sources", all_sources)
            yield ("answer", "Sorry, couldn't find enough information.")
            return
        messages.append({"role": "assistant", "content": full_text})
        messages.append({"role": "user", "content": "Please choose: search(), rewrite(), or Final Answer."})

    yield ("sources", all_sources)
    yield ("answer", "Sorry, search didn't return enough information.")
