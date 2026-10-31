"""
Ollama Provider for local open-source models (Llama 3.1, Qwen 2.5).
"""

from typing import List, Dict, Any, Optional
import json
import time
import httpx
from agentprobe.llm.base import BaseLLMProvider, LLMResponse
from agentprobe.tools.base import ToolCall
from agentprobe.config import settings


class OllamaProvider(BaseLLMProvider):
    """Local / Self-hosted open-source model provider via Ollama."""

    def __init__(self, model_name: str = "llama3.1:8b", base_url: Optional[str] = None):
        self.model_name = model_name
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")

    def generate(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.0,
    ) -> LLMResponse:
        payload: Dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if tools:
            payload["tools"] = tools

        start_time = time.perf_counter()
        with httpx.Client(timeout=60.0) as client:
            response = client.post(f"{self.base_url}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()

        latency_ms = (time.perf_counter() - start_time) * 1000.0
        msg = data.get("message", {})

        tool_calls = []
        for tc in msg.get("tool_calls", []):
            fn = tc.get("function", {})
            args = fn.get("arguments", {})
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except Exception:
                    args = {"raw": args}
            tool_calls.append(
                ToolCall(
                    name=fn.get("name"),
                    arguments=args,
                )
            )

        return LLMResponse(
            thought=msg.get("thinking") or "Local open-source model inference.",
            content=msg.get("content"),
            tool_calls=tool_calls,
            input_tokens=data.get("prompt_eval_count", 0),
            output_tokens=data.get("eval_count", 0),
            latency_ms=latency_ms,
            model_name=self.model_name,
            raw_response=data,
        )

