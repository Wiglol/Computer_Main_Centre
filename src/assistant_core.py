"""
assistant_core.py — Embedded AI assistant integration for Computer Main Centre (CMC).

Supports multiple AI backends:
  • Ollama (local, default)       — http://localhost:11434/api/chat
  • Anthropic (Claude)            — https://api.anthropic.com/v1/messages
  • OpenAI (ChatGPT / Codex)      — https://api.openai.com/v1/chat/completions
                                    https://api.openai.com/v1/responses  (Codex only)
  • OpenRouter                    — https://openrouter.ai/api/v1/chat/completions

Active backend is stored in CMC_Config.json under ai.backend.
API keys are stored in ~/.ai_helper/api_keys.json (outside the repo).
Environment variables ANTHROPIC_API_KEY / OPENAI_API_KEY / OPENROUTER_API_KEY
take precedence over stored keys.

Public entry points used by Computer_Main_Centre.py:
    run_ai_assistant(user_query, cwd, state, macros, aliases) -> str
    run_ai_fix(last_cmd, last_error, cwd, state, macros, aliases) -> str
    clear_history() -> None

Key management (called by Computer_Main_Centre.py command handlers):
    get_api_key(backend) -> str | None
    set_api_key(backend, key) -> None
    clear_api_key(backend) -> None
    get_active_backend() -> str
    set_active_backend(backend) -> None
    resolve_model_name(name) -> str
    detect_backend_for_model(model) -> str
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
    """True for 14b+ Ollama models, or any cloud backend (always gets the full manual)."""
    if get_active_backend() != "ollama":
        return True
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

        "MACROS/ALIASES — the = sign is REQUIRED:\n"
        "  WRONG: macro add deploy batch on, git update \"ship\"\n"
        "  RIGHT: macro add deploy = batch on, git update \"ship\"\n"
        "  WRONG: alias add dl explore '%HOME%/Downloads'\n"
        "  RIGHT: alias add dl = explore '%HOME%/Downloads'\n\n"

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
    Prefix for large models (14b+) and all cloud backends.
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

        "MACROS & ALIASES — the = sign is mandatory:\n"
        "  macro add deploy = batch on, git update \"ship it\"\n"
        "  alias add dl = explore '%HOME%/Downloads'\n\n"

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
    Large models (14b+) and cloud backends get a richer, more nuanced prefix.
    Small Ollama models (≤8b) get a terse, punchy prefix with explicit examples.
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
        "  Macros : macro add name = cmd1, cmd2       (= sign is REQUIRED)\n"
        "  Aliases: alias add name = cmd              (= sign is REQUIRED)\n"
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
    """
    Choose the correct manual based on the active backend and model.

    Three tiers:
      LARGE  (AI_Manual.md)             — top-tier cloud: anthropic, openai, claude-code
      MEDIUM (CMC_AI_Manual_MEDIUM.md)  — openrouter + Ollama 14b/32b/70b/72b
      MINI   (CMC_AI_Manual_MINI.md)    — small Ollama models (≤8b)
    """
    here = Path(__file__).resolve().parent.parent
    manuals_dir = here / "manuals"

    backend = get_active_backend()

    if backend in ("anthropic", "openai", "claude-code"):
        name = "AI_Manual.md"
    elif backend == "openrouter":
        name = "CMC_AI_Manual_MEDIUM.md"
    else:
        # Ollama — pick by model size
        model = _get_active_model().lower()
        if any(x in model for x in ("14b", "32b", "72b", "70b")):
            name = "CMC_AI_Manual_MEDIUM.md"
        else:
            name = "CMC_AI_Manual_MINI.md"

    path = manuals_dir / name
    if path.exists():
        return path
    # Fallback: MEDIUM if LARGE is somehow missing
    fallback = manuals_dir / "CMC_AI_Manual_MEDIUM.md"
    return fallback if fallback.exists() else manuals_dir / "CMC_AI_Manual_MINI.md"


# ---------------------------------------------------------------------------
# API key storage  (~/.ai_helper/api_keys.json — outside the repo)
# ---------------------------------------------------------------------------

_KEYS_PATH = Path.home() / ".ai_helper" / "api_keys.json"

# Maps backend name → environment variable that overrides stored key
_ENV_KEY_MAP: Dict[str, str] = {
    "anthropic":  "ANTHROPIC_API_KEY",
    "openai":     "OPENAI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}


def _load_keys() -> Dict[str, str]:
    try:
        # Accept UTF-8 with/without BOM for compatibility with legacy setup writers.
        return json.loads(_KEYS_PATH.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def _save_keys(keys: Dict[str, str]) -> None:
    _KEYS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _KEYS_PATH.write_text(json.dumps(keys, indent=2), encoding="utf-8")


def get_api_key(backend: str) -> Optional[str]:
    """Return API key for *backend*. Env var takes precedence over stored key."""
    env_var = _ENV_KEY_MAP.get(backend)
    if env_var:
        val = os.getenv(env_var)
        if val:
            return val
    return _load_keys().get(backend) or None


def set_api_key(backend: str, key: str) -> None:
    """Store API key for *backend* in ~/.ai_helper/api_keys.json."""
    keys = _load_keys()
    keys[backend] = key
    _save_keys(keys)


def clear_api_key(backend: str) -> None:
    """Remove stored API key for *backend*."""
    keys = _load_keys()
    keys.pop(backend, None)
    _save_keys(keys)


# ---------------------------------------------------------------------------
# Backend selection + model aliases
# ---------------------------------------------------------------------------

VALID_BACKENDS = ("ollama", "anthropic", "openai", "openrouter", "claude-code")

# Claude Code CLI — known models with descriptions for the picker
CLAUDE_CODE_MODELS: List[tuple] = [
    ("claude-haiku-4-5",  "Haiku  — fastest & cheapest"),
    ("claude-sonnet-4-6", "Sonnet — balanced performance"),
    ("claude-opus-4-6",   "Opus   — most capable"),
]

# Friendly aliases → full model IDs
_MODEL_ALIASES: Dict[str, str] = {
    "claude-code":    "claude-code",       # uses local claude CLI — no API key needed
    "claude":         "claude-sonnet-4-6",
    "claude-sonnet":  "claude-sonnet-4-6",
    "claude-opus":    "claude-opus-4-6",
    "claude-haiku":   "claude-haiku-4-5",
    "chatgpt":        "gpt-5.2",
    "gpt":            "gpt-5.2",
    "gpt-5":          "gpt-5.2",
    "codex":          "gpt-5.3-codex",
}


def resolve_model_name(name: str) -> str:
    """Expand a friendly alias to the full model ID, or return name unchanged."""
    return _MODEL_ALIASES.get(name.lower(), name)


def detect_backend_for_model(model: str) -> str:
    """
    Guess the correct backend from a model name:
      claude-code           → claude-code  (local CLI, no API key needed)
      claude* / anthropic*  → anthropic
      gpt* / codex* / o1*   → openai
      contains '/'          → openrouter  (e.g. "meta-llama/llama-3.1-8b")
      anything else         → ollama
    """
    m = model.lower()
    if m == "claude-code":
        return "claude-code"
    if m.startswith(("claude", "anthropic")):
        return "anthropic"
    if m.startswith(("gpt", "codex", "o1-", "o3-", "o4-")):
        return "openai"
    if "/" in m:
        return "openrouter"
    return "ollama"


def get_active_backend() -> str:
    """Return the currently active backend (default: ollama)."""
    try:
        import CMC_Config
        cfg = CMC_Config.load_config()
        return cfg.get("ai", {}).get("backend", "ollama")
    except Exception:
        return "ollama"


def set_active_backend(backend: str) -> None:
    """Persist the chosen backend in CMC_Config.json."""
    try:
        import CMC_Config
        cfg = CMC_Config.load_config()
        cfg = CMC_Config.set_config_value(cfg, "ai.backend", backend)
        CMC_Config.save_config(cfg)
    except Exception:
        pass


def get_claude_code_model() -> str:
    """Return the specific Claude model to pass to claude CLI, or '' to use the CLI default."""
    try:
        import CMC_Config
        cfg = CMC_Config.load_config()
        return cfg.get("ai", {}).get("claude_code_model", "") or ""
    except Exception:
        return ""


def set_claude_code_model(model: str) -> None:
    """Persist which specific Claude model the claude-code backend should use."""
    try:
        import CMC_Config
        cfg = CMC_Config.load_config()
        cfg = CMC_Config.set_config_value(cfg, "ai.claude_code_model", model)
        CMC_Config.save_config(cfg)
    except Exception:
        pass


def get_backend_effort(backend: str) -> str:
    """
    Return the configured effort for a backend, or '' for provider default.
    Supported backends: claude-code, openai.
    """
    key_map = {
        "claude-code": "ai.claude_code_effort",
        "openai": "ai.openai_effort",
    }
    key = key_map.get((backend or "").lower())
    if not key:
        return ""
    try:
        import CMC_Config
        cfg = CMC_Config.load_config()
        return str(CMC_Config.get_config_value(cfg, key, "") or "").strip().lower()
    except Exception:
        return ""


def set_backend_effort(backend: str, effort: str) -> None:
    """Persist effort for a backend ('', low, medium, high)."""
    key_map = {
        "claude-code": "ai.claude_code_effort",
        "openai": "ai.openai_effort",
    }
    key = key_map.get((backend or "").lower())
    if not key:
        return
    eff = (effort or "").strip().lower()
    if eff and eff not in ("low", "medium", "high"):
        return
    try:
        import CMC_Config
        cfg = CMC_Config.load_config()
        cfg = CMC_Config.set_config_value(cfg, key, eff)
        CMC_Config.save_config(cfg)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------

def _http_post(url: str, headers: Dict[str, str], payload: Dict) -> Dict:
    """POST *payload* as JSON to *url*, return parsed response dict."""
    try:
        import requests  # type: ignore
    except ImportError:
        raise RuntimeError(
            "The 'requests' library is required.\n"
            "Run: pip install requests"
        )
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=120)
    except Exception as exc:
        raise RuntimeError(f"Network error contacting {url}:\n{exc}") from exc
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"HTTP {resp.status_code} from {url}:\n{resp.text[:600]}")
    try:
        return resp.json()
    except Exception as exc:
        raise RuntimeError(f"Invalid JSON from {url}: {resp.text[:400]}") from exc


# ---------------------------------------------------------------------------
# Backend callers
# ---------------------------------------------------------------------------

_OLLAMA_URL = os.getenv("CMC_AI_OLLAMA_URL", "http://localhost:11434/api/chat")


def _call_ollama(messages: List[Dict[str, str]]) -> str:
    """Call the local Ollama /api/chat endpoint."""
    try:
        import requests  # type: ignore
    except ImportError:
        raise RuntimeError(
            "The 'requests' library is required but is not installed.\n"
            "Run: pip install requests"
        )
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


def _call_anthropic(messages: List[Dict[str, str]]) -> str:
    """Call Anthropic /v1/messages API (Claude models)."""
    key = get_api_key("anthropic")
    if not key:
        raise RuntimeError(
            "No Anthropic API key configured.\n"
            "Run:  ai key set anthropic <your-key>\n"
            "Or set the ANTHROPIC_API_KEY environment variable."
        )
    # Anthropic requires system content as a separate top-level field
    system_parts: List[str] = []
    user_messages: List[Dict[str, str]] = []
    for m in messages:
        if m["role"] == "system":
            system_parts.append(m["content"])
        else:
            user_messages.append(m)

    headers = {
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload: Dict[str, Any] = {
        "model": _get_active_model(),
        "max_tokens": 4096,
        "messages": user_messages,
    }
    if system_parts:
        payload["system"] = "\n".join(system_parts)

    data = _http_post("https://api.anthropic.com/v1/messages", headers, payload)
    try:
        return data["content"][0]["text"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Unexpected Anthropic response shape: {data!r}") from exc


def _call_openai(messages: List[Dict[str, str]]) -> str:
    """Call OpenAI Chat Completions (or Responses API for Codex models)."""
    key = get_api_key("openai")
    if not key:
        raise RuntimeError(
            "No OpenAI API key configured.\n"
            "Run:  ai key set openai <your-key>\n"
            "Or set the OPENAI_API_KEY environment variable."
        )
    model = _get_active_model()
    headers = {
        "Authorization": f"Bearer {key}",
        "content-type": "application/json",
    }
    model_lc = model.lower()
    # Keep this conservative: only send effort for model families that support reasoning controls.
    supports_effort = ("codex" in model_lc) or model_lc.startswith(("gpt-5", "o1-", "o3-", "o4-"))
    effort = get_backend_effort("openai") if supports_effort else ""
    if effort not in ("low", "medium", "high"):
        effort = ""

    # Codex models use the Responses API
    if "codex" in model_lc:
        payload: Dict[str, Any] = {
            "model": model,
            "input": messages,
            "max_output_tokens": 4096,
        }
        if effort:
            payload["reasoning"] = {"effort": effort}
        data = _http_post("https://api.openai.com/v1/responses", headers, payload)
        try:
            return data["output"][0]["content"][0]["text"].strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"Unexpected OpenAI Responses API shape: {data!r}") from exc
    else:
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": 4096,
        }
        if effort:
            payload["reasoning_effort"] = effort
        data = _http_post("https://api.openai.com/v1/chat/completions", headers, payload)
        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"Unexpected OpenAI response shape: {data!r}") from exc


def _call_openrouter(messages: List[Dict[str, str]]) -> str:
    """Call OpenRouter's OpenAI-compatible endpoint."""
    key = get_api_key("openrouter")
    if not key:
        raise RuntimeError(
            "No OpenRouter API key configured.\n"
            "Run:  ai key set openrouter <your-key>\n"
            "Or set the OPENROUTER_API_KEY environment variable."
        )
    headers = {
        "Authorization": f"Bearer {key}",
        "content-type": "application/json",
        "HTTP-Referer": "https://github.com/Wiglol/Computer_Main_Centre",
        "X-Title": "CMC (Computer Main Centre)",
    }
    payload: Dict[str, Any] = {
        "model": _get_active_model(),
        "messages": messages,
        "max_tokens": 4096,
    }
    data = _http_post("https://openrouter.ai/api/v1/chat/completions", headers, payload)
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Unexpected OpenRouter response shape: {data!r}") from exc


