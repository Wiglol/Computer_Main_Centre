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

_MANUAL_CACHE: Dict[str, str] = {}   # keyed by resolved path string


def clear_manual_cache():
    """Clear cached manual content (call on model switch so the right manual reloads)."""
    global _MANUAL_CACHE
    _MANUAL_CACHE = {}


def _default_manual_path() -> Path:
    """Return default path to the full CMC AI manual."""
    env = os.getenv("CMC_AI_MANUAL")
    if env:
        return Path(env).expanduser()
    here = Path(__file__).resolve().parent.parent
    return here / "manuals" / "CMC_AI_Manual.md"


def load_cmc_manual(path: Optional[Path | str] = None) -> str:
    """
    Load the CMC AI manual from disk, with a path-keyed in-memory cache.
    Different models load different manuals; the cache key is the resolved path
    so switching from 8b→14b correctly loads MEDIUM instead of reusing MINI.
    """
    global _MANUAL_CACHE
    manual_path = Path(path) if path is not None else _active_manual_path()
    key = str(manual_path.resolve())

    if key in _MANUAL_CACHE:
        return _MANUAL_CACHE[key]

    try:
        _MANUAL_CACHE[key] = manual_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        _MANUAL_CACHE[key] = (
            "# CMC AI Manual missing\n"
            "The manual file could not be found. "
            "Create it in the manuals/ folder next to src/.\n"
        )
    return _MANUAL_CACHE[key]


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

    # Last N commands the user typed in this CMC session (includes typos / unknowns)
    recent_commands: List[str] = list(state.get("recent_commands", []))

    # Most recent failed / unrecognised command + its error, if any
    last_issue = state.get("last_issue")  # {"command": str, "error": str} or None

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
        "recent_commands": recent_commands,
        "last_issue": last_issue,
    }
    return json.dumps(safe_state, indent=2, ensure_ascii=False)


def _is_large_model() -> bool:
    """True for 14b+ models that can follow richer, more nuanced instructions."""
    model = _get_active_model().lower()
    return any(x in model for x in ("14b", "32b", "72b", "70b"))


def _build_prompt_prefix_small(ctx: str) -> str:
    """
    Terse, punchy prefix for small models (≤8b).
    Uses ALL-CAPS headings and explicit WRONG/RIGHT examples because small
    models ignore nuanced numbered lists.
    """
    return (
        "You are the built-in AI assistant for Computer Main Centre (CMC).\n"
        "CMC is a WINDOWS TERMINAL application with its OWN command set.\n"
        "It is NOT a shell, NOT bash, NOT PowerShell. There is no UI — only terminal output.\n\n"

        "=== ABSOLUTE RULES — breaking any one makes your answer WRONG ===\n\n"

        "PATHS — always single quotes, always forward slashes:\n"
        "  WRONG: cd c:\\users\\wiggo\\desktop    RIGHT: cd 'C:/Users/Wiggo/Desktop'\n"
        "  WRONG: copy \"file.txt\" \"backup/\"    RIGHT: copy 'file.txt' 'backup/'\n\n"

        "CHAINING — comma only, never 'and' / '&&' / ';':\n"
        "  WRONG: cd 'C:/path' and create folder 'test'\n"
        "  RIGHT: cd 'C:/path', create folder 'test'\n\n"

        "CMC-ONLY COMMANDS — NEVER suggest shell/OS commands:\n"
        "  BANNED: mkdir, rm, rmdir, ls, dir, del, grep, cat, touch\n"
        "  USE INSTEAD: create folder, delete, list, move, copy, rename, find, info, echo\n\n"

        "CONTEXT — you have full visibility; NEVER ask for info already shown below:\n"
        "  last_issue = the most recent failed command AND its exact error\n"
        "  macros     = full body of every saved macro\n"
        "  recent_commands = every command typed this session\n"
        "  If diagnosing a macro problem: read macros[name], spot the syntax error, give the fix.\n\n"

        "OUTPUT FORMAT:\n"
        "  - 1-3 lines by default. No filler, no restating the question.\n"
        "  - Wrap CMC commands in ```cmc code blocks.\n"
        "  - Never reference a UI, chat window, or interface — this is a terminal.\n\n"

        "Current CMC context (JSON):\n"
        f"{ctx}\n\n"
        "CMC manual — treat as ground truth for all available commands:\n"
        "----- BEGIN CMC_AI_Manual -----\n"
    )


