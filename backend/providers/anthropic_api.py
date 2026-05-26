"""
Anthropic API provider — uses the user's own claude_api_key per request.
The key is never stored server-side; it arrives in the request body and is
used only for the duration of that single API call.
"""
from __future__ import annotations

import anthropic

from backend.providers.base import ProviderResult

_MODEL = "claude-sonnet-4-6"
_MAX_TOKENS = 2048


class AnthropicAPIProvider:
    """Calls the Anthropic Messages API with the caller-supplied api_key."""

    def __init__(self, api_key: str) -> None:
        self._client = anthropic.Anthropic(api_key=api_key)

    def generate(self, system_prompt: str, user_message: str) -> ProviderResult:
        try:
            msg = self._client.messages.create(
                model=_MODEL,
                max_tokens=_MAX_TOKENS,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
            text = msg.content[0].text if msg.content else ""
            return ProviderResult(raw_answer=text)
        except anthropic.AuthenticationError:
            return ProviderResult(
                raw_answer="",
                error="Invalid Anthropic API key. Please check your key and try again.",
            )
        except anthropic.RateLimitError:
            return ProviderResult(
                raw_answer="",
                error="Anthropic API rate limit reached. Please wait a moment and retry.",
            )
        except Exception as exc:
            return ProviderResult(raw_answer="", error=f"Claude API error: {exc}")
