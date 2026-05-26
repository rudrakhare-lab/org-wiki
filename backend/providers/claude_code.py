"""
Claude Code provider — calls `claude -p` (Claude Code CLI) as a subprocess.

Auth: uses the admin's enterprise Claude Code session that was authenticated
via `claude login`. All queries in this mode bill against that enterprise seat.

The system prompt and retrieved context are embedded directly in the prompt
(Claude Code CLI does not expose a separate system-prompt channel in -p mode).
"""
from __future__ import annotations

import shutil
import subprocess

from backend.providers.base import ProviderResult

_TIMEOUT_S = 120


class ClaudeCodeProvider:
    """
    Wraps `claude -p` subprocess. The full context (system + user message)
    is passed via stdin so there is no shell argument-length limit.
    """

    @staticmethod
    def available() -> bool:
        """Return True if the `claude` CLI is reachable on PATH."""
        return shutil.which("claude") is not None

    def generate(self, system_prompt: str, user_message: str) -> ProviderResult:
        if not self.available():
            return ProviderResult(
                raw_answer="",
                error="Claude Code CLI is not installed or not in PATH on this server.",
            )

        # Combine system prompt + user message into a single prompt string.
        # The <system> / </system> XML-like tags are a convention Claude models
        # recognise for distinguishing instructions from the actual question.
        full_prompt = (
            f"<system>\n{system_prompt}\n</system>\n\n"
            f"{user_message}"
        )

        try:
            proc = subprocess.run(
                ["claude", "-p"],
                input=full_prompt,
                capture_output=True,
                text=True,
                timeout=_TIMEOUT_S,
            )
        except subprocess.TimeoutExpired:
            return ProviderResult(
                raw_answer="",
                error=f"Claude Code timed out after {_TIMEOUT_S}s.",
            )
        except FileNotFoundError:
            return ProviderResult(
                raw_answer="",
                error="'claude' executable not found. Ensure Claude Code is installed and in PATH.",
            )
        except Exception as exc:
            return ProviderResult(raw_answer="", error=f"Claude Code subprocess error: {exc}")

        if proc.returncode != 0:
            stderr = (proc.stderr or "").strip()
            return ProviderResult(
                raw_answer="",
                error=f"Claude Code exited with code {proc.returncode}: {stderr or 'no error output'}",
            )

        return ProviderResult(raw_answer=proc.stdout.strip())