def get_codex_auth_info() -> Dict[str, Any]:
    """
    Read Codex CLI auth.json and return info about how it is authenticated.
    Returns a dict with keys:
      "found"      : bool — whether any codex config was found
      "auth_mode"  : str  — e.g. "chatgpt", "api_key", or ""
      "api_key"    : str | None — the actual sk-... key if present
    """
    import re

    auth_path = Path.home() / ".codex" / "auth.json"
    if auth_path.exists():
        try:
            data = json.loads(auth_path.read_text(encoding="utf-8"))
            auth_mode = data.get("auth_mode", "")
            # Try to find a real sk-... API key
            api_key: Optional[str] = None
            for field in ("api_key", "openai_api_key", "OPENAI_API_KEY", "apiKey", "key"):
                val = data.get(field)
                if isinstance(val, str) and val.startswith("sk-"):
                    api_key = val
                    break
            return {"found": True, "auth_mode": auth_mode, "api_key": api_key}
        except Exception:
            pass

    # Fallback: check config.toml for an api_key line
    config_path = Path.home() / ".codex" / "config.toml"
    if config_path.exists():
        try:
            text = config_path.read_text(encoding="utf-8")
            match = re.search(r'api_key\s*=\s*["\']?(sk-[A-Za-z0-9\-_]+)["\']?', text)
            if match:
                return {"found": True, "auth_mode": "api_key", "api_key": match.group(1)}
        except Exception:
            pass

    return {"found": False, "auth_mode": "", "api_key": None}


