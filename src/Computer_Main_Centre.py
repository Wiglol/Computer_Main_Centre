#!/usr/bin/env python3
# ---------- CMC hard-start globals ----------
import sys, re, pathlib, subprocess, importlib, platform
Path = pathlib.Path
globals()["Path"] = pathlib.Path

# Minimal global print wrapper; Rich can override later
def p(x):
    try:
        console = globals().get("console")
        if console:
            console.print(x)
            return
    except Exception:
        pass
    try:
        print(re.sub(r"\[/?[a-z]+\]", "", str(x)))
    except Exception:
        print(str(x))

# ---------- Dependency auto-check ----------
MIN_PY = (3, 10)
REQUIRED = ["rich", "requests", "pyautogui", "prompt_toolkit", "psutil"]

def safe_run(cmd):
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    except Exception:
        pass

def check_python_version():
    if sys.version_info < MIN_PY:
        p(f"⚠️  Python {MIN_PY[0]}.{MIN_PY[1]}+ recommended (current {platform.python_version()})")

def upgrade_pip():
    try:
        import pip
        major_minor = tuple(map(int, pip.__version__.split(".")[:2]))
        if major_minor < (23, 0):
            p("⬆️  Upgrading pip...")
            safe_run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
    except Exception:
        p("⚙️  Repairing pip...")
        safe_run([sys.executable, "-m", "ensurepip", "--upgrade"])
        safe_run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])

def ensure_packages():
    installed_any = False
    for pkg in REQUIRED:
        try:
            importlib.import_module(pkg)
        except ModuleNotFoundError:
            installed_any = True
            p(f"📦 Installing missing package: {pkg}")
            safe_run([sys.executable, "-m", "pip", "install", pkg, "--upgrade"])
    if installed_any:
        p("✅ All dependencies installed.\n")

check_python_version()
upgrade_pip()
ensure_packages()
# ---------- End of bootstrap ----------



# ==========================================================
#  Computer Main Centre  — Local AI Command Console
# ==========================================================

import os, sys, re, glob, fnmatch, shutil, zipfile, subprocess, datetime, time, json, threading
from pathlib import Path
from urllib.parse import urlparse
from CMC_Web_Create import op_web_create  # used by handle_new "web"
from CMC_Scaffold import (
    handle_setup, handle_new, handle_dev, handle_env,
)
import webbrowser, urllib.parse

# --- GitHub config path ---
GIT_CFG = Path.home() / ".ai_helper" / "github.json"
GIT_CFG.parent.mkdir(parents=True, exist_ok=True)


from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.styles import Style

try:
    import readline
except ImportError:
    try:
        import pyreadline3 as readline
    except ImportError:
        readline = None

# ---------- Optional dependencies ----------
RICH = False
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import (
        Progress, BarColumn, TextColumn, TimeRemainingColumn,
        DownloadColumn, TransferSpeedColumn
    )
    from rich.prompt import Confirm
    from rich.box import HEAVY
    RICH = True
    console = Console()
except Exception:
    class _Dummy:
        def print(self, *a, **k): print(*a)
    console = _Dummy()
    
    
    
def _start_bg_update_check():
    """
    Kick off a background thread that checks for CMC updates.
    Sets STATE["cmc_update_status"] when done.
    Uses CMC_Update.cmc_update_status_check() which works for both
    git clones and plain zip installs.
    """
    import threading

    def _worker():
        try:
            from CMC_Update import cmc_update_status_check
            # Root of CMC is one level up from src/
            cmc_root = Path(__file__).resolve().parent.parent
            result = cmc_update_status_check(cmc_root)
        except Exception:
            result = "unknown"
        STATE["cmc_update_status"] = result

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
        
        
        

_JAVA_DETECT_THREAD_STARTED = False

def _start_bg_java_detect(delay_seconds: float = 5.0):
    """
    Kick off delayed Java detection so CMC can render immediately.
    """
    global _JAVA_DETECT_THREAD_STARTED
    if _JAVA_DETECT_THREAD_STARTED:
        return
    _JAVA_DETECT_THREAD_STARTED = True

    if not STATE.get("java_version") or STATE.get("java_version") == "?":
        STATE["java_version"] = "checking..."

    def _worker():
        try:
            import time as _time
            _time.sleep(max(0.0, float(delay_seconds)))
            load_java_cfg(detect_live=True)
        except Exception:
            STATE["java_version"] = "?"

    t = threading.Thread(target=_worker, daemon=True)
    t.start()

# ---------- Safe Rich print wrapper (global early definition) ----------
def p(x):
    """Universal print wrapper for Rich and non-Rich output."""
    try:
        if "console" in globals() and globals().get("RICH", False):
            console.print(x)
        else:
            print(re.sub(r"\[/?[a-z]+\]", "", str(x)))
    except Exception:
        print(str(x))

HAVE_REQUESTS = False
try:
    import requests
    HAVE_REQUESTS = True
except Exception:
    pass
    
    
# Embedded AI assistant (optional)
HAVE_ASSISTANT = False
try:
    from assistant_core import run_ai_assistant, run_ai_fix, clear_history as ai_clear_history
    HAVE_ASSISTANT = True
except Exception:
    HAVE_ASSISTANT = False

# Track the last command + error for "ai fix"
_LAST_CMD: str = ""
_LAST_ERROR: str = ""


# ==========================================================
# 🔧  Computer Main Centre – Auto-Setup & Dependency Checker
# ==========================================================
import importlib, platform
MIN_PY = (3, 10)
REQUIRED = ["rich", "requests", "pyautogui", "prompt_toolkit", "psutil"]
...


# ---------- Global state ----------
HOME = Path.home()
CWD = Path.cwd()
STATE = {
    "batch": False,
    "dry_run": False,
    "ssl_verify": True,
    "history": [str(CWD)],
    "java_version": "?",
}

# --- Detect CMC update status in background (works for git clones + zip installs) ---
STATE["cmc_update_status"] = "checking"
_start_bg_update_check()

LOG = []    # list of strings



# ---------- Config (persistent settings) ----------
try:
    from CMC_Config import load_config, save_config, apply_config_to_state, get_config_value
except Exception:
    load_config = save_config = apply_config_to_state = None  # type: ignore
    def get_config_value(config, key, default=None): return default  # type: ignore

CONFIG = {}
try:
    if load_config is not None:
        CONFIG = load_config(Path(__file__).parent)
        apply_config_to_state(CONFIG, STATE)
except Exception:
    CONFIG = {}



# ---------- Java + Local Path Index Integration ----------

JAVA_VERSIONS = {
    "8":  r"C:\Program Files\Eclipse Adoptium\jdk-8.0.462.8-hotspot",
    "17": r"C:\Program Files\Eclipse Adoptium\jdk-17.0.16.8-hotspot",
    "21": r"C:\Program Files\Eclipse Adoptium\jdk-21.0.8.9-hotspot",
}

# Config directory (same as before)
CFG_DIR = Path(os.path.expandvars(r"%USERPROFILE%\\.ai_helper"))
CFG_DIR.mkdir(parents=True, exist_ok=True)
JAVA_CFG = CFG_DIR / "java.json"


# ---------- Apply Java Environment ----------
def _apply_java_env(java_home: str):
    if not java_home:
        return
    bin_path = str(Path(java_home) / "bin")
    os.environ["JAVA_HOME"] = java_home
    path = os.environ.get("PATH", "")
    parts = path.split(os.pathsep)
    # Remove old Java entries from PATH
    parts = [entry for entry in parts if entry and "Java" not in entry and "\\jdk-" not in entry and "/jdk-" not in entry]
    parts.insert(0, bin_path)
    os.environ["PATH"] = os.pathsep.join(parts)


# ---------- Java detection + config ----------
def detect_java_version() -> str:
    """Detects Java version from java -version, registry, or JAVA_HOME."""
    # Try java -version
    try:
        out = subprocess.check_output(["java", "-version"], stderr=subprocess.STDOUT, text=True, shell=True)
        m = re.search(r'version\s+"([^"]+)"', out)
        if not m:
            m = re.search(r"(\d+)", out)
        if m:
            full = m.group(1).strip()
            if full.startswith("1."):  # Java 8 format like "1.8.0_462"
                return full.split(".")[1]
            return full.split(".")[0]
    except Exception:
        pass

    # Try registry
    try:
        reg_out = subprocess.check_output('reg query "HKCU\\Environment" /v JAVA_HOME', shell=True, text=True, stderr=subprocess.DEVNULL)
        m2 = re.search(r"JAVA_HOME\s+REG_SZ\s+(.+)", reg_out)
        if m2:
            java_home = m2.group(1).strip()
            for ver in ("8", "17", "21"):
                if f"jdk-{ver}" in java_home or ver in java_home:
                    return ver
    except Exception:
        pass

    # Try environment variable
    java_home = os.environ.get("JAVA_HOME", "")
    if java_home:
        for ver in ("8", "17", "21"):
            if f"jdk-{ver}" in java_home or ver in java_home:
                return ver

    return "?"


def load_java_cfg(detect_live: bool = True):
    """Load persisted Java info or auto-detect + refresh environment."""
    ver = "?"
    home = None
    try:
        if JAVA_CFG.exists():
            data = json.loads(JAVA_CFG.read_text(encoding="utf-8"))
            ver = str(data.get("version", "?"))
            home = data.get("home", "")
            if home and Path(home).exists():
                _apply_java_env(home)
    except Exception:
        pass

    if detect_live:
        # Re-detect actual version live (can be delayed to avoid startup lag)
        detected = detect_java_version()
        if detected and detected != "?":
            ver = detected

    STATE["java_version"] = ver
    if home:
        os.environ["JAVA_HOME"] = home