def _build_prompt_prefix_large(ctx: str) -> str:
    """
    Prefix for large models (14b+).
    Only shows correct syntax — no WRONG examples, as models learn from
    every pattern they see regardless of the label attached to it.
    The mandatory rules are repeated as a short reminder at the END of the
    system prompt (after the manual) for maximum recency effect.
    """
    return (
        "You are the built-in AI assistant for Computer Main Centre (CMC), "
        "a Windows terminal application with its own command language.\n"
        "CMC is NOT a shell, NOT bash, NOT PowerShell. There is no graphical UI.\n\n"

        "=== MANDATORY SYNTAX — memorise this before reading anything else ===\n\n"

        "PATHS — single quotes, forward slashes, always:\n"
        "  cd 'C:/Users/Wiggo/Desktop'\n"
        "  copy 'C:/src/file.txt' to 'C:/Backup/'\n"
        "  cd 'C:/My Projects/App'       (spaces are fine inside single quotes)\n\n"

        "CHAINING — comma-separated, no trailing comma:\n"
        "  cd 'C:/path', create folder 'test' in 'C:/path', list\n"
        "  batch on, zip 'C:/proj' to 'C:/Desktop', git update \"release\", batch off\n\n"

        "SHELL COMMAND TRANSLATIONS — never use the left column, always use the right:\n"
        "  mkdir        → create folder '<name>' in '<path>'\n"
        "  rm / del     → delete '<path>'\n"
        "  ls / dir     → list\n"
        "  cp           → copy '<src>' to '<dst>'\n"
        "  mv           → move '<src>' to '<dst>'\n"
        "  cat          → read '<file>'\n"
        "  touch        → create file '<name>' in '<path>'\n"
        "  grep         → search '<text>'\n\n"

        "--- Using your context ---\n\n"

        "The JSON block below gives you full session visibility:\n"
        "  last_issue   → the most recently failed/unknown command + its error.\n"
        "                 Diagnose from this immediately; never ask what happened.\n"
        "  macros       → full body of every saved macro.\n"
        "                 When a macro breaks, read its body, find the bad syntax, fix it.\n"
        "  recent_commands → every command typed this session.\n"
        "  folder_listing  → current directory contents.\n"
        "  aliases      → saved shortcuts.\n"
        "Never ask for information already present in this context.\n\n"

        "--- Output style ---\n\n"

        "Default: 2–4 lines, no preamble, no restating the question.\n"
        "Longer only when the user explicitly asks for explanation.\n"
        "Wrap all CMC commands in ```cmc blocks.\n"
        "When fixing a mistake: one corrected command, not a list of alternatives.\n\n"

        "Current CMC context (JSON):\n"
        f"{ctx}\n\n"
        "CMC manual — treat as ground truth for all available commands:\n"
        "----- BEGIN CMC_AI_Manual -----\n"
    )


def build_system_prompt(
    cwd: str,
    state: Dict[str, Any],
    macros: Dict[str, str],
    aliases: Optional[Dict[str, str]] = None,
) -> str:
    """
    Build the full system prompt for the active model.
    Large models (14b+) get a richer, more nuanced prefix.
    Small models (≤8b) get a terse, punchy prefix with explicit examples.
    """
    ctx    = build_context_blob(cwd, state, macros, aliases)
    manual = load_cmc_manual(_active_manual_path())

    prefix = (
        _build_prompt_prefix_large(ctx)
        if _is_large_model()
        else _build_prompt_prefix_small(ctx)
    )

    suffix = (
        "\n----- END CMC_AI_Manual -----\n\n"
        "SYNTAX RULES — apply these to every single response:\n"
        "  Paths  : single quotes + forward slashes  →  cd 'C:/Users/Name'\n"
        "  Chain  : comma only                       →  cmd1, cmd2, cmd3\n"
        "  Folder : create folder 'x' in 'y'         (never mkdir)\n"
        "  Shell commands (mkdir, &&, rm, dir) are forbidden — use CMC equivalents above.\n"
    )
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
    Passes the last command + issue to the AI and asks for a fix.
    Uses and updates conversation history so the user can follow up.
    """
    system_prompt = build_system_prompt(cwd, state, macros, aliases)

    if last_error == "Unknown command":
        issue_line = "Issue:   Not recognised by CMC (unknown command / possible typo)"
        question   = (
            "What did the user likely mean? "
            "Suggest the correct CMC command or syntax. Be brief."
        )
    else:
        issue_line = f"Error:   {last_error}"
        question   = "What went wrong and what is the correct CMC command to fix it? Be brief."

    fix_query = (
        f"The last CMC command had an issue.\n"
        f"Command: {last_cmd}\n"
        f"{issue_line}\n\n"
        f"{question}"
    )

    # Include conversation history so the user can ask follow-up questions
    messages: List[Dict[str, str]] = [
        {"role": "system", "content": system_prompt},
        *_HISTORY,
        {"role": "user", "content": fix_query},
    ]

    reply = _call_ai_backend(messages)

    # Store in history so follow-ups work ("ok how do I write it correctly?" etc.)
    _add_to_history("user", fix_query)
    _add_to_history("assistant", reply)

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
