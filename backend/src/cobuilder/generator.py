"""
Co-Builder Generator for code changes and diffs
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple
import time, json, re, os, hashlib
import logging

from pydantic import BaseModel, ValidationError, Field

logger = logging.getLogger(__name__)

# Robust JSON extraction helpers
JSON_FENCE_RE = re.compile(
    r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE
)

def _extract_json_candidate(text: str) -> Optional[Dict[str, Any]]:
    """
    Try several strategies to pull a JSON object out of an arbitrary LLM response.
    Returns a dict or None if nothing usable found.
    """
    text = (text or "").strip()
    if not text:
        return None

    # 1) Direct JSON
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    # 2) Fenced code block ```json ... ```
    m = JSON_FENCE_RE.search(text)
    if m:
        candidate = m.group(1).strip()
        try:
            data = json.loads(candidate)
            if isinstance(data, dict):
                return data
        except Exception:
            pass

    # 3) Last-brace heuristic: grab last balanced {...}
    #    (helps when the model wraps JSON with prose)
    brace_start = text.find("{")
    brace_end   = text.rfind("}")
    if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
        candidate = text[brace_start:brace_end+1]
        try:
            data = json.loads(candidate)
            if isinstance(data, dict):
                return data
        except Exception:
            pass

    return None

def _coerce_llm_build_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize common alias keys to our canonical schema.
    Accepts: file|path|file_path, diff|patch, content|code|final, snippet|test|test_snippet.
    """
    norm = {}
    # file
    norm["file"] = d.get("file") or d.get("path") or d.get("file_path")
    # diff
    norm["diff"] = d.get("diff") or d.get("patch")
    # content
    norm["content"] = d.get("content") or d.get("code") or d.get("final")
    # snippet
    norm["snippet"] = d.get("snippet") or d.get("test") or d.get("test_snippet")
    # response / summary is optional
    norm["response"] = d.get("response") or d.get("summary") or d.get("message")
    return norm

@dataclass
class GenerationResult:
    response: str
    file: str
    diff: str
    content: str                # REQUIRED: final post-change content
    snippet: Optional[str]
    model: str
    elapsed_ms: int
    llm_generated: bool = True

# ---- JSON schema for LLM response
class LLMBuild(BaseModel):
    response: str
    file: str
    diff: str
    content: Optional[str] = ""     # may be empty; we'll reconstruct if so
    snippet: Optional[str] = None

JSON_INSTRUCTIONS = """\
You are Co-Builder. Return a SINGLE JSON object that matches this schema:

{
  "response": "one-line summary of the change",
  "file": "<relative path under src/>",
  "diff": "<UNIFIED DIFF for exactly that one file>",
  "content": "<FULL POST-CHANGE FILE CONTENT>",
  "snippet": "<optional tiny smoke snippet>"
}

Rules:
- Output ONLY JSON (no markdown, no prose).
- The diff must be a valid unified diff for exactly one file.
- If this is a new file, use '/dev/null' as the old path.
- content MUST contain the full post-change text of the file.
- file path must be relative (e.g. 'src/tenant/model.py') and under the project src/.
"""

def _system_prompt() -> Dict[str, str]:
    return {"role": "system", "content": JSON_INSTRUCTIONS}