def save_java_cfg(ver: str, home: str):
    """Save and immediately refresh Java version display."""
    try:
        JAVA_CFG.write_text(
            json.dumps({"version": ver, "home": home}, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        os.environ["JAVA_HOME"] = home
        _apply_java_env(home)
        STATE["java_version"] = detect_java_version()
    except Exception as e:
        print(f"[WARN] Could not save Java config: {e}")


# --- Auto-load + detect on startup ---
load_java_cfg(detect_live=False)




# ---------- Local Path Index (portable import) ----------
try:
    import runpy
    from pathlib import Path

    PATH_INDEX_LOCAL = Path(__file__).parent / "path_index_local.py"
    if not PATH_INDEX_LOCAL.exists():
        raise FileNotFoundError(f"Missing: {PATH_INDEX_LOCAL}")

    _mod_pathindex = runpy.run_path(str(PATH_INDEX_LOCAL))
    _qpaths  = _mod_pathindex.get("query_paths")
    _qcount  = _mod_pathindex.get("count_paths")
    _qbuild  = _mod_pathindex.get("rebuild_index")
    _DB_DEFAULT = _mod_pathindex.get("DEFAULT_DB")
except Exception as e:
    print(f"[WARN] Path-index module not loaded: {e}")
    _qpaths = _qcount = _qbuild = _DB_DEFAULT = None



UNDO = []  # stack of reversible actions
UNDO_MAX = 30  # maximum undo history depth

DATA_DIR = HOME / ".ai_helper"
DATA_DIR.mkdir(exist_ok=True)
TRASH_DIR = DATA_DIR / ".cmc_trash"   # temp holding area for undoable deletes
TRASH_DIR.mkdir(exist_ok=True)
MACROS_FILE = DATA_DIR / "macros.json"
if not MACROS_FILE.exists():
    MACROS_FILE.write_text("{}", encoding="utf-8")

# ---------- Aliases (persistent) ----------
ALIAS_FILE = Path(os.path.expanduser("~/.ai_helper/aliases.json"))
ALIASES = {}

def load_aliases():
    """Load alias list from ~/.ai_helper/aliases.json"""
    global ALIASES
    if ALIAS_FILE.exists():
        try:
            with open(ALIAS_FILE, "r", encoding="utf-8") as f:
                ALIASES = json.load(f)
        except Exception:
            ALIASES = {}
    else:
        ALIASES = {}

def save_aliases():
    """Save alias list"""
    ALIAS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(ALIAS_FILE, "w", encoding="utf-8") as f:
        json.dump(ALIASES, f, indent=2)

# ---------- Helpers ----------

def lc_size(n):
    try:
        n = int(n)
    except Exception:
        return "?"
    units = ["B","KB","MB","GB","TB"]
    i = 0
    while n >= 1024 and i < len(units)-1:
        n /= 1024.0; i += 1
    return f"{n:.2f} {units[i]}"

def resolve(path: str) -> Path:
    path = path.replace("\\", "/")
    if re.match(r"^[A-Za-z]:/", path):
        return Path(path)
    return (CWD / path).resolve()

def confirm(msg: str) -> bool:
    if STATE["batch"]:
        if RICH:
            p(f"[dim](auto)[/dim] {msg}")
        else:
            print(f"(auto) {msg}")
        return True
    if STATE["dry_run"]:
        p(f"[yellow]DRY-RUN {msg.splitlines()[0].lower()} ->[/yellow] {msg.splitlines()[-1]}")
        return False
    if RICH:
        console.print(Panel(msg, title="Confirm", border_style="cyan"))
        from rich.prompt import Prompt
        choice = Prompt.ask("Proceed? [y/n]", choices=["y","n"], default="y")
        return choice == "y"

    else:
        ans = input(f"{msg}\nProceed? (y/n): ").strip().lower()
        return ans.startswith("y")

def log_action(s: str):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    LOG.append(f"[{ts}] {s}")

def push_undo(kind, **kw):
    UNDO.append({"kind": kind, **kw})
    # Cap history so it doesn't grow unbounded
    if len(UNDO) > UNDO_MAX:
        UNDO.pop(0)


# ---------- Header ----------

def show_header():
    """
    Minimal cyan header — title, key flags, AI model, CMC status.
    SSL and Java are moved to the `status` command for a cleaner look.
    """
    ai_model = get_ai_model()
    ai_status = "[green]Ready[/green]" if HAVE_ASSISTANT else "[red]Not configured[/red]"

    batch_val = "[yellow]ON[/yellow]" if STATE["batch"] else "[dim]off[/dim]"
    dry_val   = "[yellow]ON[/yellow]" if STATE["dry_run"] else "[dim]off[/dim]"

    show_update = get_config_value(CONFIG, "header.show_update", True)

    upd = STATE.get("cmc_update_status", "unknown")
    if upd == "up_to_date":
        update_line = "[green]●[/green] CMC up to date"
    elif upd == "update_available":
        update_line = "[yellow]●[/yellow] [bold yellow]CMC update available[/bold yellow]  [dim]→ run:[/dim] [cyan]cmc update[/cyan]"
    elif upd == "diverged":
        update_line = "[red]●[/red] CMC has local changes"
    elif upd == "checking":
        update_line = "[dim]●[/dim] CMC checking..."
    else:
        update_line = "[dim]●[/dim] CMC status unknown"

    sep = "[dim] │ [/dim]"
    header_lines = [
        "[bold cyan]Computer Main Centre[/bold cyan]  [dim]— local command console[/dim]",
        f"[cyan]Batch:[/cyan] {batch_val}{sep}[cyan]Dry-Run:[/cyan] {dry_val}{sep}[cyan]AI:[/cyan] {ai_model} ({ai_status})",
    ]
    if show_update:
        header_lines.append(update_line)
    lines = header_lines
    content = "\n".join(lines)

    if RICH:
        console.print(Panel.fit(content, border_style="cyan", padding=(0, 2)))
    else:
        print("Computer Main Centre — local command console")
        print(f"Batch: {'ON' if STATE['batch'] else 'off'}  Dry-Run: {'ON' if STATE['dry_run'] else 'off'}  AI: {ai_model}")
        print(f"CMC: {upd}")

_FIRST_RUN_SENTINEL = DATA_DIR / ".cmc_first_run_done"

def is_first_run() -> bool:
    """Return True if this is the very first CMC launch (sentinel file absent)."""
    return not _FIRST_RUN_SENTINEL.exists()

def mark_first_run_done():
    """Write the sentinel so the first-run hint is never shown again."""
    try:
        _FIRST_RUN_SENTINEL.touch()
    except Exception:
        pass


def maybe_show_update_notes():
    """
    Shows UpdateNotes/LATEST.txt once per VERSION.txt (after an update).
    """
    try:
        base = Path(__file__).resolve().parent.parent
        notes_dir = base / "UpdateNotes"
        notes_file = notes_dir / "LATEST.txt"
        ver_file = notes_dir / "VERSION.txt"
        seen_file = notes_dir / "SEEN_VERSION.txt"

        if not notes_file.exists() or not ver_file.exists():
            return

        version = ver_file.read_text(encoding="utf-8", errors="ignore").strip()
        if not version:
            # Fallback: show once per *content*, not per file timestamp
            import hashlib
            data = notes_file.read_bytes()
            version = "notes-" + hashlib.sha1(data).hexdigest()[:10]



        seen = ""
        if seen_file.exists():
            seen = seen_file.read_text(encoding="utf-8", errors="ignore").strip()

        if seen == version:
            return  # already shown for this update

        text = notes_file.read_text(encoding="utf-8", errors="ignore").strip()
        if not text:
            # still mark as seen so it doesn't spam
            seen_file.write_text(version, encoding="utf-8")
            return

        title = "What's new in CMC"

        if RICH:
            console.print(Panel.fit(text, title=title, border_style="cyan"))
        else:
            print("\n" + "=" * 70)
            print(title)
            print("=" * 70)
            print(text)
            print("=" * 70 + "\n")

        # mark as shown
        notes_dir.mkdir(parents=True, exist_ok=True)
        seen_file.write_text(version, encoding="utf-8")

    except Exception:
        # Never block startup because of notes.
        return



def get_ai_model() -> str:
    # Prefer config value, then assistant_core runtime, then default
    try:
        m = (CONFIG or {}).get("ai", {}).get("model")
        if m:
            return str(m)
    except Exception:
        pass
    try:
        import assistant_core
        m = getattr(assistant_core, "_OLLAMA_MODEL", None)
        if m:
            return str(m)
    except Exception:
        pass
    return "llama3.1:8b"


def status_panel():
    """Full status panel — shown by the `status` command."""
    # ── Modes ──────────────────────────────────────────────────────────────
    batch_val = "[yellow]ON[/yellow]"  if STATE["batch"]       else "[green]off[/green]"
    dry_val   = "[yellow]ON[/yellow]"  if STATE["dry_run"]     else "[green]off[/green]"
    ssl_val   = "[green]ON[/green]"    if STATE["ssl_verify"]  else "[red]OFF[/red]"

    # ── AI ─────────────────────────────────────────────────────────────────
    ai_model  = get_ai_model()
    ai_status = "[green]Ready[/green]" if HAVE_ASSISTANT else "[red]Not configured[/red]"

    # ── Java ───────────────────────────────────────────────────────────────
    java_version = STATE.get("java_version") or "checking..."

    # ── CMC update ─────────────────────────────────────────────────────────
    upd = STATE.get("cmc_update_status", "unknown")
    if upd == "up_to_date":
        cmc_line = "[green]●[/green] Up to date"
    elif upd == "update_available":
        cmc_line = "[yellow]●[/yellow] Update available  [dim](run: cmc update)[/dim]"
    elif upd == "diverged":
        cmc_line = "[red]●[/red] Local changes detected"
    elif upd == "checking":
        cmc_line = "[dim]●[/dim] Checking for updates..."
    else:
        cmc_line = "[dim]●[/dim] Status unknown"

    # ── Macros / Aliases ───────────────────────────────────────────────────
    try:
        macro_count = len(macros_load())
    except Exception:
        macro_count = len(MACROS)
    alias_count = len(ALIASES)

    # ── Undo depth ─────────────────────────────────────────────────────────
    undo_depth = len(UNDO)

    # ── Assemble ───────────────────────────────────────────────────────────
    lines = [
        f"  [cyan]Batch:[/cyan]    {batch_val}",
        f"  [cyan]Dry-Run:[/cyan]  {dry_val}",
        f"  [cyan]SSL:[/cyan]      {ssl_val}",
        f"  [cyan]Undo:[/cyan]     {undo_depth}/{UNDO_MAX} steps",
        "",
        f"  [cyan]AI model:[/cyan] {ai_model} ({ai_status})",
        f"  [cyan]Java:[/cyan]     {java_version}",
        "",
        f"  [cyan]CMC:[/cyan]      {cmc_line}",
        f"  [cyan]Macros:[/cyan]   {macro_count}   [cyan]Aliases:[/cyan] {alias_count}",
    ]
    return "\n".join(lines)


def show_status_box():
    content = status_panel()
    if RICH:
        console.print(Panel(content, title="[bold cyan]Status[/bold cyan]", border_style="cyan", padding=(0, 1)))
    else:
        # Plain fallback
        batch = "ON" if STATE["batch"] else "off"
        dry   = "ON" if STATE["dry_run"] else "off"
        ssl   = "ON" if STATE["ssl_verify"] else "off"
        java_version = STATE.get("java_version") or "checking..."
        print(f"Batch: {batch}  Dry-Run: {dry}  SSL: {ssl}")
        print(f"AI: {get_ai_model()}  Java: {java_version}")
        upd = STATE.get("cmc_update_status", "unknown")
        print(f"CMC: {upd}  Macros: {len(MACROS)}  Aliases: {len(ALIASES)}")






# ---------- Navigation ----------
def op_pwd():
    p(str(CWD))

def op_cd(path):
    global CWD
    tgt = resolve(path)
    if tgt.exists() and tgt.is_dir():
        CWD = tgt
        STATE["history"].append(str(CWD))
    else:
        p(f"[red]❌ Not a directory:[/red] {tgt}" if RICH else f"Not a directory: {tgt}")

def op_back():
    hist = STATE["history"]
    if len(hist) >= 2:
        hist.pop()
        op_cd(hist[-1])
    else:
        p("[yellow]No previous directory.[/yellow]" if RICH else "No previous directory.")

def op_home():
    op_cd(str(HOME))

def op_list(path=None, depth=1, only=None, pattern=None):
    root = resolve(path) if path else CWD
    rows = []
    try:
        for base, dirs, files in os.walk(root):
            lvl = Path(base).relative_to(root).parts
            if len(lvl) > depth: continue
            if only in (None, "dirs"):
                for d in dirs:
                    full = str(Path(base)/d)
                    if pattern and not fnmatch.fnmatch(d, pattern): continue
                    rows.append((full, "dir"))
            if only in (None, "files"):
                for f in files:
                    full = str(Path(base)/f)
                    if pattern and not fnmatch.fnmatch(f, pattern): continue
                    rows.append((full, "file"))
        if RICH:
            t = Table(title=f"Listing: {root}")
            t.add_column("Path", overflow="fold")
            t.add_column("Type", width=6)
            for r in rows:
                t.add_row(*r)
            console.print(t)
        else:
            for r in rows:
                print(f"{r[0]}\t{r[1]}")
    except Exception as e:
        p(f"[red]❌ {e}[/red]" if RICH else f"Error: {e}")

# ---------- Search with progress ----------
def _walk_with_progress(root: Path):
    total_dirs = 0
    total_files = 0
    for _, dirs, files in os.walk(root):
        total_dirs += len(dirs)
        total_files += len(files)
    if RICH:
        prog = Progress(TextColumn("[progress.description]{task.description}"),
                        BarColumn(), TextColumn("{task.completed}/{task.total}"),
                        transient=True, console=console)
        task = None
        with prog:
            task = prog.add_task("Scanning", total=total_files or 1)
            for base, dirs, files in os.walk(root):
                for f in files:
                    prog.update(task, advance=1)
                    yield base, f
    else:
        scanned = 0
        for base, dirs, files in os.walk(root):
            for f in files:
                scanned += 1
                if scanned % 1000 == 0:
                    print(f"Scanning... {scanned} files")
                yield base, f

def find_name(name: str):
    root = CWD
    hits = []
    for base, f in _walk_with_progress(root):
        if name.lower() in f.lower():
            hits.append(str(Path(base)/f))
    show_hits(hits)

def find_ext(ext: str):
    if not ext.startswith("."): ext = "." + ext
    root = CWD
    hits = []
    for base, f in _walk_with_progress(root):
        if f.lower().endswith(ext.lower()):
            hits.append(str(Path(base)/f))
    show_hits(hits)

def recent_paths(path=None, limit=20):
    root = resolve(path) if path else CWD
    records = []
    for base, f in _walk_with_progress(root):
        fp = Path(base)/f
        try:
            m = fp.stat().st_mtime
            records.append((m, str(fp)))
        except Exception:
            pass
    records.sort(reverse=True)
    show_hits([b for _, b in records[:limit]])

def biggest_paths(path=None, limit=20):
    root = resolve(path) if path else CWD
    records = []
    for base, f in _walk_with_progress(root):
        fp = Path(base)/f
        try:
            s = fp.stat().st_size
            records.append((s, str(fp)))
        except Exception:
            pass
    records.sort(reverse=True)
    show_hits([b for _, b in records[:limit]], show_size=True)

def search_text(text: str):
    root = CWD
    hits = []
    for base, f in _walk_with_progress(root):
        fp = Path(base)/f
        try:
            if Path(f).suffix.lower() in (".txt",".md",".json",".cfg",".ini",".log",".xml",".py",".zs",".mcmeta",".properties"):
                s = (Path(base)/f).read_text(encoding="utf-8", errors="ignore")
                if text.lower() in s.lower():
                    hits.append(str(Path(base)/f))
        except Exception:
            pass
    show_hits(hits)

def show_hits(hits, show_size=False):
    if RICH:
        t = Table(title=f"Results ({len(hits)})")
        t.add_column("Path", overflow="fold")
        if show_size: t.add_column("Size", justify="right")
        for h in hits[:1000]:
            if show_size:
                try: t.add_row(h, lc_size(Path(h).stat().st_size))
                except Exception: t.add_row(h, "?")
            else:
                t.add_row(h)
        console.print(t)
    else:
        for h in hits:
            print(h)

# ---------- File ops ----------
def op_create_file(name, folder, text=None):
    tgt_folder = resolve(folder)
    tgt_folder.mkdir(parents=True, exist_ok=True)
    fp = tgt_folder / name
    msg = f"Create file:\n  {fp}" if text is None else f"Create file:\n  {fp}\nwith text ({len(text)} chars)"
    if confirm(msg):
        if STATE["dry_run"]:
            p(f"[yellow]DRY-RUN create file ->[/yellow] {fp}" if RICH else f"DRY-RUN create {fp}")
            return
        fp.write_text(text or "", encoding="utf-8")
        push_undo("create_file", path=str(fp))
        log_action(f"CREATED FILE {fp}")
        p(f"[green]✅ Created:[/green] {fp}" if RICH else f"Created: {fp}")

def op_create_folder(name, parent):
    par = resolve(parent)
    fp = par / name
    if confirm(f"Create folder:\n  {fp}"):
        if STATE["dry_run"]:
            p(f"[yellow]DRY-RUN create folder ->[/yellow] {fp}")
            return
        fp.mkdir(parents=True, exist_ok=True)
        push_undo("create_folder", path=str(fp))
        log_action(f"CREATED FOLDER {fp}")
        p(f"[green]✅ Created folder:[/green] {fp}")

def op_write(path, text):
    fp = resolve(path)
    if confirm(f"Write:\n  {fp}\n{text[:100]}..."):
        if STATE["dry_run"]:
            p(f"[yellow]DRY-RUN write ->[/yellow] {fp}")
            return
        # Save old content before overwriting
        existed = fp.exists()
        old_content = fp.read_text(encoding="utf-8", errors="replace") if existed else None
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(text, encoding="utf-8")
        push_undo("write", path=str(fp), old_content=old_content, existed=existed)
        log_action(f"WROTE {fp}")
        p(f"[green]✅ Written:[/green] {fp}")

def op_read(path, head=None):
    fp = resolve(path)
    if not fp.exists() or not fp.is_file():
        p(f"[red]❌ Not found:[/red] {fp}" if RICH else f"Not found: {fp}")
        return
    content = fp.read_text(encoding="utf-8", errors="replace")
    if head is not None:
        content = "\n".join(content.splitlines()[:head])
    if RICH:
        console.print(Panel(content, title=str(fp)))
    else:
        print(content)

def op_move(src, dst):
    s = resolve(src); d = resolve(dst)
    d.mkdir(parents=True, exist_ok=True)
    tgt = d / s.name
    if confirm(f"Move:\n  {s}\n→ {tgt}"):
        if STATE["dry_run"]:
            p(f"[yellow]DRY-RUN move ->[/yellow] {s} → {tgt}")
            return
        shutil.move(str(s), str(tgt))
        push_undo("move", src=str(tgt), dst=str(s))  # reverse
        log_action(f"MOVED {s} -> {tgt}")
        p("[green]✅ Moved[/green]" if RICH else "Moved")

def op_copy(src, dst):
    s = resolve(src); d = resolve(dst)
    if confirm(f"Copy:\n  {s}\n→ {d}"):
        if STATE["dry_run"]:
            p(f"[yellow]DRY-RUN copy ->[/yellow] {s} → {d}")
            return
        d.mkdir(parents=True, exist_ok=True)
        dest_path = d / s.name
        if s.is_dir():
            shutil.copytree(s, dest_path, dirs_exist_ok=True)
        else:
            shutil.copy2(s, d)
        push_undo("copy", dest=str(dest_path), is_dir=s.is_dir())
        log_action(f"COPIED {s} -> {d}")
        p(f"[green]✅ Copied to[/green] {d}" if RICH else f"Copied to {d}")

def op_rename(src, newname):
    s = resolve(src)
    t = s.parent / newname
    if confirm(f"Rename:\n  {s}\n→ {t}"):
        if STATE["dry_run"]:
            p(f"[yellow]DRY-RUN rename ->[/yellow] {s} → {t}")
            return
        os.rename(s, t)
        push_undo("rename", src=str(t), dst=str(s))  # reverse
        log_action(f"RENAMED {s} -> {t}")
        p("[green]✅ Renamed[/green]" if RICH else "Renamed")

def op_delete(path):
    s = resolve(path)
    if not s.exists():
        p(f"[red]❌ Not found:[/red] {s}")
        return
    if confirm(f"Delete:\n  {s}"):
        if STATE["dry_run"]:
            p(f"[yellow]DRY-RUN delete ->[/yellow] {s}")
            return
        # Move to trash instead of permanent delete — enables undo
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        trash_dest = TRASH_DIR / f"{ts}_{s.name}"
        shutil.move(str(s), str(trash_dest))
        push_undo("delete", original=str(s), trash=str(trash_dest), is_dir=s.is_dir())
        log_action(f"DELETED {s}")
        p(f"🗑️ Deleted {s}" + (" [dim](undo to restore)[/dim]" if RICH else " (type 'undo' to restore)"))

def _zip_dir_to(zf: zipfile.ZipFile, base: Path, root: Path):
    """Write all files under root to zf, with paths relative to base directory."""
    for r, dirs, files in os.walk(root):
        for f in files:
            fp = Path(r)/f
            zf.write(fp, fp.relative_to(base))

# ---------- Zip helper (supports optional destination) ----------
def op_zip(src, dest_folder=None):
    import zipfile, os
    from pathlib import Path

    src = Path(src)
    if dest_folder:
        dest_folder = Path(dest_folder)
    else:
        dest_folder = src.parent

    dest_folder.mkdir(parents=True, exist_ok=True)
    dest_file = dest_folder / f"{src.name}.zip"

    try:
        with zipfile.ZipFile(dest_file, "w", zipfile.ZIP_DEFLATED) as zf:
            if src.is_dir():
                for root, _, files in os.walk(src):
                    for f in files:
                        file_path = Path(root) / f
                        zf.write(file_path, file_path.relative_to(src))
            else:
                zf.write(src, src.name)
        p(f"[green bold]📦 Zipped {src} → {dest_file}[/green bold]")
    except Exception as e:
        p(f"[red]❌ Zip failed:[/red] {e}")


def op_unzip(zip_path, dest_folder):
    import zipfile
    from pathlib import Path
    zip_path = Path(zip_path)
    dest_folder = Path(dest_folder)
    dest_folder.mkdir(parents=True, exist_ok=True)

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(dest_folder)
        p(f"[green bold]📂 Unzipped {zip_path} → {dest_folder}[/green bold]")
    except Exception as e:
        p(f"[red]❌ Unzip failed:[/red] {e}")


def op_open(path):
    raw = path.strip().strip('"').strip("'")

    # ---------- URL handling ----------
    if raw.lower().startswith(("http://", "https://")):
        try:
            if not STATE["dry_run"]:
                import webbrowser
                webbrowser.open(raw)
                log_action(f"OPENED_URL {raw}")
                p(f"🌐 Opened: {raw}")
        except Exception as e:
            p(f"[red]❌ {e}[/red]" if RICH else f"Error: {e}")
        return

    # ---------- Local path handling ----------
    fp = resolve(raw)
    try:
        if not STATE["dry_run"]:
            os.startfile(str(fp))
            log_action(f"OPENED {fp}")
    except Exception as e:
        p(f"[red]❌ {e}[/red]" if RICH else f"Error: {e}")


def op_explore(path):
    fp = resolve(path)
    try:
        target = fp if fp.is_dir() else fp.parent
        if not STATE["dry_run"]:
            subprocess.Popen(["explorer", str(target)])
            log_action(f"EXPLORED {target}")
            p(f"📂 Explorer opened: {target}")
    except Exception as e:
        p(f"[red]❌ Error:[/red] {e}" if RICH else f"Error: {e}")

def op_backup(src, dest):
    # Create zip of src into dest/world_YYYY-MM-DD_HH-MM-SS.zip
    s = resolve(src); d = resolve(dest)
    ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    name = f"{s.name}_{ts}.zip" if s.is_dir() else f"{s.stem}_{ts}.zip"
    out = d / name
    if confirm(f"Backup (zip):\n  {s}\n→ {out}"):
        if STATE["dry_run"]:
            p(f"[yellow]DRY-RUN zip ->[/yellow] {out}")
            return
        d.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
            if s.is_dir():
                _zip_dir_to(zf, s.parent, s)
            else:
                zf.write(s, s.name)
        log_action(f"BACKUP_ZIP {s} -> {out}")
        p(f"[green]✅ Backup created:[/green] {out}")
        
        
        # ---------- System Info ----------
def op_sysinfo(save_path=None):
    import platform, psutil, subprocess
    info = {}
    try:
        info["OS"] = f"{platform.system()} {platform.release()} ({platform.version()})"
        info["CPU"] = platform.processor() or "Unknown"
        info["Cores"] = psutil.cpu_count(logical=True)
        info["RAM"] = f"{round(psutil.virtual_memory().total / (1024**3), 1)} GB"
        # GPU via wmic
        try:
            gpu_out = subprocess.check_output(
                "wmic path win32_VideoController get name", shell=True, text=True
            )
            gpus = [g.strip() for g in gpu_out.splitlines() if g.strip() and "Name" not in g]
            info["GPU"] = ", ".join(gpus) if gpus else "Unknown"
        except Exception:
            info["GPU"] = "Unknown"
        # PSU info (limited support)
        try:
            psu_out = subprocess.check_output(
                'powershell "Get-WmiObject Win32_PowerSupply | Select-Object Name,Manufacturer"',
                shell=True, text=True
            )
            psu_lines = [l.strip() for l in psu_out.splitlines() if l.strip()]
            info["PSU"] = "; ".join(psu_lines[2:]) if len(psu_lines) > 2 else "Unknown / No telemetry"
        except Exception:
            info["PSU"] = "Unknown / No telemetry"
        # Uptime
        info["Uptime"] = f"{round(time.time() - psutil.boot_time())/3600:.1f} h"
    except Exception as e:
        p(f"[red]❌ sysinfo failed:[/red] {e}")
        return

    text = "\n".join(f"{k}: {v}" for k, v in info.items())
    if save_path:
        Path(save_path).write_text(text, encoding="utf-8")
        p(f"[green]Saved system info →[/green] {save_path}")
    else:
        p(Panel(text, title="🧠 System Info", border_style="cyan") if RICH else text)

        
# ---------- Info / Find / Search ----------
def op_info(path):
    pth = resolve(path)
    if not pth.exists():
        p(f"[red]❌ Not found:[/red] {pth}")
        return
    typ = "dir" if pth.is_dir() else "file"
    size = pth.stat().st_size if pth.is_file() else sum(f.stat().st_size for f in pth.rglob('*') if f.is_file())
    mtime = datetime.datetime.fromtimestamp(pth.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    p(f"[cyan]ℹ️ Info:[/cyan] {pth}\n  Type: {typ}\n  Size: {size:,} bytes\n  Modified: {mtime}")

def op_recent(path=None):
    base = resolve(path or ".")
    items = sorted(base.rglob("*"), key=lambda f: f.stat().st_mtime, reverse=True)[:10]
    p(f"[cyan]🕓 Recent in {base}:[/cyan]")
    for f in items:
        t = datetime.datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        p(f"  {t}  {f}")

def op_biggest(path=None):
    base = resolve(path or ".")
    files = sorted([f for f in base.rglob("*") if f.is_file()], key=lambda f: f.stat().st_size, reverse=True)[:10]
    p(f"[cyan]📦 Largest files in {base}:[/cyan]")
    for f in files:
        p(f"  {f.stat().st_size/1024/1024:6.1f} MB  {f}")

def op_find_name(name):
    base = Path.cwd()
    results = [str(fp) for fp in base.rglob("*") if name.lower() in fp.name.lower()]
    if results:
        p(f"[cyan]🔎 Found {len(results)} match(es) for '{name}':[/cyan]")
        for r in results[:20]:
            p(f"  {r}")
        if len(results) > 20:
            p(f"[dim]...and {len(results) - 20} more.[/dim]")
    else:
        p(f"[yellow]No matches for '{name}'.[/yellow]")


def op_find_ext(ext):
    base = Path.cwd()
    results = [str(fp) for fp in base.rglob(f"*{ext}")]
    if results:
        p(f"[cyan]🔎 Files with {ext}:[/cyan]")
        for r in results[:20]:
            p(f"  {r}")
    else:
        p(f"[yellow]No *{ext} files found.[/yellow]")


def op_search_text(term):
    import pathlib
    base = resolve(".")  # respect CMC's virtual directory
    matches = []

    for fp in base.rglob("*"):
        if fp.is_file():
            try:
                txt = fp.read_text(errors="ignore")
                if term.lower() in txt.lower():
                    matches.append(str(fp))
                    if len(matches) >= 20:
                        break
            except Exception:
                continue

    if matches:
        p(f"[cyan]🧠 Found '{term}' in {len(matches)} file(s):[/cyan]")
        for m in matches:
            p(f"  {m}")
    else:
        p(f"[yellow]No text matches for '{term}'.[/yellow]")






def op_run(path):
    fp = resolve(path)
    if not fp.exists():
        p(f"[red]❌ Not found:[/red] {fp}" if RICH else f"Not found: {fp}")
        return
    if confirm(f"Run script:\n  {fp}"):
        if not STATE["dry_run"]:
            try:
                subprocess.Popen([sys.executable, str(fp)], cwd=str(fp.parent))
                log_action(f"RUN {fp}")
            except Exception as e:
                p(f"[red]❌ {e}[/red]" if RICH else f"Error: {e}")



# ---------- Web Project Setup Wizard ----------
def op_web_setup():
    """
    Web Project Setup Wizard (separate from normal projectsetup).

    Detects:
      - Static web (index.html)
      - React / Vue / Svelte / Next.js (via package.json)
      - Express backend (Node)
      - Flask / Django web projects (Python)
      - Fullstack (client/ + server/)

    Then suggests actions like:
      - npm install
      - create .gitignore
      - create README.md
      - create assets/ + preview script for static sites
      - create start scripts for Node / Python
      - git init

    All actions respect STATE["dry_run"] and Batch mode.
    """
    global CWD
    base = CWD

    try:
        files = [f for f in base.iterdir() if f.is_file()]
        dirs = [d for d in base.iterdir() if d.is_dir()]
    except Exception as e:
        p(f"[red]❌ Cannot scan folder for websetup:[/red] {e}")
        return

    file_names = [f.name for f in files]
    dir_names = [d.name for d in dirs]

    # ---------- helpers ----------
    def _read_small(fp: Path) -> str:
        try:
            return fp.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return ""

    def _load_package_json():
        if "package.json" not in file_names:
            return None, {}
        try:
            data = json.loads(_read_small(base / "package.json") or "{}")
            deps = {}
            deps.update(data.get("dependencies", {}) or {})
            deps.update(data.get("devDependencies", {}) or {})
            lower = {k.lower(): v for k, v in deps.items()}
            return data, lower
        except Exception:
            return None, {}

    pkg, deps = _load_package_json()

    # ---------- detection ----------
    is_static = any(fn.lower() in ("index.html", "index.htm") for fn in file_names)
    is_node = "package.json" in file_names
    has_node_modules = "node_modules" in dir_names

    is_react = "react" in deps or "react-dom" in deps
    is_next = "next" in deps
    is_vue = "vue" in deps
    is_svelte = "svelte" in deps or any(fn.lower().endswith(".svelte") for fn in file_names)

    # Express backend: deps or server.js/app.js
    is_express = (
        "express" in deps
        or any(fn.lower() in ("server.js", "app.js", "index.js") for fn in file_names)
    )

    # Python web: Flask / Django
    is_django = any(fn.lower() == "manage.py" for fn in file_names)
    is_flask = False
    if not is_django:
        for f in files:
            if f.suffix == ".py":
                s = _read_small(f)
                if "import flask" in s or "from flask" in s:
                    is_flask = True
                    break

    # Fullstack: client + server folders
    is_fullstack = "client" in dir_names and "server" in dir_names

    # ---------- label ----------
    project_type = "Unknown Web Project"
    if is_fullstack:
        project_type = "Fullstack Project (client + server)"
    elif is_next:
        project_type = "Next.js Project"
    elif is_react:
        project_type = "React Project"
    elif is_vue:
        project_type = "Vue Project"
    elif is_svelte:
        project_type = "Svelte Project"
    elif is_express and is_node:
        project_type = "Express (Node.js) Backend"
    elif is_django:
        project_type = "Django Web Project"
    elif is_flask:
        project_type = "Flask Web Project"
    elif is_static:
        project_type = "Web Project (Static HTML/CSS/JS)"
    elif is_node:
        project_type = "Node.js Web Project"

    # ---------- build actions ----------
    actions = []

    # Git
    has_git = (base / ".git").exists()
    if not has_git:
        actions.append({"id": "git_init", "label": "Initialize a new Git repository in this folder"})

    # Static web
    if is_static and not is_node:
        actions.append({"id": "web_gitignore", "label": "Create basic web .gitignore"})
        actions.append({"id": "web_readme", "label": "Create README.md for website"})
        actions.append({"id": "web_assets", "label": "Create assets/ folder and sample files"})
        actions.append({"id": "web_preview", "label": "Create simple local preview script (python http.server)"})

    # Frontend frameworks
    if is_node and (is_react or is_vue or is_svelte or is_next):
        if not has_node_modules:
            actions.append({"id": "npm_install", "label": "Run 'npm install' to restore dependencies"})
        actions.append({"id": "web_gitignore", "label": "Create framework .gitignore"})
        actions.append({"id": "web_readme", "label": "Create README.md for this project"})

    # Express backend
    if is_express:
        if not has_node_modules:
            actions.append({"id": "npm_install", "label": "Run 'npm install' for backend"})
        actions.append({"id": "node_start", "label": "Create start_server.bat for Node backend"})

    # Python web (Flask/Django)
    is_python_web = is_flask or is_django
    if is_python_web:
        has_venv = (base / "venv").exists() or (base / ".venv").exists()
        has_requirements = (base / "requirements.txt").exists()
        if not has_venv:
            actions.append({"id": "py_venv", "label": "Create Python virtual environment (venv)"})
        if has_requirements:
            actions.append({"id": "py_install_reqs", "label": "Install dependencies from requirements.txt"})
        else:
            actions.append({"id": "py_gen_reqs", "label": "Generate requirements.txt from current environment"})
        actions.append({"id": "py_start", "label": "Create start_server.bat for Python web app"})

    # Fullstack convenience
    if is_fullstack:
        actions.append({"id": "fullstack_install", "label": "Install client + server dependencies"})

    # README for any web project if missing
    if not (base / "README.md").exists():
        actions.append({"id": "web_readme", "label": "Create README.md for this project"})

    # If nothing to do:
    if not actions:
        msg = f"[bold cyan]Web Project Setup Wizard[/bold cyan]\n\nNo recommended actions.\nDetected web type: {project_type}"
        if RICH:
            console.print(Panel(msg, title="🌐 Web Setup", border_style="cyan"))
        else:
            print(msg)
        return

    # ---------- build wizard text ----------
    lines = [
        "[bold cyan]Web Project Setup Wizard[/bold cyan]",
        f"Detected project type: [green]{project_type}[/green]",
        "",
        "Recommended actions:"
    ]
    for i, a in enumerate(actions, 1):
        lines.append(f"  [{i}] {a['label']}")
    lines.append("")
    lines.append("Apply all recommended actions?")

    msg = "\n".join(lines)

    # ---------- ask: apply all? ----------
    if STATE.get("batch"):
        apply_all = True
    else:
        if RICH:
            console.print(Panel(msg, title="🌐 Web Setup", border_style="cyan"))
            from rich.prompt import Confirm
            apply_all = Confirm.ask("Apply all recommended actions?", default=True)
        else:
            print(msg)
            ans = input("Apply all? (Y/n): ").strip().lower()
            apply_all = ans in ("", "y", "yes")

    # ---------- action executors ----------
    def run_action(a):
        aid = a["id"]
        try:
            # Git init
            if aid == "git_init":
                if (base / ".git").exists():
                    p("• Git repo already exists, skipping git init.")
                    return
                if STATE["dry_run"]:
                    p("[yellow]DRY-RUN would run 'git init'[/yellow]")
                    return
                p("→ Initializing Git repository ...")
                subprocess.run(["git", "init"], cwd=str(base), check=True)
                p("  ✔ Git repository initialized")
                return

            # npm install
            if aid == "npm_install":
                if STATE["dry_run"]:
                    p("[yellow]DRY-RUN would run 'npm install'[/yellow]")
                    return
                p("→ Running 'npm install' ...")
                try:
                    subprocess.run(["npm", "install"], cwd=str(base), check=True)
                    p("  ✔ npm install completed")
                except FileNotFoundError:
                    p("[red]❌ npm not found on PATH[/red]")
                return

            # web .gitignore
            if aid == "web_gitignore":
                gi = base / ".gitignore"
                if gi.exists():
                    p("• .gitignore already exists, skipping.")
                    return
                content = "\n".join([
                    "node_modules/",
                    "dist/",
                    "build/",
                    ".env",
                    ".DS_Store",
                    "__pycache__/",
                    "*.log",
                ]) + "\n"
                if STATE["dry_run"]:
                    p("[yellow]DRY-RUN would create .gitignore[/yellow]")
                else:
                    gi.write_text(content, encoding="utf-8")
                    p("  ✔ .gitignore created")
                return

            # README
            if aid == "web_readme":
                fp = base / "README.md"
                if fp.exists():
                    p("• README.md already exists, skipping.")
                    return
                text = f"# {base.name}\n\nAuto-generated by CMC Web Setup.\n\nType: {project_type}\n"
                if STATE["dry_run"]:
                    p("[yellow]DRY-RUN would create README.md[/yellow]")
                else:
                    fp.write_text(text, encoding="utf-8")
                    p("  ✔ README.md created")
                return

            # assets
            if aid == "web_assets":
                folder = base / "assets"
                if folder.exists():
                    p("• assets/ already exists, skipping.")
                    return
                if STATE["dry_run"]:
                    p("[yellow]DRY-RUN would create assets/ folder[/yellow]")
                else:
                    folder.mkdir(parents=True, exist_ok=True)
                    (folder / "sample.txt").write_text("Assets folder", encoding="utf-8")
                    p("  ✔ assets/ folder created")
                return

            # preview script for static sites
            if aid == "web_preview":
                if os.name == "nt":
                    out = base / "preview_server.bat"
                    content = "@echo off\npython -m http.server 8000\npause\n"
                else:
                    out = base / "preview_server.sh"
                    content = "#!/bin/sh\npython3 -m http.server 8000\n"
                if out.exists():
                    p("• Preview script already exists, skipping.")
                    return
                if STATE["dry_run"]:
                    p(f"[yellow]DRY-RUN would create preview script {out.name}[/yellow]")
                else:
                    out.write_text(content, encoding="utf-8")
                    try:
                        out.chmod(0o755)
                    except Exception:
                        pass
                    p(f"  ✔ Preview script created: {out.name}")
                return

            # Node backend start script
            if aid == "node_start":
                script = base / "start_server.bat"
                if script.exists():
                    p("• start_server.bat already exists, skipping.")
                    return
                entry = None
                for name in ("server.js", "app.js", "index.js"):
                    if (base / name).exists():
                        entry = name
                        break
                if not entry:
                    p("[yellow]No server.js/app.js/index.js found, skipping start script.[/yellow]")
                    return
                content = f"@echo off\nnode {entry}\npause\n"
                if STATE["dry_run"]:
                    p("[yellow]DRY-RUN would create Node start_server.bat[/yellow]")
                else:
                    script.write_text(content, encoding="utf-8")
                    p("  ✔ Node start script created (start_server.bat)")
                return

            # Python venv
            if aid == "py_venv":
                target = base / "venv"
                if target.exists():
                    p("• venv already exists, skipping.")
                    return
                if STATE["dry_run"]:
                    p(f"[yellow]DRY-RUN would create venv at {target}[/yellow]")
                else:
                    p(f"→ Creating venv at {target} ...")
                    subprocess.run([sys.executable, "-m", "venv", str(target)], cwd=str(base), check=True)
                    p("  ✔ venv created")
                return

            # pip install -r requirements
            if aid == "py_install_reqs":
                req = base / "requirements.txt"
                if not req.exists():
                    p("[yellow]requirements.txt not found, skipping install.[/yellow]")
                    return
                if STATE["dry_run"]:
                    p("[yellow]DRY-RUN would install from requirements.txt[/yellow]")
                else:
                    p(f"→ Installing from {req} ...")
                    subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(req)], cwd=str(base), check=True)
                    p("  ✔ dependencies installed")
                return

            # generate requirements.txt
            if aid == "py_gen_reqs":
                if STATE["dry_run"]:
                    p("[yellow]DRY-RUN would generate requirements.txt[/yellow]")
                else:
                    p("→ Generating requirements.txt from current environment ...")
                    res = subprocess.run([sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True)
                    if res.returncode != 0:
                        p(f"[red]❌ pip freeze failed:[/red] {res.stderr.strip()}")
                    else:
                        (base / "requirements.txt").write_text(res.stdout, encoding="utf-8")
                        p("  ✔ requirements.txt written")
                return

            # Python start script
            if aid == "py_start":
                script = base / "start_server.bat"
                if script.exists():
                    p("• start_server.bat already exists, skipping.")
                    return
                candidate = None
                for name in ("app.py", "main.py", "wsgi.py"):
                    if (base / name).exists():
                        candidate = name
                        break
                if not candidate:
                    p("[yellow]No Python entrypoint (app.py/main.py/wsgi.py), skipping start script.[/yellow]")
                    return
                content = f"@echo off\n{sys.executable} {candidate}\npause\n"
                if STATE["dry_run"]:
                    p("[yellow]DRY-RUN would create Python start_server.bat[/yellow]")
                else:
                    script.write_text(content, encoding="utf-8")
                    p("  ✔ Python start script created (start_server.bat)")
                return

            # fullstack install
            if aid == "fullstack_install":
                cdir = base / "client"
                sdir = base / "server"
                if cdir.exists() and (cdir / "package.json").exists():
                    p("→ Installing client dependencies (npm install in client/) ...")
                    try:
                        subprocess.run(["npm", "install"], cwd=str(cdir), check=True)
                        p("  ✔ client deps installed")
                    except Exception as e:
                        p(f"[red]❌ client npm install failed:[/red] {e}")
                if sdir.exists():
                    if (sdir / "package.json").exists():
                        p("→ Installing server Node deps (npm install in server/) ...")
                        try:
                            subprocess.run(["npm", "install"], cwd=str(sdir), check=True)
                            p("  ✔ server Node deps installed")
                        except Exception as e:
                            p(f"[red]❌ server npm install failed:[/red] {e}")
                    elif (sdir / "requirements.txt").exists():
                        p("→ Installing server Python deps (pip install -r requirements.txt) ...")
                        try:
                            subprocess.run(
                                [sys.executable, "-m", "pip", "install", "-r", str(sdir / "requirements.txt")],
                                cwd=str(sdir),
                                check=True,
                            )
                            p("  ✔ server Python deps installed")
                        except Exception as e:
                            p(f"[red]❌ server pip install failed:[/red] {e}")
                return

        except Exception as e:
            p(f"[red]❌ Web setup action failed ({aid}):[/red] {e}")

    # ---------- run actions ----------
    if apply_all:
        for a in actions:
            run_action(a)
    else:
        for a in actions:
            label = a["label"]
            if STATE.get("batch"):
                do_it = True
            else:
                if RICH:
                    from rich.prompt import Prompt
                    choice = Prompt.ask(f"{label}? [y/n]", choices=["y", "n"], default="y")
                    do_it = choice == "y"
                else:
                    ans = input(f"{label}? (Y/n): ").strip().lower()
                    do_it = ans in ("", "y", "yes")
            if do_it:
                run_action(a)

    # Final small summary
    summary = "[bold cyan]Web setup complete.[/bold cyan]"
    if RICH:
        console.print(Panel(summary, title="🌐 Web Setup", border_style="cyan"))
    else:
        print("Web setup complete.")




def _format_state_flag(label: str, before, after, true_label="Present", false_label="Missing", na_label="N/A"):
    def fmt(x):
        if x is None:
            return na_label
        return true_label if x else false_label
    if before == after:
        return None
    return f"{label}: {fmt(before)} → {fmt(after)}"
    
    

def _detect_project_for_setup(base: Path):
    """
    Detect project type and return a dict with keys that the projectsetup
    wizard expects:

        {
          "project_type": str,
          "is_python": bool,
          "is_node": bool,
          "is_minecraft": bool,
          "has_venv": bool,
          "has_requirements": bool,
          "has_node_modules": bool,
          "has_git": bool,
          "required_java": int | None,
          "java_ok": bool,
        }
    """
    try:
        files = [f for f in base.iterdir() if f.is_file()]
        dirs = [d for d in base.iterdir() if d.is_dir()]
    except Exception:
        files, dirs = [], []

    file_names = [f.name for f in files]
    dir_names = [d.name for d in dirs]

    # ---------- Python detection ----------
    is_python = (
        "main.py" in file_names
        or "requirements.txt" in file_names
        or any(f.suffix == ".py" for f in files)
    )
    has_venv = (base / "venv").exists() or (base / ".venv").exists()
    has_requirements = (base / "requirements.txt").exists()

    # ---------- Node / frontend detection ----------
    is_node = "package.json" in file_names
    has_node_modules = "node_modules" in dir_names

    # ---------- Minecraft server detection ----------
    mc_jar = None
    for name in file_names:
        lower = name.lower()
        if lower.endswith(".jar") and any(
            tag in lower for tag in ("server", "forge", "paper", "fabric", "purpur", "spigot", "bukkit")
        ):
            mc_jar = name
            break

    is_minecraft = mc_jar is not None
    required_java = None
    java_ok = True

    if is_minecraft:
        # Try to infer Minecraft version from jar name
        mc_version = "Unknown"
        m = re.search(r"(\d+\.\d+(?:\.\d+)?)", mc_jar)
        if m:
            mc_version = m.group(1)

        try:
            parts = mc_version.split(".")
            major = int(parts[0]) if len(parts) > 0 else 0
            minor = int(parts[1]) if len(parts) > 1 else 0
            key = (major, minor)

            # Simple mapping: same as in project scan
            if key < (1, 17):
                required_java = 8
            elif key < (1, 18):
                required_java = 16
            elif key < (1, 20):
                required_java = 17
            else:
                required_java = 21
        except Exception:
            required_java = None

        active_java = STATE.get("java_version", "?")
        if required_java and active_java != "?":
            java_ok = str(required_java) in str(active_java)
        else:
            java_ok = True

    # ---------- Git detection ----------
    has_git = (base / ".git").exists()

    # ---------- Project type label ----------
    project_type = "Unknown"
    if is_minecraft:
        project_type = "Minecraft Server"
    elif is_node:
        project_type = "Node.js Project"
    elif is_python:
        project_type = "Python Project"

    return {
        "project_type": project_type,
        "is_python": is_python,
        "is_node": is_node,
        "is_minecraft": is_minecraft,
        "has_venv": has_venv,
        "has_requirements": has_requirements,
        "has_node_modules": has_node_modules,
        "has_git": has_git,
        "required_java": required_java,
        "java_ok": java_ok,
    }

    


def op_project_setup():
    """
    Project Setup Wizard:
      - Detect project type
      - Recommend actions (Python / Node / MC / Unity / Java / Web / Git)
      - Optionally apply all automatically or ask per-action
      - Show BEFORE → AFTER summary using a second detection pass
    """
    global CWD
    base = CWD

    # We'll also need the current file list for some actions (e.g. MC start script)
    try:
        files = [f for f in base.iterdir() if f.is_file()]
    except Exception:
        files = []
    file_names = [f.name for f in files]

    before = _detect_project_for_setup(base)
    project_type = before["project_type"]

    actions = []

    # Python actions
    if before["is_python"]:
        if not before["has_venv"]:
            actions.append({
                "id": "py_venv",
                "label": "Create Python virtual environment (venv)"
            })
        if before["has_requirements"]:
            actions.append({
                "id": "py_install_reqs",
                "label": "Install dependencies from requirements.txt"
            })
        else:
            actions.append({
                "id": "py_generate_reqs",
                "label": "Generate requirements.txt from current environment"
            })

    # Node.js actions
    if before["is_node"]:
        if not before["has_node_modules"]:
            actions.append({
                "id": "node_npm_install",
                "label": "Run 'npm install' to restore dependencies"
            })
        # basic gitignore for Node projects
        if not (base / ".gitignore").exists():
            actions.append({
                "id": "node_gitignore",
                "label": "Create a basic .gitignore for Node projects"
            })

    # Minecraft actions
    if before["is_minecraft"]:
        if before["required_java"] is not None and not before["java_ok"]:
            actions.append({
                "id": "mc_switch_java",
                "label": f"Switch Java to {before['required_java']} for this Minecraft server",
                "java_version": before["required_java"],
            })
        # simple start script helper for Windows
        has_start_script = any(
            fn.lower().endswith((".bat", ".cmd")) and "start" in fn.lower()
            for fn in file_names
        )
        if not has_start_script:
            actions.append({
                "id": "mc_start_script",
                "label": "Create a basic Windows start script for this server (start_server.bat)"
            })

    # Generic Git action
    if not before["has_git"]:
        actions.append({
            "id": "git_init",
            "label": "Initialize a new Git repository in this folder"
        })

    # If no actions detected
    if not actions:
        msg = f"[bold cyan]Project Setup Wizard[/bold cyan]\n\nNo recommended setup actions for this folder.\nDetected type: {project_type}"
        if RICH:
            console.print(Panel(msg, title="🧙 Project Setup", border_style="cyan"))
        else:
            print(msg)
        return

    # Build recommendation text
    lines_txt = [
        "[bold cyan]Project Setup Wizard[/bold cyan]",
        f"Detected project type: [green]{project_type}[/green]",
        "",
        "Recommended actions:"
    ]
    for idx, act in enumerate(actions, start=1):
        lines_txt.append(f"  [{idx}] {act['label']}")
    lines_txt.append("")
    lines_txt.append("Apply all recommended actions?")

    msg = "\n".join(lines_txt)

    # Ask: apply all or manual?
    apply_all = False
    if STATE["batch"]:
        apply_all = True
    else:
        if RICH:
            console.print(Panel(msg, title="🧙 Project Setup", border_style="cyan"))
            from rich.prompt import Confirm
            apply_all = Confirm.ask("Apply all recommended actions?", default=True)
        else:
            print(msg)
            ans = input("Apply all? (Y/n): ").strip().lower()
            apply_all = (ans in ("", "y", "yes"))



    # Execute actions
    def run_action(act):
        aid = act["id"]
        try:
            if aid == "py_venv":
                target = (base / "venv")
                if STATE["dry_run"]:
                    p(f"[yellow]DRY-RUN would create venv at:[/yellow] {target}")
                else:
                    p(f"→ Creating virtual environment at {target} ...")
                    import subprocess as _sp
                    _sp.run([sys.executable, "-m", "venv", str(target)], cwd=str(base), check=True)
                    p("  ✔ venv created")

            elif aid == "py_install_reqs":
                req = base / "requirements.txt"
                if not req.exists():
                    p(f"[yellow]requirements.txt not found at {req}[/yellow]")
                else:
                    if STATE["dry_run"]:
                        p(f"[yellow]DRY-RUN would install dependencies from:[/yellow] {req}")
                    else:
                        p(f"→ Installing dependencies from {req} ...")
                        import subprocess as _sp
                        _sp.run([sys.executable, "-m", "pip", "install", "-r", str(req)],
                                cwd=str(base), check=True)
                        p("  ✔ Dependencies installed")

            elif aid == "py_generate_reqs":
                if STATE["dry_run"]:
                    p(f"[yellow]DRY-RUN would generate requirements.txt[/yellow]")
                else:
                    p("→ Generating requirements.txt from current environment ...")
                    import subprocess as _sp
                    result = _sp.run([sys.executable, "-m", "pip", "freeze"],
                                     capture_output=True, text=True)
                    if result.returncode != 0:
                        p(f"[red]❌ pip freeze failed:[/red] {result.stderr.strip()}")
                    else:
                        (base / "requirements.txt").write_text(result.stdout, encoding="utf-8")
                        p(f"  ✔ requirements.txt written at {base / 'requirements.txt'}")

            elif aid == "node_npm_install":
                if STATE["dry_run"]:
                    p(f"[yellow]DRY-RUN would run 'npm install'[/yellow]")
                else:
                    p("→ Running 'npm install' ...")
                    import subprocess as _sp
                    try:
                        _sp.run(["npm", "install"], cwd=str(base), check=True)
                        p("  ✔ npm install completed")
                    except FileNotFoundError:
                        p("[red]❌ npm not found on PATH[/red]")

            elif aid == "node_gitignore":
                gitignore = base / ".gitignore"
                if gitignore.exists():
                    p("• .gitignore already exists, skipping.")
                else:
                    contents = "\n".join([
                        "node_modules/",
                        "npm-debug.log",
                        "yarn-error.log",
                        "dist/",
                        "build/",
                    ]) + "\n"
                    if STATE["dry_run"]:
                        p(f"[yellow]DRY-RUN would create .gitignore with Node patterns[/yellow]")
                    else:
                        gitignore.write_text(contents, encoding="utf-8")
                        p("  ✔ .gitignore created for Node project")

            elif aid == "mc_switch_java":
                ver = str(act.get("java_version", ""))
                if not ver:
                    p("[yellow]No required Java version computed, skipping Java switch.[/yellow]")
                else:
                    if STATE["dry_run"]:
                        p(f"[yellow]DRY-RUN would run: java change {ver}[/yellow]")
                    else:
                        p(f"→ Switching Java to {ver} via 'java change' ...")
                        handle_command(f"java change {ver}")

            elif aid == "mc_start_script":
                script = base / "start_server.bat"
                if script.exists():
                    p("• start_server.bat already exists, skipping.")
                else:
                    jar_name = None
                    for name in file_names:
                        if name.lower().endswith(".jar"):
                            jar_name = name
                            break
                    if not jar_name:
                        p("[yellow]No server jar found to create start script.[/yellow]")
                    else:
                        contents = (
                            "@echo off\n"
                            f"java -Xmx4G -Xms1G -jar \"{jar_name}\" nogui\n"
                            "pause\n"
                        )
                        if STATE["dry_run"]:
                            p(f"[yellow]DRY-RUN would create start_server.bat[/yellow]")
                        else:
                            script.write_text(contents, encoding="utf-8")
                            p("  ✔ start_server.bat created")

            elif aid == "git_init":
                if (base / ".git").exists():
                    p("• Git repository already exists, skipping git init.")
                else:
                    if STATE["dry_run"]:
                        p(f"[yellow]DRY-RUN would run: git init[/yellow]")
                    else:
                        p("→ Initializing Git repository ...")
                        try:
                            _git_run("git init", cwd=str(base))
                            p("  ✔ Git repository initialized")
                        except Exception as e:
                            p(f"[red]❌ git init failed:[/red] {e}")

        except Exception as e:
            p(f"[red]❌ Setup action failed ({aid}):[/red] {e}")

    # Run actions based on mode
    if apply_all:
        for act in actions:
            run_action(act)
    else:
        # Manual mode: ask for each action
        for act in actions:
            label = act["label"]
            if STATE["batch"]:
                do_it = True
            else:
                if RICH:
                    from rich.prompt import Confirm as _Confirm
                    do_it = _Confirm.ask(f"{label}?", default=True)
                else:
                    ans = input(f"{label}? (Y/n): ").strip().lower()
                    do_it = (ans in ("", "y", "yes"))
            if do_it:
                run_action(act)

    # AFTER state: re-scan and show summary
    after = _detect_project_for_setup(base)

    summary_lines = ["[bold cyan]Setup Summary (Before → After)[/bold cyan]"]
    changed = []

    changed_fields = [
        ("Virtual environment", before["has_venv"], after["has_venv"]),
        ("requirements.txt", before["has_requirements"], after["has_requirements"]),
        ("node_modules", before["has_node_modules"], after["has_node_modules"]),
        ("Git repository", before["has_git"], after["has_git"]),
        ("Java OK for Minecraft", before["java_ok"], after["java_ok"]),
    ]

    for label, b, a in changed_fields:
        line = _format_state_flag(
            label, b, a,
            true_label="Present/OK",
            false_label="Missing/Not OK",
            na_label="N/A",
        )
        if line:
            changed.append("  " + line)

    if not changed:
        summary_lines.append("No observable changes detected (folder is likely already configured).")
    else:
        summary_lines.extend(changed)

    text = "\n".join(summary_lines)

    if RICH:
        console.print(Panel(text, title="🧙 Project Setup", border_style="cyan"))
    else:
        print(text)





# ---------- Internet ops ----------
DOWNLOAD_CAP_BYTES = 1_000_000_000  # 1 GB

def filename_from_url(url):
    pth = urlparse(url).path
    fn = Path(pth).name or "download.bin"
    return fn

def op_open_url(url):
    try:
        if sys.platform.startswith("win"):
            os.startfile(url)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", url])
        else:
            subprocess.Popen(["xdg-open", url])
        log_action(f"OPEN_URL {url}")
    except Exception as e:
        p(f"[red]❌ {e}[/red]" if RICH else f"Error: {e}")

def op_download(url, dest_folder):
    dest = resolve(dest_folder)
    dest.mkdir(parents=True, exist_ok=True)
    fname = filename_from_url(url)
    out_path = dest / fname

    size_bytes = None
    if HAVE_REQUESTS:
        try:
            h = requests.head(url, allow_redirects=True, timeout=10, verify=STATE["ssl_verify"])
            if h.ok and "content-length" in h.headers:
                size_bytes = int(h.headers["content-length"])
        except Exception:
            size_bytes = None

    if size_bytes is not None and size_bytes > DOWNLOAD_CAP_BYTES:
        p(f"[red]❌ File exceeds 1 GB limit ({lc_size(size_bytes)}).[/red]" if RICH else "File exceeds 1 GB.")
        return

    label_size = lc_size(size_bytes) if size_bytes is not None else "unknown size"
    if not confirm(f"Download:\n  {url}\n→ {out_path}\nSize: {label_size}"):
        return

    try:
        if HAVE_REQUESTS:
            with requests.get(url, stream=True, timeout=30, verify=STATE["ssl_verify"]) as r:
                r.raise_for_status()
                total = int(r.headers.get("content-length", 0)) or size_bytes or 0
                if total and total > DOWNLOAD_CAP_BYTES:
                    p(f"[red]❌ File exceeds 1 GB limit during GET ({lc_size(total)}).[/red]" if RICH else "File exceeds 1 GB.")
                    return
                if RICH and total:
                    with Progress(
                        TextColumn("[progress.description]{task.description}"),
                        BarColumn(),
                        DownloadColumn(),
                        TransferSpeedColumn(),
                        TimeRemainingColumn(),
                        transient=True,
                        console=console
                    ) as prog, open(out_path, "wb") as f:
                        t = prog.add_task(f"Downloading {fname}", total=total)
                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                prog.update(t, advance=len(chunk))
                else:
                    with open(out_path, "wb") as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
        else:
            # urllib fallback
            import urllib.request, ssl
            req = urllib.request.Request(url)
            ctx = None
            if not STATE["ssl_verify"]:
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
            with urllib.request.urlopen(req, context=ctx) as response, open(out_path, "wb") as out:
                total = response.length or 0
                if total and total > DOWNLOAD_CAP_BYTES:
                    p("File exceeds 1 GB limit."); return
                block = 8192; downloaded = 0
                if RICH and total:
                    with Progress(TextColumn("[progress.description]{task.description}"), BarColumn(),
                                  DownloadColumn(), TransferSpeedColumn(), TimeRemainingColumn(),
                                  transient=True, console=console) as prog:
                        t = prog.add_task(f"Downloading {fname}", total=total or 1)
                        while True:
                            buf = response.read(block)
                            if not buf: break
                            downloaded += len(buf)
                            if downloaded > DOWNLOAD_CAP_BYTES:
                                p("File exceeds 1 GB limit during download.")
                                return
                            out.write(buf)
                            prog.update(t, advance=len(buf))
                else:
                    while True:
                        buf = response.read(block)
                        if not buf: break
                        downloaded += len(buf)
                        if downloaded > DOWNLOAD_CAP_BYTES:
                            p("File exceeds 1 GB limit during download."); return
                        out.write(buf)
        log_action(f"DOWNLOADED {url} -> {out_path}")
        p(f"[green]✅ Downloaded:[/green] {out_path}" if RICH else f"Downloaded: {out_path}")
        if confirm("📂 Open containing folder?"):
            op_explore(str(out_path.parent))
    except Exception as e:
        p(f"[red]❌ {e}[/red]" if RICH else f"Error: {e}")

def op_download_list(file_with_urls, dest_folder):
    fp = resolve(file_with_urls)
    if not fp.exists():
        p(f"[red]❌ Not found:[/red] {fp}" if RICH else f"Not found: {fp}")
        return
    urls = [line.strip() for line in fp.read_text(encoding="utf-8", errors="ignore").splitlines() if line.strip()]
    for u in urls:
        op_download(u, dest_folder)
        
        
# ---------- Timer / Reminder ----------
def op_timer(delay, action=None):
    """
    timer <seconds> [action]
      - If [action] starts with 'run' or 'macro', it executes that command.
      - Otherwise it prints the text as a reminder.
    """
    import threading, sys

    # ---- parse delay safely ----
    try:
        delay = int(delay)
        if delay <= 0:
            p("[red]Timer delay must be positive.[/red]")
            return
    except Exception:
        p("[red]Invalid timer delay.[/red]")
        return

    def thread_print(msg: str):
        """Thread-safe print that keeps cursor and color consistent."""
        sys.stdout.write(f"\n{msg}\n")
        # Carriage return resets line start, print bright cyan prompt
        _bg_path = str(CWD) if get_config_value(CONFIG, "prompt.show_path", True) else CWD.name
        sys.stdout.write(f"\r\033[1;96mCMC>{_bg_path}> \033[0m")
        sys.stdout.flush()

    def _trigger():
        try:
            if not action:
                thread_print(f"✅ Timer finished ({delay}s).")
                return

            text = action.strip()
            low = text.lower()

            if low.startswith("run ") or low.startswith("macro "):
                thread_print(f"⏰ Timer triggered: {text}")
                prev_batch = STATE.get("batch", False)
                STATE["batch"] = True
                try:
                    handle_command(text)
                except Exception as e:
                    thread_print(f"❌ Timer action failed: {e}")
                finally:
                    STATE["batch"] = prev_batch
            else:
                thread_print(f"⏰ {action}")

        except Exception as e:
            thread_print(f"❌ Timer thread error: {e}")

        finally:
            try:
                from prompt_toolkit.application import get_app
                app = get_app()
                app.invalidate()
                # ensure color reset after redraw
                sys.stdout.write("\033[0m")
                sys.stdout.flush()
            except Exception:
                pass

    try:
        t = threading.Timer(delay, _trigger)
        t.daemon = True
        t.start()
        p(f"[cyan]⏳ Timer set for {delay} s.[/cyan]")
        sys.stdout.flush()
    except Exception as e:
        p(f"[red]❌ Timer error:[/red] {e}")



 
 

# ---------- Log / Undo ----------
def op_log():
    if not LOG:
        p("[yellow]No log entries yet.[/yellow]" if RICH else "No log entries.")
        return
    if RICH:
        t = Table(title="Log")
        t.add_column("Entry", overflow="fold")
        for e in LOG[-200:]:
            t.add_row(e)
        console.print(t)
    else:
        for e in LOG[-200:]:
            print(e)

def op_undo():
    if not UNDO:
        p("[yellow]Nothing to undo.[/yellow]" if RICH else "Nothing to undo.")
        return
    step = UNDO.pop()
    kind = step["kind"]
    try:
        if kind == "move":
            shutil.move(step["src"], step["dst"])
            p(f"[green]✅ Undid move → restored to {step['dst']}[/green]" if RICH else f"Undid move.")

        elif kind == "rename":
            os.rename(step["src"], step["dst"])
            p(f"[green]✅ Undid rename → back to {Path(step['dst']).name}[/green]" if RICH else "Undid rename.")

        elif kind == "delete":
            # Restore from trash back to original location
            original = Path(step["original"])
            original.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(step["trash"], str(original))
            p(f"[green]✅ Restored:[/green] {original}" if RICH else f"Restored: {original}")

        elif kind == "copy":
            # Delete the copy that was created
            dest = Path(step["dest"])
            if dest.exists():
                if step.get("is_dir"):
                    shutil.rmtree(dest)
                else:
                    dest.unlink()
            p(f"[green]✅ Undid copy — removed {dest}[/green]" if RICH else f"Undid copy.")

        elif kind == "create_file":
            fp = Path(step["path"])
            if fp.exists():
                fp.unlink()
            p(f"[green]✅ Undid file creation — deleted {fp.name}[/green]" if RICH else f"Undid create file.")

        elif kind == "create_folder":
            fp = Path(step["path"])
            if fp.exists() and fp.is_dir():
                shutil.rmtree(fp)
            p(f"[green]✅ Undid folder creation — deleted {fp.name}[/green]" if RICH else f"Undid create folder.")

        elif kind == "write":
            fp = Path(step["path"])
            if step["existed"]:
                fp.write_text(step["old_content"], encoding="utf-8")
                p(f"[green]✅ Undid write — restored previous content of {fp.name}[/green]" if RICH else f"Undid write.")
            else:
                fp.unlink(missing_ok=True)
                p(f"[green]✅ Undid write — removed {fp.name} (it didn't exist before)[/green]" if RICH else "Undid write.")

        elif kind == "macro_add":
            name = step["name"]
            if step["old_val"] is None:
                # Was a new macro — remove it
                MACROS.pop(name, None)
                macros_save(MACROS)
                p(f"[green]✅ Undid macro add — removed '{name}'[/green]" if RICH else f"Undid macro add.")
            else:
                # Was an overwrite — restore old body
                MACROS[name] = step["old_val"]
                macros_save(MACROS)
                p(f"[green]✅ Undid macro overwrite — '{name}' restored[/green]" if RICH else f"Undid macro overwrite.")

        elif kind == "macro_delete":
            MACROS[step["name"]] = step["body"]
            macros_save(MACROS)
            p(f"[green]✅ Restored macro '{step['name']}'[/green]" if RICH else f"Restored macro.")

        elif kind == "macro_clear":
            MACROS.update(step["snapshot"])
            macros_save(MACROS)
            p(f"[green]✅ Restored {len(step['snapshot'])} macro(s)[/green]" if RICH else "Restored macros.")

        elif kind == "alias_add":
            name = step["name"]
            if step["old_val"] is None:
                ALIASES.pop(name, None)
                save_aliases()
                p(f"[green]✅ Undid alias add — removed '{name}'[/green]" if RICH else f"Undid alias add.")
            else:
                ALIASES[name] = step["old_val"]
                save_aliases()
                p(f"[green]✅ Undid alias overwrite — '{name}' restored[/green]" if RICH else "Undid alias overwrite.")

        elif kind == "alias_delete":
            ALIASES[step["name"]] = step["cmd"]
            save_aliases()
            p(f"[green]✅ Restored alias '{step['name']}' → {step['cmd']}[/green]" if RICH else "Restored alias.")

        elif kind == "config_change":
            global CONFIG
            CONFIG = step["old_config"]
            apply_config_to_state(CONFIG, STATE)
            save_config(CONFIG, Path(__file__).parent)
            p("[green]✅ Config restored to previous state.[/green]" if RICH else "Config restored.")

        else:
            p(f"[yellow]Cannot undo '{kind}'.[/yellow]" if RICH else f"Cannot undo '{kind}'.")
            UNDO.append(step)  # put it back since we didn't handle it

    except Exception as e:
        p(f"[red]❌ Undo failed:[/red] {e}" if RICH else f"Undo failed: {e}")


# ---------- Auto-detect installed Java versions ----------
def detect_java_versions():
    """Scan registry and common folders for Java installations."""
    detected = {}

    try:
        import winreg
        reg_paths = [
            r"SOFTWARE\\Eclipse Adoptium",
            r"SOFTWARE\\JavaSoft\\Java Development Kit",
            r"SOFTWARE\\JavaSoft\\JDK",
            r"SOFTWARE\\JavaSoft\\Java Runtime Environment",
        ]
        for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            for path in reg_paths:
                try:
                    with winreg.OpenKey(root, path) as key:
                        i = 0
                        while True:
                            try:
                                sub = winreg.EnumKey(key, i)
                                with winreg.OpenKey(key, sub) as subkey:
                                    try:
                                        home, _ = winreg.QueryValueEx(subkey, "JavaHome")
                                        if Path(home).exists():
                                            detected[sub] = home
                                    except FileNotFoundError:
                                        pass
                            except OSError:
                                break
                            i += 1
                except FileNotFoundError:
                    continue
    except Exception:
        pass

    # Folder scan fallback
    search_roots = [
        Path("C:/Program Files/Eclipse Adoptium"),
        Path("C:/Program Files/Java"),
        Path("C:/Program Files (x86)/Java"),
    ]
    for root in search_roots:
        if root.exists():
            for sub in root.iterdir():
                if sub.is_dir() and ("jdk" in sub.name.lower() or "jre" in sub.name.lower()):
                    detected[sub.name] = str(sub)

    return detected

JAVA_VERSIONS = detect_java_versions()


# ---------- Macros (persistent) ----------
def macros_load():
    try:
        if MACROS_FILE.exists():
            return json.loads(MACROS_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}

def macros_save(d: dict):
    MACROS_FILE.parent.mkdir(exist_ok=True)
    MACROS_FILE.write_text(json.dumps(d, indent=2), encoding="utf-8")
    


# 🚨 Keep these two exactly at column 0 (no spaces/tabs before them)
MACROS = macros_load()
load_aliases()

def expand_vars(s: str) -> str:
    today = datetime.date.today().isoformat()
    now = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    home = str(Path.home())
    return (
        s.replace("%DATE%", today)
         .replace("%NOW%", now)
         .replace("%HOME%", home)
    )

def macro_add(name: str, text: str):
    name = name.strip()
    if not name:
        p("[red]Macro name required.[/red]"); return
    if not text.strip():
        p("[red]Macro command text required.[/red]"); return
    if name in MACROS and not STATE["batch"]:
        if not confirm(f"Macro '{name}' exists. Overwrite?"):
            p("[yellow]Canceled.[/yellow]"); return
    old_val = MACROS.get(name)  # None if new, old body if overwrite
    MACROS[name] = text.strip()
    macros_save(MACROS)
    push_undo("macro_add", name=name, old_val=old_val)
    log_action(f"MACRO ADD {name} = {text}")
    p(f"[green]✅ Macro saved:[/green] {name}")

def macro_run(name: str):
    if name not in MACROS:
        p(f"[red]❌ Macro not found:[/red] {name}"); return
    p(f"[cyan]▶ Running macro:[/cyan] {name}") if RICH else print(f"> Running macro {name}")
    text = expand_vars(MACROS[name])
    # Backward compat: old macros may use semicolons
    if ";" in text and "," not in text:
        separator = r";\s*"
    else:
        separator = r",\s*"
    for part in [t.strip() for t in re.split(separator, text) if t.strip()]:
        handle_command(part)
    log_action(f"MACRO RUN {name}")

def macro_list():
    if not MACROS:
        p("[yellow]No macros saved.[/yellow]"); return
    if RICH:
        t = Table(title="Saved Macros", show_lines=True)
        t.add_column("Name", style="cyan")
        t.add_column("Command(s)")
        for k, v in MACROS.items():
            t.add_row(k, v)
        p(t)
    else:
        for k, v in MACROS.items():
            print(f"- {k} = {v}")

def macro_delete(name: str):
    if name not in MACROS:
        p(f"[yellow]No such macro:[/yellow] {name}"); return
    old_body = MACROS[name]
    del MACROS[name]
    macros_save(MACROS)
    push_undo("macro_delete", name=name, body=old_body)
    log_action(f"MACRO DELETE {name}")
    p(f"[green]✅ Deleted macro:[/green] {name}")

def macro_clear():
    if not STATE["batch"]:
        if not confirm("Delete ALL macros?"):
            p("[yellow]Canceled.[/yellow]"); return
    snapshot = dict(MACROS)  # save all macros before clearing
    MACROS.clear()
    macros_save(MACROS)
    push_undo("macro_clear", snapshot=snapshot)
    log_action("MACRO CLEAR ALL")
    p("[green]✅ Cleared all macros.[/green]")


def macro_edit(name: str):
    """Open a macro body in a pre-filled prompt_toolkit input for editing."""
    if name not in MACROS:
        p(f"[yellow]No such macro:[/yellow] {name}"); return
    old_body = MACROS[name]
    p(f"[cyan]Editing macro:[/cyan] {name}")
    p("[dim]Edit the command below and press Enter to save, or Ctrl+C to cancel.[/dim]")
    try:
        from prompt_toolkit import PromptSession as _PS
        from prompt_toolkit.history import InMemoryHistory as _IMH
        _sess = _PS(history=_IMH())
        new_body = _sess.prompt("  > ", default=old_body).strip()
    except KeyboardInterrupt:
        p("[yellow]Edit cancelled.[/yellow]"); return
    except Exception:
        # Fallback: plain input pre-filled with old value shown as hint
        print(f"  Current: {old_body}")
        try:
            new_body = input("  New value (Enter to keep): ").strip()
            if not new_body:
                new_body = old_body
        except KeyboardInterrupt:
            p("[yellow]Edit cancelled.[/yellow]"); return
    if new_body == old_body:
        p("[dim]No changes made.[/dim]"); return
    MACROS[name] = new_body
    macros_save(MACROS)
    push_undo("macro_add", name=name, old_val=old_body)
    log_action(f"MACRO EDIT {name} = {new_body}")
    p(f"[green]✅ Macro updated:[/green] {name} = {new_body}")


# ===========================================================================
# ── PORTS  (show open ports / kill a port)
# ===========================================================================

def _get_listening_ports() -> list:
    """Return list of dicts: {port, pid, name} for all LISTENING TCP ports."""
    import psutil
    rows = []
    try:
        seen = set()
        for conn in psutil.net_connections(kind="inet"):
            if conn.status == "LISTEN" and conn.laddr:
                port = conn.laddr.port
                pid  = conn.pid or 0
                if port in seen:
                    continue
                seen.add(port)
                name = ""
                if pid:
                    try:
                        name = psutil.Process(pid).name()
                    except Exception:
                        name = "?"
                rows.append({"port": port, "pid": pid, "name": name})
    except Exception:
        pass
    return sorted(rows, key=lambda r: r["port"])


def op_ports(p) -> None:
    """Show all listening ports with PID and process name."""
    rows = _get_listening_ports()
    if not rows:
        p("[yellow]No listening ports found (try running as admin for full list).[/yellow]")
        return
    if RICH:
        from rich.table import Table as _T
        t = _T(title="Open Ports", show_lines=False, border_style="cyan")
        t.add_column("Port",    style="bold cyan", justify="right")
        t.add_column("PID",     style="dim",       justify="right")
        t.add_column("Process", style="green")
        for r in rows:
            t.add_row(str(r["port"]), str(r["pid"]) if r["pid"] else "—", r["name"] or "—")
        console.print(t)
    else:
        print(f"{'PORT':<8} {'PID':<8} PROCESS")
        for r in rows:
            print(f"{r['port']:<8} {r['pid']:<8} {r['name']}")
    p(f"[dim]{len(rows)} port(s) listening.[/dim]")


def op_kill_port(port: int, p) -> None:
    """Kill the process listening on a given port."""
    import psutil
    killed = []
    try:
        for conn in psutil.net_connections(kind="inet"):
            if conn.status == "LISTEN" and conn.laddr and conn.laddr.port == port and conn.pid:
                try:
                    proc = psutil.Process(conn.pid)
                    name = proc.name()
                    proc.kill()
                    killed.append(f"{name} (PID {conn.pid})")
                except Exception as exc:
                    p(f"[red]Could not kill PID {conn.pid}:[/red] {exc}")
    except Exception as exc:
        p(f"[red]Error scanning ports:[/red] {exc}")
        return
    if killed:
        p(f"[green]✅ Killed on port {port}:[/green] {', '.join(killed)}")
    else:
        p(f"[yellow]Nothing listening on port {port}.[/yellow]")


# ---------- Suggestions for partial commands ----------
COMMAND_HINTS = [
    "pwd","cd","back","home","list","info","find","findext","recent","biggest","search",
    "create file","create folder","write","read","move","copy","rename","delete", "ai-model list", "ai-model current" , "ai-model set <model>" , "model list" , "model current" , "model set <model>",
    "zip","unzip","open","explore","backup","run",
    "download","downloadlist","open url",
    "batch on","batch off","dry-run on","dry-run off","ssl on","ssl off","status","log","undo",
    "macro add <name> = <commands>","macro run <name>","macro edit <name>","macro list","macro delete <name>","macro clear","help","exit", "search web <query>",
    "ports","kill",
    # Scaffolding & dev tools
    "setup",
    "new python","new node","new flask","new fastapi","new react","new vue","new svelte",
    "new next","new electron","new discord","new cli","new web",
    "dev","dev stop",
    "env list","env show","env get","env set","env delete","env template","env check",
]

def suggest_commands(s: str):
    s = s.strip().lower()
    cands = [h for h in COMMAND_HINTS if h.startswith(s)]
    if not cands:
        p(f"Unknown command: {s}")
        return
    if RICH:
        t = Table(title="Suggestions")
        t.add_column("Try")
        for c in cands[:10]:
            t.add_row(c)
        console.print(t)
    else:
        print("Suggestions:", ", ".join(cands[:10]))


# ---------- Main command handler ----------
def handle_command(s: str):
    global Path, p, CONFIG  # ✅ ensure we always use the global versions

    # --- Runtime Path fix (safest minimal form) ---
    import pathlib, builtins
    builtins.Path = pathlib.Path
    globals()["Path"] = pathlib.Path

    import subprocess  # used by several commands below

    s = s.strip()
    if not s:
        return

        # Skip comment / empty lines
    if s.startswith("#"):
        return
        
            # ---------- Config system ----------
    low = s.lower()
    if low.startswith("config"):
        from CMC_Config import (
            load_config,
            save_config,
            get_config_value,
            set_config_value,
            parse_value,
            DEFAULT_CONFIG,
        )
        global CONFIG

        # ------------------------------------------------------------------
        # Flat short-name aliases → full dotted key
        # Lets users type e.g. "config set show_update false" instead of
        # "config set header.show_update false".
        # ------------------------------------------------------------------
        _CONFIG_ALIASES: dict = {
            "batch":          "batch",
            "dry_run":        "dry_run",
            "ssl_verify":     "ssl_verify",
            "ai_model":       "ai.model",
            "open_browser":   "git.open_browser",
            "show_update":    "header.show_update",
            "show_path":      "prompt.show_path",
            "default_depth":  "space.default_depth",
            "auto_ai":        "space.auto_ai",
            "auto_report":    "space.auto_report",
        }

        def _resolve_config_key(k: str) -> str:
            """Return the full dotted key, resolving flat aliases."""
            return _CONFIG_ALIASES.get(k, k)

        parts = s.split()
        # Just "config" or "config help"
        if len(parts) == 1 or (len(parts) >= 2 and parts[1].lower() == "help"):
            p(
                "Config usage:\n"
                "  config list\n"
                "  config get <key>\n"
                "  config set <key> <value>\n"
                "  config reset\n\n"
                "Short names (no prefix needed):\n"
                "  show_update     header.show_update    show ● CMC up to date in header\n"
                "  show_path       prompt.show_path      show full path in prompt\n"
                "  ai_model        ai.model              active AI model name\n"
                "  open_browser    git.open_browser      open GitHub after git upload/update\n"
                "  default_depth   space.default_depth   default depth for space command\n"
                "  auto_ai         space.auto_ai         auto-run AI after space scan\n"
                "  batch           batch                 skip all confirmations\n"
                "  dry_run         dry_run               preview commands without running\n\n"
                "Examples:\n"
                "  config set show_update false\n"
                "  config set open_browser false\n"
                "  config set default_depth 3\n"
                "  config set batch on\n"
            )
            return

        cmd = parts[1].lower()

        # config list — show a clean table
        if cmd == "list":
            if RICH:
                from rich.table import Table as _Table
                tbl = _Table(show_header=True, header_style="bold cyan", show_lines=True, box=None)
                tbl.add_column("Key", style="cyan", no_wrap=True)
                tbl.add_column("Short name", style="dim", no_wrap=True)
                tbl.add_column("Value", style="green")
                tbl.add_column("Default", style="dim")
                # Build reverse alias map: dotted_key → short_name
                _rev: dict = {}
                for short, full in _CONFIG_ALIASES.items():
                    if full not in _rev:
                        _rev[full] = short
                def _flat_items(d: dict, prefix: str = "") -> list:
                    rows = []
                    for k, v in sorted(d.items()):
                        full_key = f"{prefix}.{k}" if prefix else k
                        if isinstance(v, dict):
                            rows.extend(_flat_items(v, full_key))
                        else:
                            rows.append((full_key, v))
                    return rows
                for dotted, def_val in _flat_items(DEFAULT_CONFIG):
                    cur_val = get_config_value(CONFIG or DEFAULT_CONFIG, dotted, default=def_val)
                    short = _rev.get(dotted, "")
                    changed = cur_val != def_val
                    val_str = f"[bold green]{cur_val}[/bold green]" if changed else str(cur_val)
                    tbl.add_row(dotted, short, val_str, str(def_val))
                p(tbl)
            else:
                import json as _json
                p(_json.dumps(CONFIG or {}, indent=2, sort_keys=True))
            return

        # config reset
        if cmd == "reset":
            old_cfg = dict(CONFIG)
            CONFIG = dict(DEFAULT_CONFIG)
            apply_config_to_state(CONFIG, STATE)
            save_config(CONFIG, Path(__file__).parent)
            push_undo("config_change", old_config=old_cfg)
            p("[green]Config reset to defaults.[/green]")
            return

        # config get <key>
        if cmd == "get" and len(parts) >= 3:
            key = _resolve_config_key(parts[2])
            val = get_config_value(CONFIG, key, default=None)
            p(f"{key} = {val!r}")
            return

        # config set <key> <value...>
        if cmd == "set" and len(parts) >= 4:
            key = _resolve_config_key(parts[2])
            raw_value = " ".join(parts[3:])
            # Validate key exists in DEFAULT_CONFIG
            test = get_config_value(DEFAULT_CONFIG, key, default="__missing__")
            if test == "__missing__":
                p(f"[red]❌ Unknown config key:[/red] {key}")
                p("[dim]Use 'config list' to see valid keys, or 'config help' for short names.[/dim]")
                return
            value = parse_value(raw_value)
            old_cfg = dict(CONFIG)
            CONFIG = set_config_value(CONFIG, key, value)
            # Apply top-level flags immediately
            apply_config_to_state(CONFIG, STATE)
            save_config(CONFIG, Path(__file__).parent)
            push_undo("config_change", old_config=old_cfg)
            p(f"[green]✓[/green] {key} = [bold]{value!r}[/bold]")
            return

        p(f"[red]Unknown config command:[/red] {' '.join(parts[1:])}")
        return



    # ---------- Space (disk usage + AI cleanup) ----------
    if low.startswith("space"):
        try:
            from CMC_Space import op_space
            op_space(s, CWD, STATE, MACROS, p, RICH)
        except Exception as e:
            p(f"[red]Space command error:[/red] {e}" if RICH else f"Space command error: {e}")
        return


    # ---------- AI model manager ----------
    # Allow "model ..." as an alias for "ai-model ..."
    if low.startswith("model"):
        s = "ai-model" + s[len("model"):]
        low = s.lower()

    if low.startswith("ai-model"):
        parts = s.split()

        if len(parts) == 1 or (len(parts) >= 2 and parts[1].lower() in ("help", "?", "-h", "--help")):
            p("Usage:")
            p("  ai-model list")
            p("  ai-model current")
            p("  ai-model set <model>")
            p("Alias:")
            p("  model list|current|set <model>")
            return

        sub = parts[1].lower()

        if sub == "list":
            try:
                ollama_cmd = shutil.which("ollama") or shutil.which("ollama.exe")
                if not ollama_cmd:
                    candidates = [
                        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe",
                        Path(os.environ.get("ProgramFiles", "")) / "Ollama" / "ollama.exe",
                        Path(os.environ.get("ProgramFiles(x86)", "")) / "Ollama" / "ollama.exe",
                    ]
                    for cand in candidates:
                        if str(cand).strip() and cand.exists():
                            ollama_cmd = str(cand)
                            break

                if not ollama_cmd:
                    p("[yellow]Ollama CLI not found.[/yellow] Install Ollama or add it to PATH.")
                    p("[dim]Then retry: ai-model list[/dim]")
                    return

                out = subprocess.check_output([ollama_cmd, "list"], stderr=subprocess.STDOUT, text=True)
                names = []
                for line in out.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    head = line.split()[0]
                    if head.upper() == "NAME":
                        continue
                    names.append(head)

                if not names:
                    p("[yellow]No models found (ollama list returned no entries).[/yellow]")
                else:
                    p("Available models:")
                    for name in names:
                        p(f"  - {name}")
            except Exception as e:
                p(f"[red]Failed to list Ollama models.[/red] {e}")
            return

        if sub == "current":
            p(f"Current AI model: {get_ai_model()}")
            return

        if sub == "set":
            if len(parts) < 3:
                p("[red]Missing model name.[/red] Example: ai-model set qwen2.5:7b-instruct")
                return
            new_model = parts[2].strip()

            # Persist model in config on disk (load -> set -> save -> verify)
            try:
                from CMC_Config import load_config as _cfg_load, save_config as _cfg_save
                cfg_dir = Path(__file__).parent
                cfg_path = cfg_dir / "CMC_Config.json"

                cfg = _cfg_load(cfg_dir) if callable(_cfg_load) else {}
                if not isinstance(cfg, dict):
                    cfg = {}
                if not isinstance(cfg.get("ai"), dict):
                    cfg["ai"] = {}
                cfg["ai"]["model"] = new_model

                if callable(_cfg_save):
                    _cfg_save(cfg, cfg_dir)

                verify = _cfg_load(cfg_dir) if callable(_cfg_load) else cfg
                persisted = None
                if isinstance(verify, dict):
                    persisted = (verify.get("ai", {}) or {}).get("model")
                if persisted != new_model:
                    p(f"[red]Failed to persist AI model.[/red] Check write access to {cfg_path}")
                    return

                CONFIG = verify if isinstance(verify, dict) else cfg
            except Exception as e:
                p(f"[red]Failed to save AI model to config.[/red] {e}")
                return

            # Sync assistant runtime if available
            try:
                import assistant_core
                if hasattr(assistant_core, "_OLLAMA_MODEL"):
                    assistant_core._OLLAMA_MODEL = new_model
                if hasattr(assistant_core, "clear_manual_cache"):
                    assistant_core.clear_manual_cache()
                if hasattr(assistant_core, "clear_history"):
                    assistant_core.clear_history()
            except Exception:
                pass

            p(f"[green]AI model updated and saved:[/green] {new_model}")
            p("[dim]AI conversation history cleared (new model).[/dim]")
            return






       # ---------- Embedded AI assistant ----------
    # Usage:
    #   ai how do I back up my project?
    #   ai fix          → diagnose last error
    #   ai clear        → reset conversation history
    if s.lower().startswith("ai "):
        if not HAVE_ASSISTANT:
            p("[yellow]⚠ AI assistant is not configured (assistant_core.py missing or Ollama not running).[/yellow]")
            return

        # Everything after "ai "
        user_query = s[3:].strip()

        # Strip matching outer quotes
        if (user_query.startswith('"') and user_query.endswith('"')) or (
            user_query.startswith("'") and user_query.endswith("'")
        ):
            user_query = user_query[1:-1].strip()

        sub = user_query.lower()

        # ai fix — diagnose the last failed command
        if sub == "fix":
            if not _LAST_ERROR:
                p("[yellow]No recent error to fix.[/yellow]")
                return
            try:
                reply_text = run_ai_fix(_LAST_CMD, _LAST_ERROR, str(CWD), STATE, MACROS, ALIASES)
                p(reply_text)
            except Exception as e:
                p(f"[red]❌ AI fix error:[/red] {e}")
            return

        # ai clear — reset conversation history
        if sub == "clear":
            try:
                ai_clear_history()
                p("[cyan]AI conversation history cleared.[/cyan]")
            except Exception:
                p("[yellow]Could not clear history.[/yellow]")
            return

        try:
            cwd_str = str(CWD)
            reply_text = run_ai_assistant(user_query, cwd_str, STATE, MACROS, ALIASES)
            p(reply_text)
        except Exception as e:
            p(f"[red]❌ AI assistant error:[/red] {e}")
        return




        
            # ---------- CMD passthrough (inline) ----------
    m = re.match(r"^cmd\s+(.+)$", s, re.I)
    if m:
        cmd_line = m.group(1)
        if STATE.get("dry_run"):
            p(f"[yellow]DRY-RUN:[/yellow] would run CMD → {cmd_line}")
            return
        try:
            import subprocess
            result = subprocess.run(cmd_line, shell=True, text=True, capture_output=True)
            if result.stdout:
                p(result.stdout.strip())
            if result.stderr:
                p(f"[red]{result.stderr.strip()}[/red]")
        except Exception as e:
            p(f"[red]❌ CMD command failed:[/red] {e}")
        return





        # ---------- Alias expansion ----------
    parts = s.split(maxsplit=1)
    if parts and parts[0] in ALIASES:
        alias_cmd = ALIASES[parts[0]]
        rest = parts[1] if len(parts) > 1 else ""
        # Combine alias expansion + remaining args
        s = f"{alias_cmd} {rest}".strip()
        p(f"[dim]↳ alias →[/dim] {s}")
        
            # ---------- Self test ----------
    if s.lower() == "selftest commands":
        try:
            import inspect, re as _re
            defined_ops = sorted([n for n, obj in globals().items()
                                  if n.startswith("op_") and callable(obj)])
            # Rough scan of this function's source for regex routes
            src = inspect.getsource(handle_command)
            routes = sorted(set(m.group(1).strip()
                                for m in _re.finditer(r'^\s*m\s*=\s*re\.match\(\s*r"(\^.+?)"', src, _re.M)))
            p("[cyan]Defined op_* functions:[/cyan]")
            for n in defined_ops: p(f"  {n}")
            p("\n[cyan]Regex routes in handle_command:[/cyan]")
            for r in routes: p(f"  {r}")
        except Exception as e:
            p(f"[red]Selftest failed:[/red] {e}")
        return



    # Fix for broken multi-line commands (when a line ends with "to")
    if s.lower().endswith("to"):
        try:
            nxt = input("... ")
            s = s + " " + nxt.strip()
        except EOFError:
            pass

    # Normalize once
    low = s.lower()
    
        # ---------- CMC Self Update ----------
    if low in ("cmc update check", "cmc update"):
        try:
            from CMC_Update import cmc_update_check, cmc_update_apply
            # CMC root is one level above src/
            cmc_root = Path(__file__).resolve().parent.parent
            if low == "cmc update check":
                cmc_update_check(p, cmc_folder=cmc_root)
            else:
                cmc_update_apply(p, cmc_root)
        except Exception as e:
            p(f"[red]❌ CMC update failed:[/red] {e}" if RICH else f"CMC update failed: {e}")
        return

    
    # ---------- Git commands ----------
    try:
       from CMC_Git import handle_git_commands
       if handle_git_commands(s, low, CWD, p, RICH, console if "console" in globals() else None):
           return
    except Exception as e:
        p(f"[red]❌ Git module error:[/red] {e}")
        return

    # ---------- Docker commands ----------
    try:
        from CMC_Docker import handle_docker_commands
        if handle_docker_commands(s, low, CWD, p):
            return
    except Exception as e:
        p(f"[red]❌ Docker module error:[/red] {e}")
        return

    
    
    # ---------- setup (auto-detect & get project running) ----------
    if low == "setup":
        try:
            handle_setup(CWD, p)
        except Exception as e:
            p(f"[red]❌ Setup error:[/red] {e}")
        return

    # ---------- new <type> (project scaffolding) ----------
    if low.startswith("new ") or low == "new":
        try:
            handle_new(s, CWD, p)
        except Exception as e:
            p(f"[red]❌ New project error:[/red] {e}")
        return

    # ---------- dev [script|stop] (smart dev-server launcher) ----------
    if low == "dev" or low.startswith("dev "):
        try:
            handle_dev(s, CWD, p)
        except Exception as e:
            p(f"[red]❌ Dev error:[/red] {e}")
        return

    # ---------- env (dotenv file manager) ----------
    if low == "env" or low.startswith("env "):
        try:
            handle_env(s, CWD, p)
        except Exception as e:
            p(f"[red]❌ Env error:[/red] {e}")
        return

    # ---------- Project Scan ----------
    m = re.match(r"^projectscan$", s, re.I)
    if m:
        try:
            op_project_scan()
        except Exception as e:
            p(f"[red]❌ Project scan failed:[/red] {e}")
        return
        
        




    

    # ---------- Timer command ----------
    m = re.match(r"^timer\s+(\d+)(?:\s+(.+))?$", s, re.I)
    if m:
        op_timer(m.group(1), m.group(2))
        return
        
        
     




    # ---------- Utility automation commands ----------
    m = re.match(r"^sleep\s+(\d+)$", s, re.I)
    if m:
        secs = int(m.group(1))
        time.sleep(secs)
        p(f"😴 Slept for {secs} seconds")
        return

    m = re.match(r'^sendkeys\s+"(.+)"$', s, re.I)
    if m:
        try:
            import pyautogui
            keys = m.group(1)
            if "{ENTER}" in keys.upper():
                parts = re.split(r"\{ENTER\}", keys, flags=re.I)
                for i, part in enumerate(parts):
                    if part.strip():
                        pyautogui.typewrite(part.strip())
                    if i < len(parts) - 1:
                        pyautogui.press("enter")
                        time.sleep(0.2)
            else:
                pyautogui.typewrite(keys)
            p(f"⌨️ Sent keys: {keys}")
        except Exception as e:
            p(f"[red]❌ Sendkeys failed:[/red] {e}")
        return

    # --- Universal run command (supports optional 'in <path>') ---
    m = re.match(r"^run\s+'(.+?)'\s*(?:in\s+'([^']+)')?$", s, re.I)
    if m:
        import pathlib
        full_cmd = m.group(1).strip()
        workdir = pathlib.Path(m.group(2)).expanduser() if m.group(2) else None
        try:
            cwd = str(workdir) if workdir else None
            subprocess.Popen(full_cmd, cwd=cwd, shell=True)
            p(f"🚀 Launched: {full_cmd}" + (f" (cwd={cwd})" if cwd else ""))
        except Exception as e:
            p(f"[red]❌ Failed to run:[/red] {e}")
        return






    # ---------- Control ----------
    m = re.match(r"^help(?:\s+(.+))?$", s, re.I)
    if m or low == "?":
        topic = None
        if m:
            raw = m.group(1)
            if raw:
                topic = raw.strip()
        show_help(topic)
        return
    if low == "status":
        show_status_box()
        return
    if low == "batch on":
        STATE["batch"] = True; log_action("BATCH ON"); p("Batch ON"); return
    if low == "batch off":
        STATE["batch"] = False; log_action("BATCH OFF"); p("Batch OFF"); return
    if low == "dry-run on":
        STATE["dry_run"] = True; p("Dry-Run ON"); return
    if low == "dry-run off":
        STATE["dry_run"] = False; p("Dry-Run OFF"); return
    if low == "ssl on":
        STATE["ssl_verify"] = True; p("SSL ON"); return
    if low == "ssl off":
        STATE["ssl_verify"] = False; p("⚠️ SSL verification OFF — allowing untrusted/expired certs"); return
    if low == "log":
        op_log(); return
    if low == "undo":
        op_undo(); return
            # ---------- Echo (for macros and inline output) ----------
    m = re.match(r"^echo\s+['\"]?(.+?)['\"]?$", s, re.I)
    if m:
        p(m.group(1))
        return

    if low == "exit":
        sys.exit(0)

    # Simple echo for macros
    m = re.match(r'^echo\s+["“](.+?)["”]$', s, re.I)
    if m:
        p(m.group(1)); return


    # ---------- Alias Commands ----------
    m = re.match(r"^alias\s+add\s+([A-Za-z0-9_\-]+)\s*(?:=\s*)?(.+)$", s, re.I)
    if m:
        name = m.group(1)
        value = m.group(2).strip()

        # strip accidental leading '=' if user typed "name = command"
        if value.startswith("="):
            value = value[1:].strip()

        old_alias = ALIASES.get(name)  # None if new, old cmd if overwrite
        ALIASES[name] = value
        save_aliases()
        push_undo("alias_add", name=name, old_val=old_alias)
        p(f"[cyan]Alias added:[/cyan] {name} → {value}")
        return


    m = re.match(r"^alias\s+delete\s+([A-Za-z0-9_\-]+)$", s, re.I)
    if m:
        name = m.group(1)
        if name in ALIASES:
            old_cmd = ALIASES[name]
            del ALIASES[name]
            save_aliases()
            push_undo("alias_delete", name=name, cmd=old_cmd)
            p(f"[yellow]Alias removed:[/yellow] {name}")
        else:
            p(f"[red]Alias not found:[/red] {name}")
        return

    if re.match(r"^alias\s+list$", s, re.I):
        if not ALIASES:
            p("[dim]No aliases defined.[/dim]")
        else:
            for k, v in ALIASES.items():
                p(f"[cyan]{k}[/cyan] → {v}")
        return
        
            # ---------- Java management ----------
    # Fallback helpers in case _apply_java_env / save_java_cfg aren't defined in this build
    def _apply_java_env_local(home_path: str):
        try:
            _apply_java_env(home_path)  # existing helper (if present in your build)
        except NameError:
            # Minimal local apply for this process only
            os.environ["JAVA_HOME"] = home_path
            binp = str(Path(home_path) / "bin")
            if binp not in os.environ.get("PATH", ""):
                os.environ["PATH"] = os.environ.get("PATH", "") + ";" + binp

    def _save_java_cfg_local(ver: str, home_path: str):
        try:
            save_java_cfg(ver, home_path)  # existing helper (if present)
        except NameError:
            pass  # no-op if not present

  

    if low == "java list":
        if not JAVA_VERSIONS:
            p("[yellow]No JAVA_VERSIONS configured in this build.[/yellow]")
        else:
            for k, v in JAVA_VERSIONS.items():
                tag = "(installed)" if Path(v).exists() else "(missing)"
                p(f"{k} -> {v} {tag}")
        return

    if low == "java version":
        home = os.environ.get("JAVA_HOME", "?")
        ver = STATE.get("java_version", "?")
        p(f"Active Java: {ver} ({home})")
        return

    if low == "java reload":
        try:
            # Try both user and system registry locations
            new_home = None
            for reg_cmd in [
                'reg query "HKCU\\Environment" /v JAVA_HOME',
                'reg query "HKLM\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment" /v JAVA_HOME'
            ]:
                try:
                    out = subprocess.check_output(
                        reg_cmd, shell=True, text=True, stderr=subprocess.DEVNULL
                    )
                    m = re.search(r"JAVA_HOME\s+REG_SZ\s+(.+)", out)
                    if m:
                        new_home = m.group(1).strip()
                        break
                except subprocess.CalledProcessError:
                    continue

            if new_home and Path(new_home).exists():
                _apply_java_env_local(new_home)

                # Ensure PATH bin is present for this process (matches system PATH)
                binp = str(Path(new_home) / "bin")
                if binp not in os.environ.get("PATH", ""):
                    os.environ["PATH"] = binp + ";" + os.environ.get("PATH", "")
                    
                    
                STATE["java_version"] = Path(new_home).name
                _save_java_cfg_local(STATE["java_version"], new_home)
                p(f"🔄 Reloaded Java from registry: {new_home}")
                p(f"✅ Now active: {STATE['java_version']}")
            else:
                p("[yellow]⚠️ No JAVA_HOME found in registry (user or system).[/yellow]")
        except Exception as e:
            p(f"[red]Reload failed:[/red] {e}")
        return
        
        
    
  
     # ---------- Improved Java change ----------
    m = re.match(r"^java\s+change\s+(.+)$", s, re.I)
    if m:
        arg = m.group(1).strip().strip('"').strip("'")
        target_path = None
        chosen_key = None

        # 1. Try direct key match (version or name)
        if arg in JAVA_VERSIONS:
            target_path = JAVA_VERSIONS[arg]
            chosen_key = arg
        else:
            # 2. Try partial match (e.g. "17" matches "jdk-17.0.x")
            for k, v in JAVA_VERSIONS.items():
                if arg in k or arg in v:
                    target_path = v
                    chosen_key = k
                    break

        # 3. If still not found, maybe it's a full path
        if not target_path and Path(arg).exists():
            target_path = arg
            chosen_key = Path(arg).name

        if not target_path or not Path(target_path).exists():
            p(f"[red]Java version or path not found:[/red] {arg}")
            return

        # ---- Apply to current process (CMC runtime only) ----
        java_bin = str(Path(target_path) / "bin")
        os.environ["JAVA_HOME"] = target_path
        if java_bin not in os.environ.get("PATH", ""):
            os.environ["PATH"] = os.environ.get("PATH", "") + f";{java_bin}"

        STATE["java_version"] = chosen_key or arg
        _save_java_cfg_local(STATE["java_version"], target_path)

        # ---- Tier 1: Set user-level JAVA_HOME and user Path (no admin needed) ----
        try:
            import winreg as _wr
            _hkcu_env = r"Environment"

            # Set user JAVA_HOME
            with _wr.OpenKey(_wr.HKEY_CURRENT_USER, _hkcu_env, 0, _wr.KEY_READ | _wr.KEY_WRITE) as _k:
                _wr.SetValueEx(_k, "JAVA_HOME", 0, _wr.REG_EXPAND_SZ, target_path)

                # Update user Path: strip old java/jdk entries, prepend new bin
                try:
                    _cur_path, _ = _wr.QueryValueEx(_k, "Path")
                except FileNotFoundError:
                    _cur_path = ""
                _parts = [e for e in _cur_path.split(";") if e.strip() and
                          "java" not in e.lower() and "jdk" not in e.lower()]
                _parts.insert(0, java_bin)
                _wr.SetValueEx(_k, "Path", 0, _wr.REG_EXPAND_SZ, ";".join(_parts))

            p(f"[green]✔ User JAVA_HOME → {target_path}[/green]" if RICH else f"User JAVA_HOME -> {target_path}")
            p(f"[green]✔ User Path updated (java bin prepended)[/green]" if RICH else "User Path updated.")
        except Exception as e:
            p(f"[yellow]Could not set user environment:[/yellow] {e}" if RICH else f"Could not set user environment: {e}")

        # ---- Tier 2: Try system-level (needs admin) ----
        try:
            import winreg
            reg_path = r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"

            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE, reg_path, 0,
                winreg.KEY_READ | winreg.KEY_WRITE,
            ) as key:
                current_path, _ = winreg.QueryValueEx(key, "Path")
                parts = current_path.split(";")
                parts = [
                    entry for entry in parts
                    if "java" not in entry.lower() and "jdk" not in entry.lower()
                ]
                parts.insert(0, java_bin)
                new_path = ";".join(parts)
                winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_path)

            subprocess.run(
                ["setx", "JAVA_HOME", target_path, "/M"],
                shell=True, check=True, text=True, capture_output=True,
            )
            p(f"[green]Java set system-wide to: {chosen_key or target_path}[/green]" if RICH else f"Java set system-wide to: {chosen_key or target_path}")
            p("Restart terminals and launchers to apply PATH changes.")

        except PermissionError:
            # ---- Tier 3: Request UAC elevation via PowerShell ----
            p("[yellow]Admin rights needed for system PATH. Requesting elevation...[/yellow]" if RICH else "Admin rights needed. Requesting elevation...")
            ps_script = (
                f'$ErrorActionPreference = "Stop"; '
                f'& setx JAVA_HOME "{target_path}" /M; '
                f'$regPath = "HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment"; '
                f'$cur = (Get-ItemProperty -Path $regPath -Name Path).Path; '
                f'$parts = $cur -split ";" | Where-Object {{ $_ -and $_.ToLower() -notmatch "java|jdk" }}; '
                f'$newPath = "{java_bin};" + ($parts -join ";"); '
                f'Set-ItemProperty -Path $regPath -Name Path -Value $newPath -Type ExpandString'
            )
            try:
                import ctypes
                ret = ctypes.windll.shell32.ShellExecuteW(
                    None, "runas", "powershell.exe",
                    f'-NoProfile -ExecutionPolicy Bypass -Command "{ps_script}"',
                    None, 1,
                )
                if ret > 32:
                    p("[green]Elevation requested — check the admin window.[/green]" if RICH else "Elevation requested - check the admin window.")
                else:
                    p("[red]Elevation was denied or failed.[/red]" if RICH else "Elevation was denied or failed.")
            except Exception as e2:
                p(f"[red]Could not request elevation:[/red] {e2}" if RICH else f"Could not request elevation: {e2}")

        except Exception as e:
            p(f"[yellow]System-level Java update failed:[/yellow] {e}" if RICH else f"System-level Java update failed: {e}")
            p("User-level JAVA_HOME was set. For system-wide, run CMC as admin.")

        return


        
            # ---------- System Info ----------
    m = re.match(r"^sysinfo(?:\s+save\s+'(.+?)')?$", s, re.I)
    if m:
        op_sysinfo(m.group(1))
        return

        
            # ---------- File & Info operations ----------
    # list ['path']
    m = re.match(r"^list(?:\s+'(.+?)')?$", s, re.I)
    if m:
        op_list(m.group(1) if m.group(1) else None); return

    # info 'path'
    m = re.match(r"^info\s+'(.+?)'$", s, re.I)
    if m:
        op_info(m.group(1)); return

    # find 'name'
    m = re.match(r"^find\s+'(.+?)'$", s, re.I)
    if m:
        op_find_name(m.group(1)); return

    # findext '.ext'
    m = re.match(r"^findext\s+'?(\.[A-Za-z0-9]+)'?$", s, re.I)
    if m:
        op_find_ext(m.group(1)); return

    # recent ['path']
    m = re.match(r"^recent(?:\s+'(.+?)')?$", s, re.I)
    if m:
        op_recent(m.group(1) if m.group(1) else None); return

    # biggest ['path']
    m = re.match(r"^biggest(?:\s+'(.+?)')?$", s, re.I)
    if m:
        op_biggest(m.group(1) if m.group(1) else None); return

    # search 'text'
    m = re.match(r"^search\s+'(.+?)'$", s, re.I)
    if m:
        op_search_text(m.group(1)); return

    # create file 'name.txt' in 'C:/path' [with text="..."]
    m = re.match(r"^create\s+file\s+'(.+?)'\s+in\s+'(.+?)'(?:\s+with\s+text=['\"](.+?)['\"])?$", s, re.I)
    if m:
        op_create_file(m.group(1), m.group(2), m.group(3)); return

    # create folder 'Name' in 'C:/path'
    m = re.match(r"^create\s+folder\s+'(.+?)'\s+in\s+'(.+?)'$", s, re.I)
    if m:
        op_create_folder(m.group(1), m.group(2)); return

    # write 'C:/path/file.txt' text='hello'
    m = re.match(r"^write\s+'(.+?)'\s+text=['\"](.+?)['\"]$", s, re.I)
    if m:
        op_write(m.group(1), m.group(2)); return

    # read 'C:/path/file.txt' [head=50]
    m = re.match(r"^read\s+'(.+?)'(?:\s+\[head=(\d+)\])?$", s, re.I)
    if m:
        op_read(m.group(1), int(m.group(2)) if m.group(2) else None); return

    # move 'C:/src' to 'C:/dst'
    m = re.match(r"^move\s+'(.+?)'\s+to\s+'(.+?)'$", s, re.I)
    if m:
        op_move(m.group(1), m.group(2)); return

    # copy 'C:/src' to 'C:/dst'
    m = re.match(r"^copy\s+'(.+?)'\s+to\s+'(.+?)'$", s, re.I)
    if m:
        op_copy(m.group(1), m.group(2)); return

    # rename 'C:/old' to 'NewName'
    m = re.match(r"^rename\s+'(.+?)'\s+to\s+'(.+?)'$", s, re.I)
    if m:
        op_rename(m.group(1), m.group(2)); return

    # delete 'C:/path'
    m = re.match(r"^delete\s+'(.+?)'$", s, re.I)
    if m:
        op_delete(m.group(1)); return

     

    # zip 'C:/path' or zip 'C:/path' to 'C:/dest'
    m = re.match(r"^zip\s+'([^']+)'(?:\s+to\s+'([^']+)')?$", s, re.I)
    if m:
        src = m.group(1)
        dest = m.group(2)
        if dest:
            op_zip(src, dest)
        else:
            # default: zip to same folder
            from pathlib import Path
            p = Path(src)
            op_zip(src, str(p.parent))
        return

        # unzip 'C:/file.zip' or unzip 'C:/file.zip' to 'C:/dest'
    m = re.match(r"^unzip\s+'([^']+)'(?:\s+to\s+'([^']+)')?$", s, re.I)
    if m:
        zip_path = m.group(1)
        dest = m.group(2)
        if dest:
            op_unzip(zip_path, dest)
        else:
            from pathlib import Path
            p = Path(zip_path)
            op_unzip(zip_path, str(p.parent))
        return



    # open 'C:/file-or-app'
    m = re.match(r"^open\s+'(.+?)'$", s, re.I)
    if m:
        op_open(m.group(1)); return

    # explore 'C:/path'
    m = re.match(r"^explore\s+'(.+?)'$", s, re.I)
    if m:
        op_explore(m.group(1)); return

    # backup 'C:/src' 'C:/dest'
    m = re.match(r"^backup\s+'(.+?)'\s+'(.+?)'$", s, re.I)
    if m:
        op_backup(m.group(1), m.group(2)); return

    # ---------- Internet ----------
    # open url https://example.com  OR  open url 'https://...'
    m = re.match(r"^open\s+url\s+(?:'([^']+)'|(\S+))$", s, re.I)
    if m:
        url = m.group(1) or m.group(2)
        op_open_url(url); return

    # download 'https://...' to 'C:/Downloads'
    m = re.match(r"^download\s+'(.+?)'\s+to\s+'(.+?)'$", s, re.I)
    if m:
        op_download(m.group(1), m.group(2)); return

    # downloadlist 'C:/urls.txt' to 'C:/Downloads'
    m = re.match(r"^downloadlist\s+'(.+?)'\s+to\s+'(.+?)'$", s, re.I)
    if m:
        op_download_list(m.group(1), m.group(2)); return

    # ---------- Run (already have your improved version; keep if missing) ----------
    # run 'cmd or path' [in 'folder']
    m = re.match(r"^run\s+'(.+?)'\s*(?:in\s+'([^']+)')?$", s, re.I)
    if m:
        full_cmd = m.group(1).strip()
        import pathlib
        workdir = pathlib.Path(m.group(2)).expanduser() if m.group(2) else None
        try:
            cwd = str(workdir) if workdir else None
            subprocess.Popen(full_cmd, cwd=cwd, shell=True)
            p(f"🚀 Launched: {full_cmd}" + (f" (cwd={cwd})" if cwd else ""))
        except Exception as e:
            p(f"[red]❌ Failed to run:[/red] {e}")
        return
        
            # ---------- Navigation ----------
    if low in ("home", "cd home"):
        op_home(); return

    if low == "back":
        op_back(); return

    if low in ("cd", "cd ~"):
        op_home(); return

    if low in ("cd ..", "..", "cd..", "../"):
        op_cd(str(CWD.parent)); return

    m = re.match(r"^cd\s+'(.+?)'$", s, re.I)
    if m:
        op_cd(m.group(1)); return

    # cd without quotes (unquoted path)
    m = re.match(r"^cd\s+(\S+)$", s, re.I)
    if m:
        op_cd(m.group(1)); return

    if low == "pwd":
        op_pwd(); return

    # ---------- Backup ----------
    m = re.match(r"^backup\s+'(.+?)'\s+'(.+?)'$", s, re.I)
    if m:
        op_backup(m.group(1), m.group(2)); return

    # ---------- Log / Undo ----------
    if low == "log":
        op_log(); return

    if low == "undo":
        op_undo(); return




    # ---------- Macros (inline) ----------
    m = re.match(r"^macro\s+add\s+([A-Za-z0-9_\-]+)\s*=\s*(.+)$", s, re.I)
    if m: macro_add(m.group(1), m.group(2)); return
    m = re.match(r"^macro\s+run\s+([A-Za-z0-9_\-]+)$", s, re.I)
    if m: macro_run(m.group(1)); return
    m = re.match(r"^macro\s+edit\s+([A-Za-z0-9_\-]+)$", s, re.I)
    if m: macro_edit(m.group(1)); return
    m = re.match(r"^macro\s+delete\s+([A-Za-z0-9_\-]+)$", s, re.I)
    if m: macro_delete(m.group(1)); return
    if re.match(r"^macro\s+list$", s, re.I): macro_list(); return
    if re.match(r"^macro\s+clear$", s, re.I): macro_clear(); return

    # ---------- Ports ----------
    if low == "ports":
        op_ports(p); return
    m = re.match(r"^kill\s+(\d+)$", s, re.I)
    if m:
        op_kill_port(int(m.group(1)), p); return
    
        # ---------- File Operations ----------
    m = re.match(r"^create\s+file\s+'(.+?)'\s+in\s+'(.+?)'(?:\s+with\s+text=['\"](.+?)['\"])?$", s, re.I)
    if m:
        op_create_file(m.group(1), m.group(2), m.group(3))
        return

    m = re.match(r"^create\s+folder\s+'(.+?)'\s+in\s+'(.+?)'$", s, re.I)
    if m:
        op_create_folder(m.group(1), m.group(2))
        return

    m = re.match(r"^write\s+'(.+?)'\s+text=['\"](.+?)['\"]$", s, re.I)
    if m:
        op_write(m.group(1), m.group(2))
        return

    m = re.match(r"^read\s+'(.+?)'(?:\s+\[head=(\d+)\])?$", s, re.I)
    if m:
        op_read(m.group(1), int(m.group(2)) if m.group(2) else None)
        return

    m = re.match(r"^move\s+'(.+?)'\s+to\s+'(.+?)'$", s, re.I)
    if m:
        op_move(m.group(1), m.group(2))
        return

    m = re.match(r"^copy\s+'(.+?)'\s+to\s+'(.+?)'$", s, re.I)
    if m:
        op_copy(m.group(1), m.group(2))
        return

    m = re.match(r"^rename\s+'(.+?)'\s+to\s+'(.+?)'$", s, re.I)
    if m:
        op_rename(m.group(1), m.group(2))
        return

    m = re.match(r"^delete\s+'(.+?)'$", s, re.I)
    if m:
        op_delete(m.group(1))
        return


    # ---------- Navigation ----------
    # (keep your existing navigation / file ops / java / index handlers here...)

    # ---------- Internet ----------
    m = re.match(r"^open\s+url\s+(?:'([^']+)'|(\S+))$", s, re.I)
    if m:
        url = m.group(1) or m.group(2)
        op_open_url(url)
        return

    # ---------- Web search (default browser e.g. Brave) ----------
    m = re.match(r"^search\s+web\s+(.+)$", s, re.I)
    if m:
        q = m.group(1).strip()
        if q:
            url = "https://www.google.com/search?q=" + urllib.parse.quote_plus(q)
            webbrowser.open(url)
            p(f"[cyan]🌐 Opened Google search for:[/cyan] {q}")
        else:
            p("Usage: search web <text>")
        return

    # ---------- Web search (opens your default browser e.g., Brave) ----------
    m = re.match(r"^search\s+web\s+(.+)$", s, re.I)
    if m:
        q = m.group(1).strip()
        if q:
            url = "https://www.google.com/search?q=" + urllib.parse.quote_plus(q)
            webbrowser.open(url)
            p(f"[cyan]🌐 Opened Google search for:[/cyan] {q}")
        else:
            p("Usage: search web <text>")
        return
        
    # ---------- Local Path Index: Super Fuzzy Search ----------
    # /find <terms> [limit]
    m = re.match(r"^/find\s+(.+?)(?:\s+(\d+))?$", s, re.I)
    if m:
        terms = m.group(1)
        limit = int(m.group(2)) if m.group(2) else 20
        try:
            from path_index_local import super_find
            results = super_find(terms, limit)
            if results:
                p(f"[cyan]Top {len(results)} fuzzy matches for '{terms}':[/cyan]")
                for r in results:
                    score = r.get("score", 0)
                    path = r.get("path", "")
                    p(f"[yellow]{score:>3}%[/yellow]  {path}")
            else:
                p(f"[yellow]No matches found for '{terms}'.[/yellow]")
        except Exception as e:
            p(f"[red]Super-find error:[/red] {e}")
        return
        
        



    # /qcount
    if re.match(r"^/qcount$", s, re.I):
        try:
            from path_index_local import quick_count
            count = quick_count()
            p(f"📁 Indexed paths: {count}")
        except Exception as e:
            p(f"[red]Quick-count error:[/red] {e}")
        return

    # /build [targets...]
    m = re.match(r"^/build(?:\s+(.+))?$", s, re.I)
    if m:
        targets = m.group(1)
        try:
            from path_index_local import quick_build
            quick_build(targets)
        except Exception as e:
            p(f"[red]Quick-build error:[/red] {e}")
        return



    # ---------- CMD passthrough ----------
    # Opens a real Windows Command Prompt session inside the same window.
    # Type 'exit' to return back to CMC after using normal CMD commands.
    if low == "cmd":
        if STATE.get("dry_run"):
            p("[yellow]DRY-RUN:[/yellow] CMD session skipped.")
            return
        if not STATE.get("batch"):
            if not confirm("Open a full CMD session? You can type 'exit' to return to CMC."):
                p("[yellow]Canceled.[/yellow]")
                return
        try:
            p("[cyan]Entering Windows CMD mode — type 'exit' to return to CMC.[/cyan]")
            os.system("cmd")
            p("[cyan]Returned from CMD mode.[/cyan]")
        except Exception as e:
            p(f"[red]❌ CMD session failed:[/red] {e}")
        return


    # Unknown / partial
    suggest_commands(s)

