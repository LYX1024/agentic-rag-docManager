"""Chat history with sliding window + summary compression."""
from datetime import datetime
from loguru import logger

WINDOW_SIZE = 8       # 滑动窗口：最近 N 轮完整保留
SUMMARIZE_AT = 14     # 总轮数超过此时触发摘要压缩


class ChatHistoryManager:
    """Manage per-session chat history with sliding window and LLM summarization.

    Algorithm:
    - Recent WINDOW_SIZE turns are kept in full
    - When total turns exceed SUMMARIZE_AT, all older turns are compressed
      into a single system-level summary message via an LLM call
    - The summary is cached — further growth doesn't re-summarize the same turns
    """

    def __init__(self, llm_api_base: str, llm_api_key: str, llm_model: str):
        self._sessions: dict[str, list[dict]] = {}
        self._summaries: dict[str, str] = {}  # session_id -> summary text
        self._summarized_up_to: dict[str, int] = {}  # session_id -> last summarized turn index
        self._llm_base = llm_api_base
        self._llm_key = llm_api_key
        self._llm_model = llm_model

    def add_turn(self, session_id: str, user_msg: str, assistant_msg: str,
                 sources: list | None = None):
        """Add a conversation turn (user + assistant pair)."""
        if session_id not in self._sessions:
            self._sessions[session_id] = []
            self._summaries[session_id] = ""
            self._summarized_up_to[session_id] = 0

        now = datetime.now().isoformat()
        self._sessions[session_id].append({
            "id": f"turn_{len(self._sessions[session_id])}",
            "role": "user",
            "content": user_msg,
            "sources": [],
            "created_at": now,
        })
        self._sessions[session_id].append({
            "id": f"turn_{len(self._sessions[session_id])}",
            "role": "assistant",
            "content": assistant_msg,
            "sources": sources or [],
            "created_at": now,
        })

    async def maybe_summarize(self, session_id: str):
        """Check if summary is needed and run it asynchronously."""
        turns = self._sessions[session_id]
        if len(turns) < SUMMARIZE_AT * 2:  # each turn = 2 messages (user+assistant)
            return

        # Only summarize turns older than the window, and not already summarized
        last_idx = self._summarized_up_to[session_id]
        window_start = len(turns) - WINDOW_SIZE * 2
        if window_start <= last_idx:
            return

        # Collect turns between last_idx and window_start for summarization
        turns_to_summarize = turns[last_idx:window_start]
        if not turns_to_summarize:
            return

        logger.info(f"Summarizing {len(turns_to_summarize)} messages for session {session_id}")
        summary = await self._call_llm_summarize(turns_to_summarize)
        if summary:
            self._summaries[session_id] = summary
            self._summarized_up_to[session_id] = window_start
            logger.info(f"Summary complete: {len(summary)} chars")

    def build_messages(self, session_id: str) -> list[dict]:
        """Build the LLM message list with summary + recent window."""
        turns = self._sessions.get(session_id, [])
        if not turns:
            return []

        messages = []

        # Prepend summary if exists
        summary = self._summaries.get(session_id, "")
        if summary:
            messages.append({
                "role": "system",
                "content": f"[历史对话摘要]\n{summary}",
            })

        # Sliding window: last WINDOW_SIZE turns
        window_start = max(0, len(turns) - WINDOW_SIZE * 2)
        for msg in turns[window_start:]:
            messages.append({
                "role": msg["role"],
                "content": msg["content"],
            })

        return messages

    def get_raw(self, session_id: str) -> list[dict]:
        """Return raw turns (for API responses), including sources."""
        return self._sessions.get(session_id, [])

    def clear_session(self, session_id: str):
        self._sessions.pop(session_id, None)
        self._summaries.pop(session_id, None)
        self._summarized_up_to.pop(session_id, None)

    # ---- private ----

    async def _call_llm_summarize(self, turns: list[dict]) -> str:
        """Call LLM via functionless chat to summarize conversation history."""
        from openai import AsyncOpenAI

        client = AsyncOpenAI(base_url=self._llm_base, api_key=self._llm_key, timeout=60.0)

        dialogue = "\n".join(
            f"{'用户' if t['role'] == 'user' else '助手'}: {t['content'][:200]}"
            for t in turns
        )
        prompt = (
            "请用一段简洁的中文总结以下对话的核心内容和关键信息，"
            "保留重要的实体、观点和结论。控制在200字以内。\n\n"
            f"{dialogue}"
        )

        try:
            resp = await client.chat.completions.create(
                model=self._llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=300,
            )
            return resp.choices[0].message.content or ""
        except Exception as e:
            logger.warning(f"Summary LLM call failed: {e}")
            return ""
