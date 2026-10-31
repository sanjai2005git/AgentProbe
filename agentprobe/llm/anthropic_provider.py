"""
Anthropic Claude Provider supporting tools and multi-turn conversations.
"""

from typing import List, Dict, Any, Optional
import time
import httpx
from agentprobe.llm.base import BaseLLMProvider, LLMResponse
from agentprobe.tools.base import ToolCall
from agentprobe.config import settings


class AnthropicProvider(BaseLLMProvider):
    """Anthropic API Provider for Claude 3.5 Sonnet / Claude 3.5 Haiku."""

    def __init__(self, model_name: str = "claude-3-5-sonnet-20241022", api_key: Optional[str] = None):
        self.model_name = model_name
        self.api_key = api_key or settings.anthropic_api_key
        self.base_url = "https://api.anthropic.com/v1"

    def generate(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.0,
    ) -> LLMResponse:
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY is not configured. Set it in .env or pass it to AnthropicProvider.")

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        system_prompt = "You are an enterprise payment operations investigation agent."
        claude_messages = []
        for m in messages:
            if m.get("role") == "system":
                system_prompt = m.get("content", system_prompt)
            else:
                role = "user" if m.get("role") in ["user", "tool"] else "assistant"
                claude_messages.append({"role": role, "content": m.get("content", "")})

        # Format tools to Claude specification
        claude_tools = []
        if tools:
            for t in tools:
                fn = t.get("function", {})
                claude_tools.append({
                    "name": fn.get("name"),
                    "description": fn.get("description"),
                    "input_schema": fn.get("parameters", {"type": "object", "properties": {}}),
                })

        payload: Dict[str, Any] = {
            "model": self.model_name,
            "max_tokens": 1024,
            "system": system_prompt,
            "messages": claude_messages,
            "temperature": temperature,
        }
        if claude_tools:
            payload["tools"] = claude_tools

        start_time = time.perf_counter()
        with httpx.Client(timeout=45.0) as client:
            response = client.post(f"{self.base_url}/messages", headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        latency_ms = (time.perf_counter() - start_time) * 1000.0
        usage = data.get("usage", {})

        tool_calls = []
        text_content = []
        for block in data.get("content", []):
            if block.get("type") == "text":
                text_content.append(block.get("text", ""))
            elif block.get("type") == "tool_use":
                tool_calls.append(
                    ToolCall(
                        id=block.get("id"),
                        name=block.get("name"),
                        arguments=block.get("input", {}),
                    )
                )

        return LLMResponse(
            thought="Claude reasoning chain processed.",
            content="\n".join(text_content) if text_content else None,
            tool_calls=tool_calls,
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            latency_ms=latency_ms,
            model_name=self.model_name,
            raw_response=data,
        )