# ---------- Help ----------

def show_help(topic: str | None = None) -> None:
    """
    Category-based help.

    - `help`           -> show categories menu
    - `help 4`         -> show Disk space & cleanup
    - `help macros`    -> same as help 5
    - `help git`       -> git help
    - `help all`       -> show everything
    """

    def _panel(title: str, body: str) -> None:
        if RICH:
            console.print(Panel(body.rstrip("\n"), title=title, border_style="cyan"))
        else:
            print("\n" + "=" * 60)
            print(title)
            print("=" * 60)
            print(body)

    # ---------- SECTION TEXTS (verified syntax) ----------

    sec1 = """
[bold]1. Basics & Navigation[/bold]
-----------------------------------

Movement:
• cd <path>                       Change directory
• cd ..                           Go up one folder
• cd                              Go to HOME
• home                            Go to HOME (explicit)
• back                            Go to previous directory
• list                            List current folder
• pwd                             Show current path

Opening:
• open '<file>'                   Open file in default program
• explore '<folder>'              Open folder in Explorer

Examples:
  cd C:/Users/Wiggo/Desktop
  cd ..
  list
  pwd
  explore 'C:/Users/Wiggo/Downloads'
"""

    sec2 = """
[bold]2. Files & Folders[/bold]
-----------------------------------

Viewing:
• read '<file>'

Creating:
• create folder '<name>' in '<path>'
• create file '<name>' in '<path>'

Copy / Move / Rename (REAL SYNTAX):
• copy '<src>' to '<dst>'
• move '<src>' to '<dst>'
• rename '<src>' to '<dst>'      (alias for move)

Delete:
• delete '<path>'                 Safe unless batch ON

Zip tools (REAL SYNTAX):
• zip '<source>' to '<destination-folder>'
• unzip '<zipfile>' to '<destination-folder>'

Backup (REAL SYNTAX):
• backup '<source>' '<destination-folder>'

Examples:
  create folder 'Logs' in 'C:/Servers/MyPack'
  copy 'C:/A/file.txt' to 'C:/B/file.txt'
  move 'notes.txt' to 'archive/notes.txt'
  zip 'C:/Project' to 'C:/Backups'
  unzip 'C:/Project.zip' to 'C:/Unpacked'
  backup 'C:/Project' 'C:/Backups/ProjectBackup'
"""

    sec3 = """
[bold]3. Search & Indexing[/bold]
-----------------------------------

Folder-level search (current folder):
• find '<name>'                   Find files/folders by name — any partial match works
• findext '.ext'                  Filter by extension (example: '.json')
• recent                          Show newest files
• biggest                         Show largest files

Inside-file search:
• search '<text>'                 Search contents inside files

Quick Path Index (fast global fuzzy search):
• /build <drive letters...>
  Build/update the path index for the given drives.
  Example:
    /build C D E

• /find <query>
  Global fuzzy-style search using the index (fast).
  Example:
    /find Atlauncher Server

Notes:
• Run /build first (once per machine, rerun if drives change).

Examples:
  find 'log'
  find '.py'
  find 'test'
  findext '.json'
  search 'error'
  /build C D
  /find NBTExplorer 2.8
"""

    sec4 = """
[bold]4. Disk Space & Cleanup[/bold]
------------------------------------

Analyze folders + optional AI cleanup suggestions.

Usage:
  space                             Analyze current folder
  space '<path>'                    Analyze specific folder
  space '<path>' depth <n>          Depth = 1–6
  space '<path>' depth <n> report   Write CMC_space_report.txt

Examples:
  space
  space 'C:/Users/Wiggo/Desktop'
  space 'C:/Servers/MyPack' depth 3
  space 'C:/Downloads' depth 4 report
"""

    sec5 = """
[bold]5. Macros[/bold]
-----------------------------------

Macros = saved automation (comma-separated chains).

Commands:
• macro add <name> = <command>     Save a new macro
• macro run <name>                 Run a macro
• macro edit <name>                Edit a macro in a pre-filled prompt (clickable!)
• macro delete <name>              Delete a macro
• macro list                       List all saved macros
• macro clear                      Delete all macros

Tips:
• Use single quotes around paths in macros.
• Use variables: %HOME% %DATE% %NOW%
• macro edit opens the existing command pre-filled — just change what you need.

Examples:
  macro add desk = cd '%HOME%/Desktop'
  macro add publish = copy 'Computer_Main_Centre.py' to 'C:/Public/Computer_Main_Centre.py'
  macro run desk
  macro edit desk
"""


    sec6 = """
[bold]6. Aliases[/bold]
-----------------------------------

Aliases = shortcuts for single commands.

• alias add <name> = <command>
• alias list
• alias delete <name>

Rules:
  - Only ONE command allowed.
  - No commas (single command only).
  - Cannot override built-in commands.

Examples:
  alias add dl = explore '%HOME%/Downloads'
"""

    sec7 = """
    
[bold]7. Git (GitHub publishing)[/bold]
-----------------------------------

CMC provides a simplified Git workflow focused on fast publishing.
You usually do NOT need normal git commands.

[bold]Core commands[/bold]

• git upload
  Create a new GitHub repository from the current folder.
  Asks for repo name, public/private, and commit message.
  Automatically initializes git (if needed), commits, pushes,
  saves the folder → repo mapping, and opens the repo in the browser.

• git update
  Commit and push changes from the current folder to its linked repository.
  Uses the saved folder → repo mapping automatically.

• git update "<message>"
  Commit + push using a commit message (without changing the repo link).
  Tip: If your message has spaces, wrap it in quotes.

• git update <owner>/<repo> ["message"]
  Commit and push the current folder to a specific GitHub repo.
  Useful for relinking the folder or pushing to a different repo.

• git update <owner>/<repo> ["message"] --add <file/folder>
  Commit and push ONLY the specified file/folder (partial commit).
  Other changes are ignored.

• git download <owner>/<repo>
  Download (clone) any GitHub repository into the current CMC folder.
  Works with public repos and private repos you have access to.
  Simplified alternative to git clone.

• git link <owner>/<repo>
  Link the current folder to an existing GitHub repository.
  Required for GitHub Classroom and organization repositories.

[bold]Self-healing commands (recommended when git is cursed)[/bold]

• git force upload
  Like git upload, but tries to auto-fix common problems:
  - missing repo init
  - wrong branch / missing main
  - missing first commit (refspec issues)
  - index.lock problems
  - origin mismatch (when a real repo is provided)
  If it still fails, it creates a big debug report file.

• git force update [<owner>/<repo>] ["message"] [--add <file/folder>]
  Like git update, but aggressively repairs common issues and retries push.
  Uses pull --rebase when needed and may use force-with-lease as last resort.

• git debug upload / git debug update ...
  Same as force, but also prints the steps it performed.

[bold]Branch management[/bold]

• git branch list               List all branches (local + remote)
• git branch create <name>      Create a new branch and switch to it
• git branch switch <name>      Switch to an existing branch
• git branch delete <name>      Delete a branch
• git branch merge <name>       Merge a branch into your current branch

[bold]Diagnostics / extras[/bold]

• git status
  Show current Git status (changed, staged, clean).

• git log
  Show recent commits (short format).

• git doctor
  Diagnostic command.
  Shows:
   - which folder CMC is using
   - detected repository root
   - whether Git is installed
   - whether a GitHub token is stored
   - saved folder → repository mapping
   - origin remote info (if present)

• git repo list [all|mine]
  List GitHub repositories accessible by your account
  (includes Classroom, forks, and organization repos).

• git repo delete <owner>/<repo>   (or: git repo delete <repoName>)
  Permanently delete a GitHub repository you own.
  Requires typing DELETE to confirm.
  This action is irreversible.

Notes:
• Git commands use the CMC working directory (shown in the prompt).
• GitHub token is requested once and stored locally.
• Empty folders are not tracked by Git.
• CMC creates/updates a .gitignore (rules are always respected).
• Repository deletion affects GitHub only (local files are untouched).
• GitHub Classroom repos may require `git pull` before `git update`.
• If you see an origin containing "<you>", fix it with `git link owner/repo`.

Examples:
  git upload
  git update
  git update "Update 1"
  git update MyAcc/MyRepo "Update 2"
  git update MyAcc/MyRepo "Update only one file" --add src/main.py
  git force upload
  git force update
  git debug update MyAcc/MyRepo "Debugging this push"
  git download MyAcc/Test123
  git link OrgOrOwner/RepoName
  git repo list
  git repo delete MyAcc/OldTestRepo
  git status
  git doctor
  git branch list
  git branch create my-feature
  git branch switch main
"""





    sec8 = """
[bold]8. Java [/bold]
-----------------------------------

Java:
• java list
• java version
• java change <8|17|21>
• java reload

Examples:
  java list
  java change 17
"""

    sec9 = """
[bold]9. Automation & Execution[/bold]
-----------------------------------

Run programs / scripts:
• run '<path>'
• run '<script>' in '<folder>'

Rules:
• Paths MUST be wrapped in single quotes.
• Use `in '<folder>'` when the program needs a working directory.

Supported:
.py, .exe, .bat, .cmd, .vbs with proper working directory.

Examples:
  run 'script.py'
  run 'start_server.bat' in 'C:/Servers/Forge'
  run 'mcreator.exe' in 'C:/MCreator_1.9.1/MCreator191'
  run 'C:/Tools/MyApp/app.exe'

Timing:
• sleep <seconds>
• timer <seconds> [message]

Input:
• sendkeys "<text>{ENTER}"

Ports & processes:
• ports                           Show all listening ports with PID and process name
• kill <port>                     Kill whatever process is running on that port

Examples:
  ports
  kill 3000
  kill 5173
"""

    sec10 = """
[bold]10. Web & Downloads[/bold]
-----------------------------------

Browser helpers:
• search web <query>               Open a browser search

Downloads:
• download '<url>' ['<file>']      Download a file (optional output name)
• download_list '<txtfile>'        Download many URLs listed in a text file

Open:
• open '<file/URL>'                    Opens a local file or URL

Flags:
  ssl on/off
  dry-run on/off

Examples:
  download 'https://example.com/app.zip' 'app.zip'
  download_list '%HOME%/Desktop/links.txt'
  search web "java install"
"""


    sec11 = """
[bold]11. Project setup & dev tools[/bold]
-----------------------------------

Create a new project from scratch:
• new python                       Python script/CLI (venv + requirements.txt)
• new node                         Node.js project
• new flask                        Flask REST API (venv + CORS + .env)
• new fastapi                      FastAPI project (venv + uvicorn + /docs)
• new react                        React + Vite
• new vue                          Vue 3 + Vite
• new svelte                       Svelte + Vite
• new next                         Next.js (via create-next-app)
• new electron                     Electron desktop app
• new discord                      Discord.py bot skeleton
• new cli                          Python CLI tool (argparse)
• new web                          Full-stack web app (pick frontend + backend)

Set up an existing project (auto-detects type):
• setup                            Install deps, copy .env, offer to start server

Dev server (smart launcher — opens browser automatically):
• dev                              Auto-detect project + start + open browser
• dev <script>                     Run a specific package.json script
• dev stop                         Kill the last dev server launched by CMC

.env file manager:
• env list                         List all keys in .env (values hidden)
• env show                         List all keys and values
• env get <KEY>                    Show one value
• env set KEY=value                Add or update a key
• env delete <KEY>                 Remove a key
• env template                     Create .env.example (values blanked)
• env check                        Compare .env vs .env.example

Examples:
  new flask
  new react
  setup
  dev
  dev build
  new web
  env set PORT=3000
  env check
"""

    sec12 = """
[bold]8. AI (Local assistant & models)[/bold]
-----------------------------------

CMC can run a local AI assistant (Ollama-based) and lets you control the model.
The AI knows your current folder, recent log, macros and aliases — so answers are contextual.
It also remembers your last few messages in the session (follow-up questions work).

• ai <question>
  Ask the assistant. Answers are short by default — ask for detail if you need more.
  Examples:
    ai how do I zip this folder and push to git?
    ai what macros do I have?

• ai fix
  If a command just failed, 'ai fix' automatically passes the error to the AI
  and asks what went wrong and how to fix it.

• ai clear
  Wipe the conversation history and start fresh.

• model list
  List installed local models (from `ollama list`).

• model current
  Show the model CMC is currently configured to use.

• model set <model>
  Switch the active model used by CMC. Also clears conversation history.
  Examples:
    ai-model set llama3.1:8b
    ai-model set qwen2.5:14b-instruct


Notes:
• If Ollama is not installed or running, model listing may fail.
• To install models: open CMC_AI_Ollama_Setup.cmd from your CMC folder.
• Model names must match `ollama list`.
• `status` shows the current AI model.


Examples:
  ai hello, what can you do?
  ai-model list
  ai-model current
  ai-model set llama3.1:8b
  model set qwen2.5:14b-instruct
"""


    sec13 = """
[bold]12. Flags, Modes & Config[/bold]
-----------------------------------

Modes:
• batch on/off                     Auto-confirm prompts
• dry-run on/off                   Preview actions without executing
• ssl on/off                       Toggle SSL verification for downloads

Config system:
• config list
• config get <key>
• config set <key> <value>
• config reset

Examples:
  batch on
  dry-run off
  ssl off
  config list
  config set batch on
  config get space.default_depth
"""

    sec14 = """
[bold]14. Docker[/bold]
-----------------------------------

Containers:
• docker ps                        List running containers
• docker ps all                    List all containers (including stopped)
• docker start <name>              Start a stopped container
• docker stop <name>               Stop a running container
• docker restart <name>            Restart a container
• docker remove <name>             Stop + remove a container in one step
• docker shell <name>              Open interactive shell inside container
• docker logs <name>               Show last 50 log lines
• docker logs follow <name>        Stream logs live (Ctrl+C to stop)
• docker stats                     Live CPU/memory for all containers
• docker stats <name>              Live stats for one container
• docker inspect <name>            Show container or image details
• docker ip <name>                 Show container IP address

Images:
• docker images                    List local images
• docker pull <image>              Pull image from Docker Hub
• docker push <image>              Push image to registry
• docker build <tag>               Build image from Dockerfile in current folder
• docker build <tag> <path>        Build image from Dockerfile at path

Run:
• docker run <image>               Run interactively (removed on exit)
• docker run <image> -d            Run in background (detached)
• docker run <image> -p 8080:80    Map port host:container
• docker run <image> -e KEY=VAL    Set environment variable
• docker run <image> -n myname     Assign a name

Compose (run from folder with docker-compose.yml):
• docker compose up                Build and start all services in background
• docker compose down              Stop and remove all services
• docker compose logs              Show last 50 lines from all services
• docker compose logs follow       Stream logs live
• docker compose build             Rebuild all images (no cache)
• docker compose ps                List compose services and their status
• docker compose restart           Restart all services

Volumes & Networks:
• docker volumes                   List volumes
• docker volume remove <name>      Remove a volume
• docker networks                  List networks
• docker network remove <name>     Remove a network

Cleanup:
• docker clean                     Remove stopped containers + dangling images
• docker clean all                 Full system prune (containers, images, volumes, networks)

• docker doctor                    Check Docker installation and daemon status

Examples:
  docker ps
  docker shell myapp
  docker logs follow myapp
  docker build myapp:v1
  docker run nginx -p 8080:80 -d
  docker compose up
  docker clean
"""

    # ---------- Section Map ----------
    sections = {
        "1": ("Basics & navigation", sec1),
        "2": ("Files & folders", sec2),
        "3": ("Search", sec3),
        "4": ("Disk space & cleanup", sec4),
        "5": ("Macros", sec5),
        "6": ("Aliases", sec6),
        "7": ("Git helpers", sec7),
        "8": ("Java & servers", sec8),
        "9": ("Automation", sec9),
        "10": ("Web & downloads", sec10),
        "11": ("Project setup & dev tools", sec11),
        "12": ("AI models & commands", sec12),
        "13": ("Flags & modes", sec13),
        "14": ("Docker", sec14),
    }

    # ---------- Aliases ----------
    aliases = {
        "basic": "1", "basics": "1", "nav": "1", "navigation": "1",
        "file": "2", "files": "2", "folders": "2",
        "search": "3", "find": "3", "path": "3",
        "space": "4", "disk": "4", "cleanup": "4",
        "macro": "5", "macros": "5",
        "alias": "6", "aliases": "6",
        "git": "7", "branch": "7", "branches": "7",
        "java": "8",
        "server": "8", "servers": "8",
        "auto": "9", "automation": "9", "ports": "9", "port": "9", "kill": "9",
        "web": "10", "downloads": "10",
        "project": "11", "scaffold": "11", "new": "11", "dev": "11", "env": "11", "setup": "11",
        "ai": "12", "model": "12", "models": "12", "ollama": "12",
        "flags": "13", "mode": "13", "modes": "13",
        "batch": "13", "ssl": "13", "dry-run": "13",
        "docker": "14", "container": "14", "containers": "14", "compose": "14",
    }

    # ---------- No topic: Show menu ----------
    if not topic:
        menu = """
Type `help <number>` to open a section or use: help all

  1. Basics & navigation
  2. Files & folders
  3. Search
  4. Disk space & cleanup
  5. Macros
  6. Aliases
  7. Git helpers
  8. Java & servers
  9. Automation
 10. Web & downloads
 11. Project setup & dev tools
 12. AI models & commands
 13. Flags & modes
 14. Docker

"""
        _panel("CMC Help – categories", menu)
        return

    # ---------- Resolve aliases ----------
    key = topic.strip().lower()
    key = aliases.get(key, key)

    # ---------- Show all ----------
    if key in ("all", "full", "everything"):
        for num in sorted([int(k) for k in sections]):
            k = str(num)
            t, b = sections[k]
            _panel(f"{k}. {t}", b)
        return

    # ---------- Single section ----------
    if key in sections:
        title, body = sections[key]
        _panel(f"{key}. {title}", body)

    else:
        _panel(
            "CMC Help",
            f"Unknown help topic: {topic!r}\n\nType just `help` to see available categories."
        )






