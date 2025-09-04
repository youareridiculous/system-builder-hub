"""
Co-Builder Generator for code changes and diffs
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict, Any
import time, json
import logging

logger = logging.getLogger(__name__)

@dataclass
class GenerationResult:
    response: str
    file: Optional[str] = None
    diff: Optional[str] = None
    snippet: Optional[str] = None
    model: Optional[str] = None
    elapsed_ms: int = 0

SYSTEM_PROMPT = """You are Co-Builder, a careful code editor.
- Return a unified diff for ONE file only.
- No breaking changes.
- Prefer adding an optional string field `tenant_description` defaulting to "" to the single source of tenant metadata.
- If that file is a JSON/Pydantic model, extend it; otherwise extend the single defining file.
- Include a tiny 'smoke' snippet (doctest or one-liner CLI) that reads/prints the parsed value with & without the new field present.
- Output must be a valid unified diff (---/+++), with correct relative path in headers.
"""

USER_WRAP = """User request:
{request}

Repository context hints (if any):
{context}

Return JSON with keys exactly: file, diff, snippet, summary.
- file: relative path string (e.g. src/tenant/model.py)
- diff: unified diff string
- snippet: short code/CLI text, optional
- summary: 1–2 sentence human summary
"""

class CoBuilderGenerator:
    def __init__(self, llm_client, model_default: str = "gpt-4o-mini"):
        self.client = llm_client
        self.model_default = model_default

    def apply_change(self, *, prompt: str, tenant_id: str,
                     request_id: str, deadline_ts: float) -> GenerationResult:
        start = time.monotonic()
        
        # Check if we have a valid LLM client
        if not self.client:
            raise Exception("No LLM client available")
        
        # Choose model & remaining time
        remaining = max(0.0, deadline_ts - start)
        if remaining < 0.75:  # practically out of time
            raise TimeoutError("No time remaining for generation")

        model = self.model_default
        
        # Build messages
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_WRAP.format(request=prompt, context="")}
        ]

        try:
            resp = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.2,
                timeout=remaining,
            )
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise

        try:
            text = resp.choices[0].message.content.strip()
        except Exception:
            logger.error("LLM response shape unexpected; missing choices[0].message.content")
            text = ""
            
        # Parse JSON payload; if not JSON, try to extract fenced blocks
        data = json.loads(text) if text else {}
        file = data.get("file")
        diff = data.get("diff")
        snippet = data.get("snippet")
        summary = data.get("summary") or "Change prepared."

        # Minimal validation + fallback
        if diff and not (diff.startswith("--- ") and "\n+++ " in diff):
            logger.warning("LLM returned diff but it doesn't look unified; leaving as-is")

        if not (file and diff):
            # Try to recover from fenced blocks in plain text
            file = file or self._extract_fenced(text, "file") or self._extract_file_from_diff(text)
            diff = diff or self._extract_fenced(text, "diff")
            snippet = snippet or self._extract_fenced(text, "snippet")

        elapsed_ms = int((time.monotonic() - start) * 1000)
        return GenerationResult(
            response=summary, file=file, diff=diff, snippet=snippet,
            model=model, elapsed_ms=elapsed_ms
        )

    def _extract_fenced(self, text: str, wanted: str):
        """Extract fenced code blocks from text"""
        import re
        _FENCE = re.compile(r"```(?P<tag>\w+)?\s*(?P<body>[\s\S]*?)```", re.M)
        for m in _FENCE.finditer(text or ""):
            tag = (m.group("tag") or "").lower()
            body = (m.group("body") or "").strip()
            if wanted == "diff" and tag in ("diff", "patch"):
                return body
            if wanted == "snippet" and tag in ("python","bash","sh","txt","snippet"):
                return body
            if wanted == "file" and tag == "file":
                return body.splitlines()[0].strip()
        return None

    def _extract_file_from_diff(self, text: str):
        """Extract file path from diff text"""
        import re
        _DIFF_FILE = re.compile(r"^--- a\/(?P<path>.+)$", re.M)
        m = _DIFF_FILE.search(text or "")
        return m.group("path") if m else None
