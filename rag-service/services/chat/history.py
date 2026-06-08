"""Chat history with sliding window + summary compression."""
import json
from datetime import datetime
from urllib.request import Request, urlopen
from loguru import logger

WINDOW_SIZE = 8       # 滑动窗口：最近 N 轮完整保留
SUMMARIZE_AT = 14     # 总轮数超过此时触发摘要压缩


class ChatHistoryManager:
    """Manage per-session chat history.

    On first access to a session, loads history from Java backend (MySQL).
    Subsequent turns are added in-memory and saved to Java after each exchange.

    Sliding window + LLM summarization for long conversations.
    """

    def __init__(self, java_backend_url: str,
                 llm_api_base: str, llm_api_key: str, llm_model: str):
        self._sessions: dict[str, list[dict]] = {}
        self._summaries: dict[str, str] = {}
        self._summarized_up_to: dict[str, int] = {}
        self._java_url = java_backend_url.rstrip("/")
        self._llm_base = llm_api_base
        self._llm_key = llm_api_key
        self._llm_model = llm_model

    def ensure_loaded(self, session_id: str):
        """Load history from Java if this session hasn't been loaded yet."""
        if session_id not in self._sessions:
            self._sessions[session_id] = []
            self._summaries[session_id] = ""
            self._summarized_up_to[session_id] = 0
            self._load_from_java(session_id)

    def add_turn(self, session_id: str, user_msg: str, assistant_msg: str,
                 sources: list | None = None):
        """Add a conversation turn (user + assistant pair)."""
        self.ensure_loaded(session_id)
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
            self._sync_summary_to_java(session_id, summary, window_start)
            logger.info(f"Summary complete: {len(summary)} chars")

    def build_messages(self, session_id: str) -> list[dict]:
        """Build the LLM message list with summary + recent window."""
        self.ensure_loaded(session_id)
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

    def _load_from_java(self, session_id: str):
        """Fetch chat history from Java REST API and replay into memory."""
        try:
            req = Request(f"{self._java_url}/api/chat/session/{session_id}/history?includeSystem=true")
            resp = urlopen(req, timeout=5)
            data = json.loads(resp.read().decode("utf-8"))
            messages = data.get("data", data) if isinstance(data, dict) else data
            if not isinstance(messages, list):
                return
            for msg in messages:
                role = msg.get("role", "")
                content = msg.get("content", "")
                sources = msg.get("sources")
                if isinstance(sources, str):
                    try:
                        sources = json.loads(sources)
                    except Exception:
                        sources = []

                # Restore summary state from system messages
                if role == "system" and content.startswith("__SUMMARY__:"):
                    try:
                        meta = json.loads(content[len("__SUMMARY__:"):])
                        self._summaries[session_id] = meta.get("text", "")
                        self._summarized_up_to[session_id] = meta.get("up_to", 0)
                        continue  # don't add system summaries as regular turns
                    except Exception:
                        pass

                self._sessions[session_id].append({
                    "id": str(msg.get("id", len(self._sessions[session_id]))),
                    "role": role,
                    "content": content,
                    "sources": sources or [],
                    "created_at": msg.get("createdAt", ""),
                })
            logger.info(f"Loaded {len(messages)} messages from Java for session {session_id}")
        except Exception as e:
            logger.warning(f"Failed to load history from Java: {e}")

    def _sync_summary_to_java(self, session_id: str, summary: str, up_to: int):
        """Persist summary to Java/MySQL via REST API."""
        try:
            payload = json.dumps({
                "role": "system",
                "content": f"__SUMMARY__:{json.dumps({'text': summary, 'up_to': up_to})}",
                "sources": "[]",
            }).encode("utf-8")
            req = Request(
                f"{self._java_url}/api/chat/session/{session_id}/message",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urlopen(req, timeout=5)
            logger.debug(f"Summary synced to Java: session={session_id}, up_to={up_to}")
        except Exception as e:
            logger.warning(f"Failed to sync summary to Java: {e}")

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