# ---------- Main loop ----------
def split_commands(line: str):
    """
    Splits chained commands separated by commas (,)
    but keeps whole lines for 'macro add' and 'timer' commands.
    Commas inside quoted strings are NOT treated as separators.
    """
    parts = []
    buf = []
    q = None
    in_macro_add = False
    i = 0

    line = line.rstrip()
    if not line:
        return []

    # if it's a timer command, never split it
    if line.lower().startswith("timer "):
        return [line]

    while i < len(line):
        ch = line[i]

        if q:
            # we're inside a quoted string
            if ch == q:
                q = None
            buf.append(ch)
        else:
            # not in quotes
            if not in_macro_add:
                temp = "".join(buf).lstrip().lower()
                if temp.startswith("macro add"):
                    in_macro_add = True

            if ch in ("'", '"'):
                q = ch
                buf.append(ch)
            elif ch == "," and not in_macro_add:
                part = "".join(buf).strip()
                if part:
                    parts.append(part)
                buf = []
            else:
                buf.append(ch)

        i += 1

    # append any remaining buffer once
    final = "".join(buf).strip()
    if final:
        parts.append(final)

    return parts



import shlex


# ---------- Command Autocompletion ----------

def complete_path(text, state):
    """Auto-complete file and folder paths when typing quoted paths."""
    if text.startswith(("'", '"')):
        quote = text[0]
        text = text[1:]
    else:
        quote = ''

    pattern = text + '*' if text else '*'
    matches = glob.glob(pattern)
    results = [f"{quote}{m.replace('\\', '/')}" for m in matches]

    # Append a trailing slash for directories
    results = [r + ('/' if os.path.isdir(r.strip("'\"")) else '') for r in results]
    return results[state] if state < len(results) else None


