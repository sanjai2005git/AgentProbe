"""
OpenAI LLM Provider supporting tool calling and reasoning inspection.
"""

from typing import List, Dict, Any, Optional
import json
import time
import httpx
from agentprobe.llm.base import BaseLLMProvider, LLMResponse
from agentprobe.tools.base import ToolCall
from agentprobe.config import settings


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API Provider for GPT-4o and GPT-4o-mini."""

    def __init__(self, model_name: str = "gpt-4o-mini", api_key: Optional[str] = None):
        self.model_name = model_name
        self.api_key = api_key or settings.openai_api_key
        self.base_url = "https://api.openai.com/v1"

    def generate(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.0,
    ) -> LLMResponse:
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not configured. Set it in .env or pass it to OpenAIProvider.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload: Dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        start_time = time.perf_counter()
        with httpx.Client(timeout=45.0) as client:
            response = client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        latency_ms = (time.perf_counter() - start_time) * 1000.0
        choice = data["choices"][0]["message"]
        usage = data.get("usage", {})

        tool_calls = []
        if "tool_calls" in choice and choice["tool_calls"]:
            for tc in choice["tool_calls"]:
                try:
                    args = json.loads(tc["function"]["arguments"])
                except Exception:
                    args = {"raw": tc["function"]["arguments"]}
                tool_calls.append(
                    ToolCall(
                        id=tc.get("id"),
                        name=tc["function"]["name"],
                        arguments=args,
                    )
                )

        return LLMResponse(
            thought=choice.get("refusal") or "Thought processed by model.",
            content=choice.get("content"),
            tool_calls=tool_calls,
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            latency_ms=latency_ms,
            model_name=self.model_name,
            raw_response=data,
        )