def get_codex_api_key() -> Optional[str]:
    """
    Return the OpenAI API key from the Codex CLI config, or None.
    Only returns a key if one is actually stored (not subscription-based auth).
    """
    return get_codex_auth_info().get("api_key")


def _call_claude_code(messages: List[Dict[str, str]]) -> str:
    """
    Call Claude Code CLI as a subprocess using `claude -p`.
    Uses the user's existing Claude Code authentication — no API key needed.
    Passes the CMC system prompt using the best supported CLI flag.
    Conversation history is embedded in the user query text.

    Windows note: npm-installed tools like claude land as claude.cmd, which
    cannot be launched directly by subprocess — must go through cmd.exe /c.
    """
    import shutil
    import subprocess
    import sys as _sys
    import tempfile

    def _claude_help_text(claude_command: str) -> str:
        """Best-effort `claude --help` output; empty on failure."""
        try:
            if _sys.platform == "win32" and claude_command.lower().endswith((".cmd", ".bat")):
                help_args = ["cmd.exe", "/c", claude_command, "--help"]
            else:
                help_args = [claude_command, "--help"]
            help_result = subprocess.run(
                help_args,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=10,
            )
            return (help_result.stdout or help_result.stderr or "").lower()
        except Exception:
            return ""

    def _truncate_prompt_for_cli(system_text: str, max_chars: int = 12000) -> str:
        """
        Keep prompt size under command-line limits when passing as an argument.
        """
        if len(system_text) <= max_chars:
            return system_text
        tail_budget = 1800
        head_budget = max(1000, max_chars - tail_budget - 64)
        return (
            system_text[:head_budget]
            + "\n\n[... CMC manual truncated for CLI length ...]\n\n"
            + system_text[-tail_budget:]
        )

    # Find the claude executable (may be claude.cmd on Windows)
    claude_cmd = (
        shutil.which("claude")
        or shutil.which("claude.cmd")
        or shutil.which("claude.exe")
    )
    if not claude_cmd:
        raise RuntimeError(
            "Claude Code CLI ('claude') not found in PATH.\n"
            "Make sure Claude Code is installed and `claude` is accessible from the terminal."
        )

    # Separate system prompt from conversation messages
    system_parts: List[str] = []
    conversation: List[Dict[str, str]] = []
    for m in messages:
        if m["role"] == "system":
            system_parts.append(m["content"])
        else:
            conversation.append(m)

    # Build the query text — embed prior conversation so follow-ups work
    if len(conversation) > 1:
        history_lines: List[str] = []
        for m in conversation[:-1]:
            label = "User" if m["role"] == "user" else "Assistant"
            history_lines.append(f"[{label}]:\n{m['content']}")
        history_block = "\n\n".join(history_lines)
        current = conversation[-1]["content"] if conversation else ""
        user_query = (
            f"[PRIOR CONVERSATION — for context only]\n{history_block}\n\n"
            f"[CURRENT QUESTION]\n{current}"
        )
    else:
        user_query = conversation[-1]["content"] if conversation else ""

    system_text = "\n".join(system_parts)
    tmp_path: Optional[str] = None
    result = None
    try:
        help_text = _claude_help_text(claude_cmd)

        # Build base arguments.
        claude_args = ["-p", user_query, "--output-format", "text"]

        # Choose the best supported system-prompt method.
        # Priority: file (best for long prompts) -> append/system prompt arg.
        if "--system-prompt-file" in help_text:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", delete=False, encoding="utf-8"
            ) as tmp:
                tmp.write(system_text)
                tmp_path = tmp.name
            claude_args += ["--system-prompt-file", tmp_path]
        elif "--append-system-prompt" in help_text:
            claude_args += ["--append-system-prompt", _truncate_prompt_for_cli(system_text)]
        elif "--system-prompt" in help_text:
            claude_args += ["--system-prompt", _truncate_prompt_for_cli(system_text)]

        # Add specific model if configured (e.g. claude-haiku-4-5)
        cc_model = get_claude_code_model()
        if cc_model:
            claude_args += ["--model", cc_model]
        # Only pass effort if this CLI supports the flag.
        cc_effort = get_backend_effort("claude-code")
        if cc_effort in ("low", "medium", "high") and "--effort" in help_text:
            claude_args += ["--effort", cc_effort]

        # On Windows, .cmd and .bat files must be executed via cmd.exe /c
        # (subprocess cannot launch script files directly without shell=True)
        if _sys.platform == "win32" and claude_cmd.lower().endswith((".cmd", ".bat")):
            run_args = ["cmd.exe", "/c", claude_cmd] + claude_args
        else:
            run_args = [claude_cmd] + claude_args

        result = subprocess.run(
            run_args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=120,
        )
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    if result is None:
        raise RuntimeError("claude CLI could not be launched.")

    if result.returncode != 0:
        err = (result.stderr or result.stdout or "").strip()[:600]
        # Clear guidance when CLI flag support changed.
        if "system-prompt-file" in err.lower() or "unknown option" in err.lower() or "unrecognized" in err.lower():
            raise RuntimeError(
                "Your Claude Code CLI rejected an older system-prompt flag.\n"
                "CMC now supports modern flags; if this persists, run: npm update -g @anthropic-ai/claude-code\n"
                f"Details: {err}"
            )
        raise RuntimeError(
            f"claude CLI exited with code {result.returncode}.\n"
            f"Make sure you are logged in (run `claude` in your terminal to verify).\n"
            f"Details: {err}"
        )

    output = result.stdout.strip()
    if not output:
        raise RuntimeError(
            "claude CLI returned no output. "
            "Try running `claude -p \"hello\"` in your terminal to verify it works."
        )
    return output


def _call_ai_backend(messages: List[Dict[str, str]]) -> str:
    """Route to the correct backend based on ai.backend config."""
    backend = get_active_backend()
    if backend == "anthropic":
        return _call_anthropic(messages)
    elif backend == "openai":
        return _call_openai(messages)
    elif backend == "openrouter":
        return _call_openrouter(messages)
    elif backend == "claude-code":
        return _call_claude_code(messages)
    else:
        return _call_ollama(messages)


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

    backend = get_active_backend()
    model   = _get_active_model()
    print(f"assistant_core demo shell — backend: {backend}, model: {model}")
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