def complete_command(text, state):
    """Autocomplete for commands, macros, git commands, and paths."""
    cmds = [
    # Navigation / info
    "pwd", "cd", "back", "home", "list", "info", "find", "findext",
    "recent", "biggest", "search", "ai",

    # File operations
    "create file", "create folder", "write", "read", "move", "copy",
    "rename", "delete", "zip", "unzip", "open", "explore", "backup",
    "run",

    # Internet
    "download", "open url",
    "search web",

    # Modes / safety
    "batch on", "batch off", "dry-run on", "dry-run off",
    "ssl on", "ssl off", "status", "log", "undo",

    # Macros
    "macro add", "macro run", "macro edit", "macro list", "macro delete", "macro clear",

    # Ports
    "ports", "kill",

    # Git
    "/gitsetup", "/gitlink", "/gitupdate", "/gitpull", "/gitstatus",
    "/gitlog", "/gitbranch", "/gitignore add", "/gitclean", "/gitdoctor",
    "/gitfix", "/gitlfs setup",
    "git branch", "git branch list", "git branch create", "git branch switch",
    "git branch delete", "git branch merge",

    # Docker
    "docker ps", "docker ps all", "docker images",
    "docker start", "docker stop", "docker restart", "docker remove",
    "docker shell", "docker logs", "docker logs follow",
    "docker stats", "docker inspect", "docker ip",
    "docker build", "docker pull", "docker push", "docker run",
    "docker volumes", "docker volume remove",
    "docker networks", "docker network remove",
    "docker clean", "docker clean all",
    "docker compose up", "docker compose down", "docker compose logs",
    "docker compose build", "docker compose ps", "docker compose restart",
    "docker doctor",

    # Path index
    "/find", "/qcount", "/build",

    # Java
    "java list", "java version", "java change", "java reload",

    # Automation
    "sleep", "sendkeys",

    # Web project tools (new web replaces old webcreate/websetup)

    # Control
    "help", "exit",
    "ai-model list", "ai-model current", "ai-model set", "model list", "model current", "model set",
]

    cmds += list(MACROS.keys())  # include macro names

    if text.startswith(("'", '"')):
        return complete_path(text, state)

    results = [c for c in cmds if c.lower().startswith(text.lower())]
    return results[state] if state < len(results) else None


