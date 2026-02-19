"""
assistant_core.py — Embedded AI assistant integration for Computer Main Centre (CMC).

This variant talks to a LOCAL Ollama server running on http://localhost:11434
(using the standard /api/chat endpoint).

Public entry points used by Computer_Main_Centre.py:
    run_ai_assistant(user_query, cwd, state, macros, aliases) -> str
    run_ai_fix(last_cmd, last_error, cwd, state, macros, aliases) -> str
    clear_history() -> None
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Manual loading
# ---------------------------------------------------------------------------

_MANUAL_CACHE: Optional[str] = None


def clear_manual_cache():
    global _MANUAL_CACHE
    _MANUAL_CACHE = None


def _default_manual_path() -> Path:
    """Return default path to the full CMC AI manual."""
    env = os.getenv("CMC_AI_MANUAL")
    if env:
        return Path(env).expanduser()
    here = Path(__file__).resolve().parent.parent
    return here / "manuals" / "CMC_AI_Manual.md"


def load_cmc_manual(path: Optional[Path | str] = None) -> str:
    """
    Load the CMC AI manual from disk, with a very small in-memory cache.
    If the manual is missing, return a stub so the assistant can still respond.
    """
    global _MANUAL_CACHE
    if _MANUAL_CACHE is not None:
        return _MANUAL_CACHE

    manual_path = Path(path) if path is not None else _active_manual_path()
    try:
        _MANUAL_CACHE = manual_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        _MANUAL_CACHE = (
            "# CMC AI Manual missing\n"
            "The manual file could not be found. "
            "Create it in the manuals/ folder next to src/.\n"
        )
    return _MANUAL_CACHE


# ---------------------------------------------------------------------------
# Conversation history  (rolling window, cleared on model switch)
# ---------------------------------------------------------------------------

_HISTORY: List[Dict[str, str]] = []
_HISTORY_MAX = 10   # max user+assistant message pairs to keep


def clear_history():
    """Clear the AI conversation history (called on model switch or manual reset)."""
    global _HISTORY
    _HISTORY = []


def _add_to_history(role: str, content: str):
    global _HISTORY
    _HISTORY.append({"role": role, "content": content})
    # Keep last N pairs (each pair = 2 messages)
    max_msgs = _HISTORY_MAX * 2
    if len(_HISTORY) > max_msgs:
        _HISTORY = _HISTORY[-max_msgs:]


# ---------------------------------------------------------------------------
# Context building helpers
# ---------------------------------------------------------------------------


def build_context_blob(
    cwd: str,
    state: Dict[str, Any],
    macros: Dict[str, str],
    aliases: Optional[Dict[str, str]] = None,
) -> str:
    """
    Turn the current CMC state into a compact context string passed to the AI.
    Includes: cwd, flags, macro names, alias names, java version, recent log,
    and a brief listing of the current folder.
    """
    # Current folder listing (top level only, max 30 entries)
    folder_listing: List[str] = []
    try:
        p = Path(cwd)
        entries = sorted(p.iterdir(), key=lambda e: (e.is_file(), e.name.lower()))
        for e in entries[:30]:
            folder_listing.append(("  " if e.is_file() else "📁 ") + e.name)
        if len(list(p.iterdir())) > 30:
            folder_listing.append("  ... (truncated)")
    except Exception:
        folder_listing = ["(could not read folder)"]

    # Recent log entries
    recent_log: List[str] = []
    try:
        log = state.get("log", [])
        recent_log = list(log)[-6:] if log else []
    except Exception:
        pass

    # Build macros with their full body so AI knows what they do
    macros_detail = {name: body for name, body in macros.items()}

    # Build aliases with their full command so AI knows what they do
    aliases_detail = {name: cmd for name, cmd in (aliases or {}).items()}

    safe_state = {
        "cwd": cwd,
        "flags": {
            "batch": bool(state.get("batch", False)),
            "dry_run": bool(state.get("dry_run", False)),
            "ssl_verify": bool(state.get("ssl_verify", True)),
        },
        "java_version": state.get("java_version", "?"),
        "macros": macros_detail,
        "aliases": aliases_detail,
        "folder_listing": folder_listing,
        "recent_log": recent_log,
    }
    return json.dumps(safe_state, indent=2, ensure_ascii=False)


def build_system_prompt(
    cwd: str,
    state: Dict[str, Any],
    macros: Dict[str, str],
    aliases: Optional[Dict[str, str]] = None,
) -> str:
    """
    Build the full system prompt used for each AI call.
    """
    ctx = build_context_blob(cwd, state, macros, aliases)
    manual = load_cmc_manual(_active_manual_path())

    prefix = (
        "You are the embedded AI assistant for Computer Main Centre (CMC).\n"
        "You are NOT a general chatbot. You MUST answer strictly in terms of CMC,\n"
        "its commands, its behaviour and its manual.\n\n"

        "HIGH-PRIORITY RULES (OVERRIDE ANY TRAINING HABITS):\n"
        "  1. All file and folder paths in CMC MUST use single quotes.\n"
        "     Example: copy 'C:/Project/file.txt' 'C:/Backup/file.txt'\n"
        "     Never claim that CMC uses double quotes for paths.\n"
        "  2. Use commas ',' to chain multiple CMC commands. Never put a comma at the end.\n"
        "  3. Never invent new commands or future features. Only use commands in the manual.\n"
        "  4. Never perform destructive actions unless the user clearly and explicitly asks.\n"
        "  5. BREVITY: Keep answers SHORT by default. 1-3 lines max unless the user asks\n"
        "     for more detail, a full explanation, or a script. No padding, no restating\n"
        "     the question, no 'Great question!' filler. Just the answer.\n"
        "  6. When the user asks for commands, output them in a ```cmc``` code block.\n"
        "  7. If you are not sure what to do, ask one short clarifying question.\n"
        "  8. The CMC `space` command is disk usage/cleanup. Not related to outer space.\n"
        "  9. You have conversation history. Use it for follow-up questions, but do not\n"
        "     repeat what was already said.\n"
        " 10. You can see the user's current folder contents, recent log, macros and aliases\n"
        "     in the context below. Use this to give relevant, specific answers.\n\n"

        "Current CMC context (JSON):\n"
        f"{ctx}\n\n"
        "Below is the CMC AI manual — treat it as ground truth.\n"
        "----- BEGIN CMC_AI_Manual -----\n"
    )

    suffix = "\n----- END CMC_AI_Manual -----\n"
    return prefix + manual + suffix


# ---------------------------------------------------------------------------
# Dynamic model + manual selection
# ---------------------------------------------------------------------------

def _get_active_model() -> str:
    """Load active AI model from CMC_Config.json."""
    try:
        import CMC_Config
        cfg = CMC_Config.load_config()
        return cfg.get("ai", {}).get("model", "llama3.1:8b")
    except Exception:
        return "llama3.1:8b"


def _active_manual_path() -> Path:
    """Choose correct manual depending on the active model."""
    model = _get_active_model().lower()
    here = Path(__file__).resolve().parent.parent
    manuals_dir = here / "manuals"

    if any(x in model for x in ("14b", "32b", "72b", "70b")):
        name = "CMC_AI_Manual_MEDIUM.md"
    else:
        name = "CMC_AI_Manual_MINI.md"

    path = manuals_dir / name
    if path.exists():
        return path
    return here / name


# ---------------------------------------------------------------------------
# Ollama backend
# ---------------------------------------------------------------------------

_OLLAMA_URL = os.getenv("CMC_AI_OLLAMA_URL", "http://localhost:11434/api/chat")


def _call_ai_backend(messages: List[Dict[str, str]]) -> str:
    """
    Call the Ollama /api/chat endpoint with the given messages list and return
    the assistant reply as a plain string.
    """
    try:
        import requests  # type: ignore
    except Exception as exc:
        raise RuntimeError(
            "The 'requests' library is required but is not installed.\n"
            "Run: pip install requests"
        ) from exc

    payload = {
        "model": _get_active_model(),
        "messages": messages,
        "stream": False,
    }

    try:
        resp = requests.post(_OLLAMA_URL, json=payload, timeout=120)
    except Exception as exc:
        raise RuntimeError(
            f"Could not reach Ollama at {_OLLAMA_URL}. Is Ollama running?\n"
            "Try starting the Ollama app, or check CMC_AI_OLLAMA_URL."
        ) from exc

    if resp.status_code != 200:
        raise RuntimeError(f"Ollama HTTP {resp.status_code}: {resp.text[:400]}")

    try:
        data = resp.json()
    except Exception as exc:
        raise RuntimeError(f"Failed to decode Ollama JSON: {resp.text[:400]}") from exc

    msg = data.get("message") or {}
    content = msg.get("content")
    if not isinstance(content, str):
        raise RuntimeError(f"Ollama reply did not contain assistant content: {data!r}")
    return content.strip()


# ---------------------------------------------------------------------------
# Local Fuzzy Path Search (AI super-find)
# ---------------------------------------------------------------------------

def ai_smart_find(query: str, limit: int = 20):
    """Natural-language fuzzy search for local files/folders."""
    try:
        from path_index_local import super_find
        results = super_find(query, limit)
        return results
    except Exception as e:
        return [{"path": f"[AI-Search-Error] {e}", "score": 0}]


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------


def run_ai_assistant(
    user_query: str,
    cwd: str,
    state: Dict[str, Any],
    macros: Dict[str, str],
    aliases: Optional[Dict[str, str]] = None,
) -> str:
    """
    Main entry point for the `ai` command inside CMC.
    Uses rolling conversation history so follow-up questions work.
    """
    system_prompt = build_system_prompt(cwd, state, macros, aliases)

    # Build full messages: system + history + new user message
    messages: List[Dict[str, str]] = [
        {"role": "system", "content": system_prompt},
        *_HISTORY,
        {"role": "user", "content": user_query.strip()},
    ]

    reply = _call_ai_backend(messages)

    # Store this exchange in history
    _add_to_history("user", user_query.strip())
    _add_to_history("assistant", reply)

    return reply.strip()


def run_ai_fix(
    last_cmd: str,
    last_error: str,
    cwd: str,
    state: Dict[str, Any],
    macros: Dict[str, str],
    aliases: Optional[Dict[str, str]] = None,
) -> str:
    """
    Entry point for the `ai fix` command.
    Passes the last failed command + error to the AI and asks for a fix.
    Does NOT add to conversation history (it's a one-shot diagnostic).
    """
    system_prompt = build_system_prompt(cwd, state, macros, aliases)

    fix_query = (
        f"The last CMC command failed.\n"
        f"Command: {last_cmd}\n"
        f"Error:   {last_error}\n\n"
        "What went wrong and what is the correct CMC command to fix it? "
        "Be brief."
    )

    messages: List[Dict[str, str]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": fix_query},
    ]

    reply = _call_ai_backend(messages)
    return reply.strip()


# ---------------------------------------------------------------------------
# Simple CLI test when run directly
# ---------------------------------------------------------------------------

if __name__ == "__main__":  # pragma: no cover
    import textwrap

    cwd = os.getcwd()
    state: Dict[str, Any] = {"batch": False, "dry_run": False, "ssl_verify": True}
    macros: Dict[str, str] = {}
    aliases: Dict[str, str] = {}

    print("assistant_core demo shell (Ollama).")
    print("Model:", _get_active_model())
    print("Ollama URL:", _OLLAMA_URL)
    print("Type 'clear' to reset history. Ctrl+C to exit.\n")

    try:
        while True:
            q = input("ai> ").strip()
            if not q:
                continue
            if q == "clear":
                clear_history()
                print("[History cleared]")
                continue
            try:
                ans = run_ai_assistant(q, cwd, state, macros, aliases)
            except Exception as e:
                print(f"[assistant_core] Error: {e}")
            else:
                print("\n--- AI reply ---")
                print(textwrap.indent(ans, "  "))
                print("----------------\n")
    except KeyboardInterrupt:
        print("\nExiting.")