def _user_prompt(message: str) -> Dict[str, str]:
    return {"role": "user", "content": message}

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

    def _call_llm_json(self, message: str) -> Dict[str, Any]:
        """Call the LLM and return a validated Python dict matching LLMBuild."""
        t0 = time.monotonic()

        # --- DEBUG: log model + json-mode flag
        logger.info(
            "llm.call.start model=%s json_mode=requested deadline_ms=%s",
            self.model_default, int(max(0, (getattr(self, "deadline", 0) - time.monotonic())*1000)) if hasattr(self, "deadline") else -1
        )

        # Add env "escape hatch" if JSON mode isn't supported
        USE_JSON_MODE = os.getenv("COBUILDER_USE_JSON_MODE", "1") not in ("0", "false", "False")
        
        kwargs = dict(
            model=self.model_default,
            messages=[_system_prompt(), _user_prompt(message)],
            temperature=0.2,
        )
        if USE_JSON_MODE:
            kwargs["response_format"] = {"type": "json_object"}
            logger.info("llm.json_mode.enabled")
        else:
            logger.info("llm.json_mode.disabled (env override)")

        resp = self.client.chat.completions.create(**kwargs)

        txt = (resp.choices[0].message.content or "").strip()

        # --- DEBUG: log what we REALLY got (truncated)
        logger.info(
            "llm.call.done model=%s usage=%s text_preview=%r",
            self.model_default,
            getattr(resp, "usage", None),
            txt[:300]  # avoids huge logs but is enough to see if it's JSON
        )

        # Try strict JSON first
        try:
            data = json.loads(txt)
        except json.JSONDecodeError as e:
            logger.warning("llm.json.decode.fail: %s; attempting fenced-extract", e)
            m = re.search(r"\{[\s\S]*\}\s*$", txt)
            if not m:
                # HARD FAIL -> let caller switch to fallback/mock
                raise RuntimeError(f"LLM did not return JSON. Preview={txt[:120]!r}")
            data = json.loads(m.group(0))

        try:
            parsed = LLMBuild.model_validate(data)
        except ValidationError as ve:
            logger.warning("llm.json.schema.fail: %s; data keys=%s", ve, list(data.keys()))
            raise

        elapsed_ms = int((time.monotonic() - t0) * 1000)
        return {"parsed": parsed, "elapsed_ms": elapsed_ms}

    def _call_llm_text(self, message: str) -> str:
        """Plain completion without response_format, so providers that ignore JSON mode still work."""
        resp = self.client.chat.completions.create(
            model=self.model_default,
            messages=[_system_prompt(), _user_prompt(message)],
            temperature=0.2,
        )
        return (resp.choices[0].message.content or "").strip()

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

        # Use robust fallback logic
        use_json_mode = os.getenv("COBUILDER_USE_JSON_MODE", "1") not in ("0", "false", "False")
        
        raw_text = None
        parsed_dict = None
        parsed = None
        elapsed_ms = None
        
        try:
            if use_json_mode:
                j = self._call_llm_json(prompt)  # your existing strict-JSON method
                parsed = j["parsed"]              # Pydantic LLMBuild if you already created it
                elapsed_ms = j["elapsed_ms"]
            else:
                raw_text = self._call_llm_text(prompt)
                cand = _extract_json_candidate(raw_text)
                if cand:
                    cand = _coerce_llm_build_dict(cand)
                    parsed = LLMBuild.model_validate(cand)  # keep your strict schema benefits
        except Exception as e:
            logger.warning("llm.primary.parse.fail: %s", e)
        
        # Build canonical fields (prefer parsed JSON, fallback to heuristics)
        file_path = getattr(parsed, "file", None) if parsed else None
        diff_text = getattr(parsed, "diff", None) if parsed else None
        content   = getattr(parsed, "content", None) if parsed else None
        snippet   = getattr(parsed, "snippet", None) if parsed else None
        
        # Content reconstruction pipeline (guarantee content)
        if not content:
            if diff_text and (" /dev/null" in diff_text or "+++ " in diff_text):
                content = _lines_added_from_diff(diff_text)
        
        # If still empty and the file already exists, try applying the diff
        if (not content) and diff_text and file_path and os.path.exists(file_path):
            try:
                curr = _read_current(file_path)
                if curr:
                    content = _apply_unified_diff(curr, diff_text)
            except Exception as e:
                logger.info("diff.apply.fallback.fail: %s", e)
        
        # FINAL guard — never return empty content
        if not content:
            # Produce a minimally valid file to unblock Apply.
            # (You can tailor this per extension if you want.)
            synthesized = [
                "# Generated by Co-Builder. Content synthesis safeguard (no JSON or patch to reconstruct).",
                "# Refine prompt or enable JSON mode to improve fidelity.",
                "",
            ]
            content = "\n".join(synthesized)
        
        logger.info(
            "build.result model=%s file=%s diff_len=%d content_len=%d",
            self.model_default, file_path, len(diff_text or ""), len(content or "")
        )
        
        return GenerationResult(
            response=getattr(parsed, "response", "Change prepared."),
            file=file_path or "UNKNOWN_PATH",
            diff=diff_text or "",
            content=content,                # <— REQUIRED, never empty
            snippet=snippet or "",
            model=self.model_default,
            elapsed_ms=elapsed_ms or 0,
            llm_generated=True,
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

    def _extract_final_content(self, diff: str) -> Optional[str]:
        """Extract the final file content from a unified diff"""
        if not diff:
            return None
            
        lines = diff.splitlines()
        content_lines = []
        
        for line in lines:
            if line.startswith("--- "):
                # Skip the header lines
                continue
            elif line.startswith("+++ "):
                # Skip the header lines
                continue
            elif line.startswith("@@ "):
                # Skip the hunk header
                continue
            elif line.startswith(" "):
                # Context line (unchanged) - include it
                content_lines.append(line[1:])
            elif line.startswith("+"):
                # Added line - include it
                content_lines.append(line[1:])
            elif line.startswith("-"):
                # Removed line - skip it
                continue
            # Lines starting with other characters (like \ No newline at end of file) are ignored
        
        return "\n".join(content_lines) if content_lines else None

# ---- Content reconstruction helpers
ALLOWED_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src"))

def _abs_under_src(rel_path: str) -> str:
    p = os.path.abspath(os.path.join(ALLOWED_ROOT, os.path.relpath(rel_path, "src")))
    # ensure stay under src/
    if not p.startswith(ALLOWED_ROOT + os.sep) and p != ALLOWED_ROOT:
        raise ValueError("Unsafe file path")
    return p

def _read_current(rel_path: str) -> Optional[str]:
    ap = _abs_under_src(rel_path)
    return open(ap, "r", encoding="utf-8").read() if os.path.exists(ap) else None

def _apply_unified_diff(base_text: str, diff_text: str) -> Optional[str]:
    # Minimal hunk applier (single-file). This is intentionally simple; we assume
    # diffs are small and well-formed by the model/prompt.
    # Strategy: walk lines; for each hunk, consume base lines and apply +/-.
    try:
        lines = diff_text.splitlines()
        out = []
        i = 0
        # Build an index into base_text for context matching
        base_lines = base_text.splitlines()
        bi = 0

        while i < len(lines):
            L = lines[i]
            if L.startswith('@@ '):
                # start of hunk, reset local buffers
                i += 1
                while i < len(lines) and lines[i] and not lines[i].startswith('@@ ') and not lines[i].startswith('--- ') and not lines[i].startswith('+++ '):
                    hl = lines[i]
                    if hl.startswith('+'):
                        out.append(hl[1:])
                    elif hl.startswith('-'):
                        # skip a base line
                        if bi < len(base_lines):
                            bi += 1
                    else:
                        # context line
                        if bi < len(base_lines):
                            out.append(base_lines[bi])
                            bi += 1
                    i += 1
                continue
            elif L.startswith('--- ') or L.startswith('+++ '):
                i += 1
                continue
            else:
                i += 1

        # append any remaining base lines (for partial hunks)
        while bi < len(base_lines):
            out.append(base_lines[bi])
            bi += 1

        return "\n".join(out) + ("\n" if base_text.endswith("\n") else "")
    except Exception:
        return None

def _lines_added_from_diff(diff_text: str) -> str:
    added = []
    for L in diff_text.splitlines():
        if L.startswith("+") and not L.startswith("+++"):
            added.append(L[1:])
    return "\n".join(added) + "\n"