def setup_autocomplete():
    if readline is None:
        print("(Autocomplete disabled — readline not available)")
        return

    readline.set_completer_delims(' \t\n')
    readline.set_completer(complete_command)
    readline.parse_and_bind("tab: complete")

    # 🪄 Patch TAB key to trigger inline insert behavior
    # This works by overriding readline's key bindings
    try:
        readline.parse_and_bind('"\t": complete')  # standard bind
        # Replace readline's default completer handler
        readline.set_completion_display_matches_hook(
            lambda substitution, matches, longest_match_length:
                complete_and_insert()
        )
    except Exception:
        pass

    
# ---------- Inline completion helper (Windows-friendly) ----------

def complete_and_insert():
    """Force inline completion instead of just listing matches."""
    if readline is None:
        return
    buffer = readline.get_line_buffer()
    cursor = readline.get_endidx()
    matches = []
    state = 0
    while True:
        res = complete_command(buffer, state)
        if res is None:
            break
        matches.append(res)
        state += 1
    if len(matches) == 1:
        # single match → auto-insert remainder
        match = matches[0]
        remainder = match[len(buffer):]
        if remainder:
            sys.stdout.write(remainder)
            sys.stdout.flush()
            readline.insert_text(remainder)
    elif len(matches) > 1:
        # multiple matches → show them like bash
        print()
        print("  ".join(matches))
        readline.redisplay()




