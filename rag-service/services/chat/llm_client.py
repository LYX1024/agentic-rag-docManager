"""AsyncOpenAI LLM client wrapper for streaming chat."""
from openai import AsyncOpenAI
from loguru import logger


class LLMClient:
    """Async wrapper around OpenAI-compatible chat completion API."""

    def __init__(self, base_url: str, api_key: str, timeout: float = 120.0):
        self.client = AsyncOpenAI(base_url=base_url, api_key=api_key, timeout=timeout)
        logger.info(f"LLMClient initialized: base_url={base_url}")

    async def stream(self, model: str, messages: list[dict],
                     temperature: float = 0.7, max_tokens: int = 2048):
        """Stream chat completion tokens as an async generator."""
        stream = await self.client.chat.completions.create(
            model=model, messages=messages,
            temperature=temperature, max_tokens=max_tokens, stream=True)
        async for chunk in stream:
            if chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if delta.content:
                    yield delta.content

    async def create_with_tools(self, model: str, messages: list[dict],
                                tools: list[dict] | None = None,
                                temperature: float = 0.7):
        """Non-streaming completion with optional tool definitions."""
        kwargs = dict(model=model, messages=messages, temperature=temperature)
        if tools:
            kwargs["tools"] = tools
        return await self.client.chat.completions.create(**kwargs)
