"""Thin Anthropic wrapper that forces structured output via tool use.

We give the model a single tool whose input_schema is the JSON schema of the
Pydantic model we want back, and force tool_choice to that tool. The model must
then return arguments matching the schema, which we validate. This is how the
claim/mapping schemas get *enforced* rather than parsed out of free text.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from app.config import settings


class LLMUnavailable(RuntimeError):
    """Raised when an LLM call is attempted with no API key configured."""


class LLMClient:
    def __init__(self) -> None:
        self._client: Any = None
        if settings.llm_available:
            from anthropic import Anthropic

            self._client = Anthropic(api_key=settings.anthropic_api_key)

    @property
    def available(self) -> bool:
        return self._client is not None

    def structured(
        self,
        *,
        model: str,
        system: str,
        user_text: str,
        schema: type[BaseModel],
        images: list[str] | None = None,
        max_tokens: int = 4096,
    ) -> dict:
        """Return the raw tool-input dict matching `schema`. Caller validates."""
        if self._client is None:
            raise LLMUnavailable(
                "No ANTHROPIC_API_KEY set; this path requires an LLM."
            )

        tool_name = "emit_" + schema.__name__.lower()
        content: list[dict] = [{"type": "text", "text": user_text}]
        for img in images or []:
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": img,
                    },
                }
            )

        response = self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            tools=[
                {
                    "name": tool_name,
                    "description": f"Emit a well-formed {schema.__name__}.",
                    "input_schema": schema.model_json_schema(),
                }
            ],
            tool_choice={"type": "tool", "name": tool_name},
            messages=[{"role": "user", "content": content}],
        )

        for block in response.content:
            if getattr(block, "type", None) == "tool_use":
                return dict(block.input)
        raise ValueError("model did not return a tool_use block")


# Module-level singleton; cheap to construct, holds the SDK client.
llm = LLMClient()