# ---------- Advanced input with live autocomplete ----------
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.styles import Style

# ---------- Dynamic Autocomplete Builder ----------
def build_completer():
    """
    Dynamically extract all command names from handle_command()
    regex routes + macros + aliases for live autocomplete.
    """
    import inspect, re

    cmds = []
    try:
        # --- 1. Scan handle_command source for regex routes ---
        src = inspect.getsource(handle_command)
        found = re.findall(r'\^([A-Za-z0-9/_\-]+)', src)
        cmds = sorted(set(found))
    except Exception:
        pass

    # --- 2. Add comprehensive static command list ---
    base_cmds = [
        # Navigation / info
        "pwd", "cd", "back", "home", "list", "info",
        "find", "findext", "recent", "biggest", "search",
        # File operations
        "create file", "create folder", "write", "read",
        "move", "copy", "rename", "delete",
        "zip", "unzip", "open", "explore", "backup", "run",
        # Internet
        "download", "downloadlist", "open url",
        "search web",
        # Modes / safety
        "batch on", "batch off",
        "dry-run on", "dry-run off",
        "ssl on", "ssl off",
        "status", "log", "undo",
        # Macros
        "macro add", "macro run", "macro edit", "macro list", "macro delete", "macro clear",
        # Aliases
        "alias add", "alias delete", "alias list",
        # Ports
        "ports", "kill",
        # Git
        "git upload", "git update", "git download", "git clone",
        "git link", "git status", "git log", "git doctor",
        "git repo list", "git repo delete",
        "git force upload", "git force update",
        "git debug upload", "git debug update",
        "git open",
        "git branch", "git branch list", "git branch create", "git branch switch",
        "git branch delete", "git branch merge",
        # Docker
        "docker ps", "docker ps all", "docker images",
        "docker start", "docker stop", "docker restart", "docker remove",
        "docker shell", "docker logs", "docker logs follow",
        "docker stats", "docker inspect", "docker ip",
        "docker build", "docker pull", "docker push", "docker run",
        "docker volumes", "docker volume remove",
        "docker networks", "docker network remove",
        "docker clean", "docker clean all",
        "docker compose up", "docker compose down", "docker compose logs",
        "docker compose logs follow", "docker compose build",
        "docker compose ps", "docker compose restart",
        "docker doctor",
        # Path index
        "/find", "/qcount", "/build",
        # Java
        "java list", "java version", "java change", "java reload",
        # AI
        "ai", "ai fix", "ai clear",
        "ai-model list", "ai-model current", "ai-model set",
        "model list", "model current", "model set",
        # Config
        "config list", "config get", "config set", "config reset",
        # Scaffolding & dev tools
        "setup",
        "new", "new python", "new node", "new flask", "new fastapi",
        "new react", "new vue", "new svelte", "new next",
        "new electron", "new discord", "new cli", "new web",
        "dev", "dev stop",
        "env list", "env show", "env get", "env set", "env delete", "env template", "env check",
        # Automation
        "sleep", "timer", "sendkeys",
        # System
        "space", "sysinfo", "cmc update", "cmd",
        # Control
        "help", "exit",
    ]
    cmds += base_cmds

    # --- 3. Include all macros and aliases dynamically ---
    try:
        # Always reload latest macros from disk to include old ones
        macro_data = macros_load()
        cmds += list(macro_data.keys())
    except Exception:
        pass

    try:
        cmds += list(ALIASES.keys())
    except Exception:
        pass

    # --- 4. Clean duplicates & sort ---
    cmds = sorted(set(cmds), key=str.lower)

    # --- 5. Return the prompt_toolkit completer ---
    return WordCompleter(cmds, ignore_case=True)



# create a prompt session
session = PromptSession()

# 🎨 CMC cyan theme style
style = Style.from_dict({
        # Prompt label text
    "prompt": "#00ffff bold",

    # Regular suggestions (cyan text, transparent dark background)
    "completion-menu.completion": "bg:#1a1a1a #00ffff",

    # The currently highlighted / selected completion
    "completion-menu.completion.current": "bg:#0033cc #ffffff",

    # Scrollbar (dark blue track + blue handle)
    "scrollbar.background": "bg:#0d0d0d",
    "scrollbar.button": "bg:#0033cc",
})  # ✅ <-- closing both parentheses




def main():
    global CWD

    # Give the background update-check thread a moment to finish before painting
    # the header — it's fast (git fetch locally), so 1.5s is more than enough.
    import time as _time
    _deadline = _time.monotonic() + 1.5
    while STATE.get("cmc_update_status") == "checking" and _time.monotonic() < _deadline:
        _time.sleep(0.05)

    show_header()
    _start_bg_java_detect(5.0)

    # Show update notes once after an update (if UpdateNotes/LATEST.txt exists)
    maybe_show_update_notes()

    # Ensure macros are always loaded fresh from disk
    global MACROS
    MACROS = macros_load()

    completer = build_completer()

    # First-run: show a small tip and pre-fill "help" in the prompt
    first_run = is_first_run()
    if first_run:
        if RICH:
            console.print(
                Panel(
                    "  [bold cyan]Welcome to CMC![/bold cyan]  Type [cyan]help[/cyan] to see all commands.\n"
                    "  [dim]This message only appears once.[/dim]",
                    border_style="cyan",
                    padding=(0, 1),
                )
            )
        else:
            print("Welcome to CMC! Type 'help' to see all commands.")
        mark_first_run_done()

    while True:
        try:
            # On the very first prompt ever, pre-fill "help" so the user just hits Enter
            prompt_default = "help" if first_run else ""
            first_run = False   # only pre-fill once
            _show_path = get_config_value(CONFIG, "prompt.show_path", True)
            _prompt_path = str(CWD) if _show_path else CWD.name
            line = session.prompt(
                f"CMC>{_prompt_path}> ",
                completer=completer,
                complete_while_typing=True,
                style=style,
                default=prompt_default,
            )
        except (EOFError, KeyboardInterrupt):
            print()
            break

        for part in split_commands(line):
            # Prevent timer from splitting its message argument
            if part.lower().startswith("timer "):
                handle_command(line)   # run the whole thing once
                break

            try:
                handle_command(part)
            except SystemExit:
                raise
            except Exception as e:
                global _LAST_CMD, _LAST_ERROR
                _LAST_CMD = part
                _LAST_ERROR = str(e)
                p(f"[red]❌ Error:[/red] {e}" if RICH else f"Error: {e}")
                p("[dim]Tip: type 'ai fix' to diagnose this error.[/dim]" if RICH else "Tip: type 'ai fix' to diagnose.")




if __name__ == "__main__":
    main()



