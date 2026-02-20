"""
CMC_Scaffold.py  —  Project scaffolding, dev-server launcher, and env manager
===============================================================================

Commands handled here (called from Computer_Main_Centre.py):

  SETUP / NEW PROJECT
  ───────────────────
  setup                   Auto-detect project type in CWD and get it running
  new python              Create a new Python script/CLI project from scratch
  new node                Create a new Node.js project
  new flask               Create a new Flask web-app
  new fastapi             Create a new FastAPI project
  new react               Create a new React (Vite) project
  new vue                 Create a new Vue 3 (Vite) project
  new svelte              Create a new Svelte (Vite) project
  new next                Create a new Next.js project (via npx)
  new electron            Create a new Electron desktop app
  new discord             Create a new Discord.py bot skeleton
  new cli                 Create a new Python CLI tool (argparse skeleton)
  new web                 Full-stack wizard: pick frontend + backend (replaces webcreate)

  DEV SERVER
  ──────────
  dev                     Smart dev-server: reads project, runs dev script + opens browser
  dev <script>            Run a specific package.json script + open browser
  dev stop                Kill the last dev server started by CMC

  ENV FILE MANAGER
  ────────────────
  env list                Show all keys in .env (values hidden by default)
  env show                Show all keys AND values in .env
  env get <KEY>           Show the value of one key
  env set <KEY>=<VALUE>   Add or update a key in .env
  env delete <KEY>        Remove a key from .env
  env template            Create .env.example from .env (values blanked)
  env check               Compare .env vs .env.example, show missing keys
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from typing import Callable, Optional

# Imported lazily inside handle_new to avoid circular imports
_op_web_create = None
def _get_web_create():
    global _op_web_create
    if _op_web_create is None:
        from CMC_Web_Create import op_web_create as _owc
        _op_web_create = _owc
    return _op_web_create

PFunc = Callable[[str], None]

# Tracks the last dev-server PID so "dev stop" can kill it
_DEV_PID: Optional[int] = None


# ===========================================================================
# Tiny helpers
# ===========================================================================

def _yn(prompt: str, default: bool = True) -> bool:
    sfx = "[Y/n]" if default else "[y/N]"
    while True:
        ans = input(f"{prompt} {sfx}: ").strip().lower()
        if not ans:
            return default
        if ans in ("y", "yes"):
            return True
        if ans in ("n", "no"):
            return False
        print("Please answer y or n.")


def _ask(prompt: str, default: str = "") -> str:
    if default:
        ans = input(f"{prompt} [{default}]: ").strip()
        return ans or default
    return input(f"{prompt}: ").strip()


def _run(cmd: list, cwd: Optional[Path] = None, capture: bool = True):
    try:
        r = subprocess.run(
            cmd, cwd=str(cwd) if cwd else None,
            text=True,
            stdout=subprocess.PIPE if capture else None,
            stderr=subprocess.STDOUT if capture else None,
        )
        return r.returncode, (r.stdout or "").strip()
    except FileNotFoundError:
        return 1, f"Command not found: {cmd[0]}"
    except Exception as exc:
        return 1, str(exc)


def _run_live(cmd: list, cwd: Optional[Path] = None) -> None:
    try:
        proc = subprocess.Popen(cmd, cwd=str(cwd) if cwd else None)
        proc.wait()
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        print(str(exc))


def _npm() -> str:
    for c in ["npm.cmd", "npm.exe", "npm"]:
        found = shutil.which(c)
        if found:
            return found
    return "npm"


def _python() -> str:
    return sys.executable or "python"


def _slugify(name: str) -> str:
    clean, last_dash = [], False
    for ch in name.strip():
        if ch.isalnum():
            clean.append(ch.lower())
            last_dash = False
        elif ch in " _-" and not last_dash:
            clean.append("-")
            last_dash = True
    return "".join(clean).strip("-") or "my-project"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _pip_install(reqs_file: Path, venv: Path) -> None:
    pip = venv / "Scripts" / "pip.exe"
    if not pip.exists():
        pip = venv / "bin" / "pip"
    _run_live([str(pip), "install", "-r", str(reqs_file)], cwd=reqs_file.parent)


def _gitignore_python() -> str:
    return "venv/\n__pycache__/\n*.pyc\n*.pyo\n.env\ndist/\nbuild/\n*.egg-info/\n"


def _gitignore_node() -> str:
    return "node_modules/\ndist/\n.env\n.DS_Store\n"


def _readme(name: str, extra: str = "") -> str:
    return f"# {name}\n\n{extra}\n"


# ===========================================================================
# ── SETUP  (auto-detect & get running)
# ===========================================================================

def _detect_project(folder: Path) -> str:
    """Return a short label for the project type, or 'unknown'."""
    files = {f.name.lower() for f in folder.iterdir() if f.is_file()} if folder.exists() else set()
    pkg = folder / "package.json"
    if pkg.exists():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8"))
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            if "next" in deps:              return "next"
            if "nuxt" in deps:              return "nuxt"
            if "@sveltejs/kit" in deps:     return "sveltekit"
            if "svelte" in deps:            return "svelte"
            if "vue" in deps:               return "vue"
            if "react" in deps:             return "react"
            if "electron" in deps:          return "electron"
            if "express" in deps:           return "express"
            return "node"
        except Exception:
            return "node"
    if "requirements.txt" in files or "pyproject.toml" in files:
        if "manage.py" in files:           return "django"
        try:
            reqs = (folder / "requirements.txt").read_text(encoding="utf-8").lower()
            if "fastapi" in reqs:           return "fastapi"
            if "flask" in reqs:             return "flask"
        except Exception:
            pass
        return "python"
    if "cargo.toml" in files:              return "rust"
    if "go.mod" in files:                  return "go"
    if "pom.xml" in files:                 return "java-maven"
    if "build.gradle" in files or "build.gradle.kts" in files: return "java-gradle"
    if "makefile" in files:                return "make"
    if "docker-compose.yml" in files or "docker-compose.yaml" in files: return "compose"
    if "dockerfile" in files:              return "docker"
    return "unknown"


def _get_make_targets(folder: Path) -> list:
    try:
        rc, out = _run(["make", "-qp"], cwd=folder)
        targets = []
        for line in out.splitlines():
            m = re.match(r"^([a-zA-Z0-9_][a-zA-Z0-9_\-\.]*)\s*:", line)
            if m and not m.group(1).startswith("."):
                targets.append(m.group(1))
        return sorted(set(targets))[:15]
    except Exception:
        return []


def handle_setup(cwd: Path, p: PFunc) -> None:
    """Auto-detect current project and get it ready to run."""
    kind = _detect_project(cwd)
    p(f"[cyan]Detected project type:[/cyan] [bold]{kind}[/bold]")

    # ── Node / JS frameworks ──────────────────────────────────────────────
    if kind in ("node", "react", "vue", "svelte", "next", "nuxt", "sveltekit", "electron", "express"):
        nm = cwd / "node_modules"
        if not nm.exists():
            p("[yellow]node_modules not found — running npm install...[/yellow]")
            _run_live([_npm(), "install"], cwd=cwd)
        else:
            p("[green]✓ node_modules already present[/green]")

        if not (cwd / ".env").exists() and (cwd / ".env.example").exists():
            import shutil as _sh
            _sh.copy(cwd / ".env.example", cwd / ".env")
            p("[yellow]Copied .env.example → .env. Edit it before starting.[/yellow]")

        try:
            scripts = json.loads((cwd / "package.json").read_text(encoding="utf-8")).get("scripts", {})
        except Exception:
            scripts = {}

        if "dev" in scripts:
            if _yn("Run 'npm run dev'?"):
                _launch_dev(cwd, "dev", p)
        elif "start" in scripts:
            if _yn("Run 'npm start'?"):
                _launch_dev(cwd, "start", p)
        else:
            p("[yellow]No 'dev' or 'start' script found in package.json.[/yellow]")
        return

    # ── Python ────────────────────────────────────────────────────────────
    if kind in ("python", "flask", "fastapi", "django"):
        venv = cwd / "venv"
        if not venv.exists():
            p("[yellow]No venv found — creating one...[/yellow]")
            _run_live([_python(), "-m", "venv", "venv"], cwd=cwd)

        reqs = cwd / "requirements.txt"
        if reqs.exists():
            p("[yellow]Installing requirements...[/yellow]")
            _pip_install(reqs, venv)
        else:
            p("[dim]No requirements.txt found. Skipping pip install.[/dim]")

        if not (cwd / ".env").exists() and (cwd / ".env.example").exists():
            import shutil as _sh
            _sh.copy(cwd / ".env.example", cwd / ".env")
            p("[yellow]Copied .env.example → .env. Edit it before running.[/yellow]")

        if kind == "django":
            p("[green]✓ Django project ready.[/green]")
            p("[dim]Tip: activate venv then run:  python manage.py runserver[/dim]")
        elif kind in ("flask", "fastapi"):
            entry = next((f for f in ["app.py", "main.py", "run.py"] if (cwd / f).exists()), None)
            if entry and _yn(f"Run 'python {entry}'?"):
                _launch_dev_python(cwd, entry, p)
        else:
            p("[green]✓ Python project ready.[/green]")
            p("[dim]Activate venv:  venv\\Scripts\\activate[/dim]")
        return

    # ── Rust ──────────────────────────────────────────────────────────────
    if kind == "rust":
        p("Running cargo build...")
        _run_live(["cargo", "build"], cwd=cwd)
        return

    # ── Go ────────────────────────────────────────────────────────────────
    if kind == "go":
        p("Running go mod tidy + go build...")
        _run_live(["go", "mod", "tidy"], cwd=cwd)
        _run_live(["go", "build", "./..."], cwd=cwd)
        return

    # ── Docker Compose ────────────────────────────────────────────────────
    if kind == "compose":
        if _yn("Run docker compose up?"):
            _run_live(["docker", "compose", "up", "-d", "--build"], cwd=cwd)
        return

    # ── Makefile ──────────────────────────────────────────────────────────
    if kind == "make":
        targets = _get_make_targets(cwd)
        if targets:
            p(f"[cyan]Make targets found:[/cyan] {', '.join(targets[:10])}")
            choice = _ask("Run which target? (Enter to skip)", "")
            if choice and choice in targets:
                _run_live(["make", choice], cwd=cwd)
        return

    p("[yellow]Could not detect project type. Try 'new <type>' to create one, or 'help 15' for docs.[/yellow]")


# ===========================================================================
# ── DEV SERVER  (smart launcher)
# ===========================================================================

def _open_browser(url: str, delay: float, p: PFunc) -> None:
    """Wait delay seconds then open url in browser."""
    p(f"[dim]Opening browser at {url} in {int(delay)}s...[/dim]")
    time.sleep(delay)
    webbrowser.open_new_tab(url)


def _spawn(cmd: str, cwd: Path, p: PFunc, label: str) -> None:
    """Open a new cmd window running cmd. Stores PID in _DEV_PID."""
    global _DEV_PID
    p(f"[green]Starting:[/green] {label}")
    try:
        proc = subprocess.Popen(
            "start cmd /k " + cmd,
            cwd=str(cwd),
            shell=True,
        )
        _DEV_PID = proc.pid
    except Exception as exc:
        p(f"[red]Failed to launch:[/red] {exc}")


def _npm_port(cwd: Path) -> str:
    """Guess the localhost port for a Node project from its deps."""
    try:
        data = json.loads((cwd / "package.json").read_text(encoding="utf-8"))
        deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
        if "vite" in deps or "@sveltejs/vite-plugin-svelte" in deps: return "5173"
        if "@sveltejs/kit" in deps:  return "5173"
        if "next" in deps:           return "3000"
        if "nuxt" in deps:           return "3000"
        if "angular" in deps or "@angular/core" in deps: return "4200"
    except Exception:
        pass
    return "3000"


def _launch_npm(cwd: Path, script: str, p: PFunc) -> None:
    """npm run <script> in new window + open browser."""
    npm = _npm()
    port = _npm_port(cwd)
    _spawn(f'"{npm}" run {script}', cwd, p, f"npm run {script}")
    _open_browser(f"http://localhost:{port}", 3, p)


def _launch_node(cwd: Path, entry: str, port: str, p: PFunc) -> None:
    """node <entry> in new window + open browser."""
    _spawn(f'"node" {entry}', cwd, p, f"node {entry}")
    _open_browser(f"http://localhost:{port}", 2, p)


def _launch_python_entry(cwd: Path, entry: str, port: str, p: PFunc) -> None:
    """python <entry> in new window (activates venv if present) + open browser."""
    activate = cwd / "venv" / "Scripts" / "activate.bat"
    if activate.exists():
        cmd = f'"cmd" /k "call venv\\Scripts\\activate.bat && python {entry}"'
    else:
        cmd = f'"python" {entry}'
    _spawn(cmd, cwd, p, f"python {entry}")
    _open_browser(f"http://localhost:{port}", 3, p)


def _launch_django(cwd: Path, p: PFunc) -> None:
    activate = cwd / "venv" / "Scripts" / "activate.bat"
    if activate.exists():
        cmd = '"cmd" /k "call venv\\Scripts\\activate.bat && python manage.py runserver"'
    else:
        cmd = '"python" manage.py runserver'
    _spawn(cmd, cwd, p, "python manage.py runserver")
    _open_browser("http://localhost:8000", 3, p)


def _launch_http_server(cwd: Path, p: PFunc) -> None:
    """python -m http.server for plain HTML/static projects."""
    port = "8080"
    py = _python()
    _spawn(f'"{py}" -m http.server {port}', cwd, p, f"python -m http.server {port}")
    _open_browser(f"http://localhost:{port}", 2, p)


def _launch_cargo(cwd: Path, p: PFunc) -> None:
    _spawn('"cargo" run', cwd, p, "cargo run")


def _launch_go(cwd: Path, p: PFunc) -> None:
    _spawn('"go" run ./...', cwd, p, "go run ./...")


def _launch_docker_compose(cwd: Path, p: PFunc) -> None:
    _spawn('"docker" compose up --build', cwd, p, "docker compose up --build")


def _launch_make(cwd: Path, target: str, p: PFunc) -> None:
    _spawn(f'"make" {target}', cwd, p, f"make {target}")


def _is_static_site(cwd: Path) -> bool:
    """True if folder looks like a plain static HTML project."""
    files = {f.name.lower() for f in cwd.iterdir() if f.is_file()}
    return "index.html" in files and "package.json" not in files


def handle_dev(raw: str, cwd: Path, p: PFunc) -> None:
    global _DEV_PID
    parts = raw.strip().split()

    # ── dev stop ──────────────────────────────────────────────────────────
    if len(parts) >= 2 and parts[1].lower() == "stop":
        if _DEV_PID:
            try:
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(_DEV_PID)],
                               capture_output=True)
                p(f"[green]✓ Dev server (PID {_DEV_PID}) stopped.[/green]")
                _DEV_PID = None
            except Exception as exc:
                p(f"[red]Could not stop:[/red] {exc}")
        else:
            p("[yellow]No dev server was started by CMC this session.[/yellow]")
        return

    # ── explicit script name passed: dev <script> ─────────────────────────
    explicit_script = parts[1] if len(parts) >= 2 else None

    # If package.json exists and user named a script, just run it
    pkg = cwd / "package.json"
    if explicit_script and pkg.exists():
        try:
            scripts = json.loads(pkg.read_text(encoding="utf-8")).get("scripts", {})
        except Exception:
            scripts = {}
        if explicit_script in scripts:
            _launch_npm(cwd, explicit_script, p)
            return
        else:
            p(f"[red]Script '{explicit_script}' not found in package.json.[/red]")
            if scripts:
                p(f"[dim]Available: {', '.join(scripts.keys())}[/dim]")
            return

    # ── auto-detect ───────────────────────────────────────────────────────
    kind = _detect_project(cwd)
    p(f"[dim]Project type: {kind}[/dim]")

    # ── Node / JS frameworks ──────────────────────────────────────────────
    if kind in ("node", "react", "vue", "svelte", "next", "nuxt",
                "sveltekit", "electron", "express"):
        # Make sure deps are installed first
        if not (cwd / "node_modules").exists():
            p("[yellow]node_modules missing — running npm install first...[/yellow]")
            _run_live([_npm(), "install"], cwd=cwd)
        try:
            scripts = json.loads(pkg.read_text(encoding="utf-8")).get("scripts", {})
        except Exception:
            scripts = {}
        if "dev" in scripts:
            _launch_npm(cwd, "dev", p)
        elif "start" in scripts:
            _launch_npm(cwd, "start", p)
        elif scripts:
            first = list(scripts.keys())[0]
            p(f"[yellow]No 'dev' script — using '{first}'[/yellow]")
            _launch_npm(cwd, first, p)
        else:
            p("[red]No scripts in package.json.[/red]")
        return

    # ── Flask ─────────────────────────────────────────────────────────────
    if kind == "flask":
        entry = next((f for f in ["app.py", "main.py", "run.py"] if (cwd / f).exists()), None)
        if entry:
            _launch_python_entry(cwd, entry, "5000", p)
        else:
            p("[red]No Flask entry point found (app.py / main.py / run.py).[/red]")
        return

    # ── FastAPI ───────────────────────────────────────────────────────────
    if kind == "fastapi":
        entry = next((f for f in ["main.py", "app.py", "run.py"] if (cwd / f).exists()), None)
        if entry:
            _launch_python_entry(cwd, entry, "8000", p)
            # FastAPI docs are at /docs
            p("[dim]API docs: http://localhost:8000/docs[/dim]")
        else:
            p("[red]No FastAPI entry point found (main.py / app.py).[/red]")
        return

    # ── Django ────────────────────────────────────────────────────────────
    if kind == "django":
        _launch_django(cwd, p)
        return

    # ── Generic Python project ────────────────────────────────────────────
    if kind == "python":
        entry = next((f for f in ["main.py", "app.py", "run.py", "server.py",
                                   "start.py", "cli.py"] if (cwd / f).exists()), None)
        if entry:
            _launch_python_entry(cwd, entry, "5000", p)
        else:
            p("[yellow]No entry point found. Falling back to static file server.[/yellow]")
            _launch_http_server(cwd, p)
        return

    # ── Static HTML site ─────────────────────────────────────────────────
    if _is_static_site(cwd):
        p("[cyan]Static HTML site detected.[/cyan]")
        _launch_http_server(cwd, p)
        return

    # ── Rust ──────────────────────────────────────────────────────────────
    if kind == "rust":
        _launch_cargo(cwd, p)
        return

    # ── Go ────────────────────────────────────────────────────────────────
    if kind == "go":
        _launch_go(cwd, p)
        return

    # ── Docker Compose ────────────────────────────────────────────────────
    if kind == "compose":
        _launch_docker_compose(cwd, p)
        return

    # ── Makefile ──────────────────────────────────────────────────────────
    if kind == "make":
        targets = _get_make_targets(cwd)
        run_target = "run" if "run" in targets else (targets[0] if targets else "")
        if run_target:
            p(f"[cyan]Makefile targets:[/cyan] {', '.join(targets[:8])}")
            chosen = _ask(f"Run which target?", run_target)
            if chosen:
                _launch_make(cwd, chosen, p)
        else:
            p("[yellow]No make targets found.[/yellow]")
        return

    # ── Nothing recognised ────────────────────────────────────────────────
    # Last resort: if there's an index.html, serve it statically
    if (cwd / "index.html").exists():
        p("[yellow]No project type detected — serving index.html as static site.[/yellow]")
        _launch_http_server(cwd, p)
        return

    p("[yellow]Could not detect how to start this project.[/yellow]")
    p("[dim]Tip: 'dev <script>' to run a specific npm script, or 'setup' to configure.[/dim]")


# ===========================================================================
# ── NEW PROJECT  (scaffolding wizard)
# ===========================================================================

def handle_new(raw: str, cwd: Path, p: PFunc) -> None:
    parts = raw.strip().split(None, 1)
    kind = parts[1].lower().strip() if len(parts) >= 2 else ""

    KINDS = {
        "python":   _new_python,
        "node":     _new_node,
        "flask":    _new_flask,
        "fastapi":  _new_fastapi,
        "react":    _new_react,
        "vue":      _new_vue,
        "svelte":   _new_svelte,
        "next":     _new_next,
        "electron": _new_electron,
        "discord":  _new_discord,
        "cli":      _new_cli,
    }

    # ── new web: full-stack wizard (frontend + backend picker) ───────────
    if kind == "web":
        p("[cyan]new web[/cyan] — full-stack web project wizard")
        p("[dim]Pick a frontend (vanilla/react/vue/svelte) and an optional backend (flask/fastapi/express).[/dim]\n")
        try:
            _get_web_create()()
        except Exception as exc:
            p(f"[red]Web project creation failed:[/red] {exc}")
        return

    if not kind or kind not in KINDS:
        p("[cyan]new[/cyan] — create a project from scratch\n")
        p("Available types:")
        p("  new web        Full-stack: frontend (vanilla/react/vue/svelte) + backend (flask/fastapi/express)")
        for k in sorted(KINDS):
            p(f"  new {k}")
        return

    name = _ask("Project name", "my-project")
    slug = _slugify(name)
    folder = cwd / slug
    if folder.exists():
        if not _yn(f"Folder '{slug}' already exists. Continue anyway?", False):
            p("[yellow]Aborted.[/yellow]")
            return
    folder.mkdir(parents=True, exist_ok=True)
    p(f"[green]Creating {kind} project:[/green] {folder}")
    KINDS[kind](name, slug, folder, p)


# ── Individual project generators ──────────────────────────────────────────

def _new_python(name: str, slug: str, folder: Path, p: PFunc) -> None:
    _write(folder / "main.py",
        '"""Entry point."""\n\n\ndef main():\n    print("Hello from ' + name + '")\n\n\n'
        'if __name__ == "__main__":\n    main()\n'
    )
    _write(folder / "requirements.txt", "# Add your dependencies here\n")
    _write(folder / ".gitignore", _gitignore_python())
    _write(folder / "README.md", _readme(name,
        "A Python project.\n\n## Setup\n```\npython -m venv venv\n"
        "venv\\Scripts\\activate\npip install -r requirements.txt\npython main.py\n```"
    ))
    if _yn("Create virtual environment now?"):
        _run_live([_python(), "-m", "venv", "venv"], cwd=folder)
        p("[green]✓ venv created. Activate with: venv\\Scripts\\activate[/green]")
    if _yn("Initialise git repo?", False):
        _run(["git", "init"], cwd=folder)
        p("[green]✓ git init done.[/green]")
    p(f"\n[bold green]✓ Python project ready![/bold green]  {folder}")


def _new_node(name: str, slug: str, folder: Path, p: PFunc) -> None:
    pkg = {
        "name": slug, "version": "1.0.0", "private": True,
        "scripts": {"start": "node index.js"},
        "dependencies": {},
    }
    _write(folder / "package.json", json.dumps(pkg, indent=2))
    _write(folder / "index.js", f'console.log("Hello from {name}");\n')
    _write(folder / ".gitignore", _gitignore_node())
    _write(folder / "README.md", _readme(name,
        "A Node.js project.\n\n## Run\n```\nnpm install\nnpm start\n```"
    ))
    p("[yellow]Running npm install...[/yellow]")
    _run_live([_npm(), "install"], cwd=folder)
    if _yn("Initialise git repo?", False):
        _run(["git", "init"], cwd=folder)
    p(f"\n[bold green]✓ Node project ready![/bold green]  {folder}")


def _new_flask(name: str, slug: str, folder: Path, p: PFunc) -> None:
    _write(folder / "app.py",
        "from flask import Flask, jsonify\n"
        "from flask_cors import CORS\n\n"
        "app = Flask(__name__)\n"
        "CORS(app)\n\n"
        "@app.get('/')\n"
        "def index():\n"
        "    return jsonify({'message': 'Hello from " + name + "'})\n\n"
        "if __name__ == '__main__':\n"
        "    app.run(debug=True)\n"
    )
    _write(folder / "requirements.txt", "flask\nflask-cors\npython-dotenv\n")
    _write(folder / ".env", "FLASK_ENV=development\nFLASK_DEBUG=1\n")
    _write(folder / ".env.example", "FLASK_ENV=development\nFLASK_DEBUG=1\n")
    _write(folder / ".gitignore", _gitignore_python())
    _write(folder / "README.md", _readme(name,
        "A Flask API.\n\n## Run\n```\npython -m venv venv\nvenv\\Scripts\\activate\n"
        "pip install -r requirements.txt\npython app.py\n```"
    ))
    if _yn("Create venv and install dependencies?"):
        _run_live([_python(), "-m", "venv", "venv"], cwd=folder)
        _pip_install(folder / "requirements.txt", folder / "venv")
    if _yn("Initialise git repo?", False):
        _run(["git", "init"], cwd=folder)
    p(f"\n[bold green]✓ Flask project ready![/bold green]  {folder}")
    p("[dim]Start: python app.py  →  http://localhost:5000[/dim]")


def _new_fastapi(name: str, slug: str, folder: Path, p: PFunc) -> None:
    _write(folder / "main.py",
        "from fastapi import FastAPI\n"
        "from fastapi.middleware.cors import CORSMiddleware\n\n"
        "app = FastAPI(title='" + name + "')\n"
        "app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])\n\n"
        "@app.get('/api/hello')\n"
        "async def hello():\n"
        "    return {'message': 'Hello from " + name + "'}\n\n"
        "if __name__ == '__main__':\n"
        "    import uvicorn\n"
        "    uvicorn.run('main:app', reload=True, host='0.0.0.0', port=8000)\n"
    )
    _write(folder / "requirements.txt", "fastapi\nuvicorn[standard]\npython-dotenv\n")
    _write(folder / ".env", "PORT=8000\n")
    _write(folder / ".env.example", "PORT=8000\n")
    _write(folder / ".gitignore", _gitignore_python())
    _write(folder / "README.md", _readme(name,
        "A FastAPI project.\n\n## Run\n```\npython -m venv venv\nvenv\\Scripts\\activate\n"
        "pip install -r requirements.txt\npython main.py\n```\n"
        "Docs: http://localhost:8000/docs"
    ))
    if _yn("Create venv and install dependencies?"):
        _run_live([_python(), "-m", "venv", "venv"], cwd=folder)
        _pip_install(folder / "requirements.txt", folder / "venv")
    if _yn("Initialise git repo?", False):
        _run(["git", "init"], cwd=folder)
    p(f"\n[bold green]✓ FastAPI project ready![/bold green]  {folder}")
    p("[dim]Start: python main.py  →  http://localhost:8000/docs[/dim]")


def _new_vite_frontend(name: str, slug: str, folder: Path, p: PFunc, framework: str) -> None:
    """Shared scaffolder for React, Vue, Svelte (all use Vite)."""
    CONFIGS = {
        "react": {
            "deps":     {"react": "^18.0.0", "react-dom": "^18.0.0"},
            "devDeps":  {"vite": "^5.4.0", "@vitejs/plugin-react-swc": "^3.5.0"},
            "vite_cfg": (
                "import { defineConfig } from 'vite'\n"
                "import react from '@vitejs/plugin-react-swc'\n"
                "export default defineConfig({ plugins: [react()] })\n"
            ),
            "root_id": "root",
            "entry":   "main.jsx",
            "entry_content": (
                "import React from 'react'\n"
                "import ReactDOM from 'react-dom/client'\n\n"
                "function App() {\n"
                "  return <h1>" + name + "</h1>\n"
                "}\n\n"
                "ReactDOM.createRoot(document.getElementById('root'))"
                ".render(<React.StrictMode><App /></React.StrictMode>)\n"
            ),
        },
        "vue": {
            "deps":     {"vue": "^3.5.0"},
            "devDeps":  {"vite": "^5.4.0", "@vitejs/plugin-vue": "^5.0.0"},
            "vite_cfg": (
                "import { defineConfig } from 'vite'\n"
                "import vue from '@vitejs/plugin-vue'\n"
                "export default defineConfig({ plugins: [vue()] })\n"
            ),
            "root_id": "app",
            "entry":   "main.js",
            "entry_content": (
                "import { createApp } from 'vue'\n"
                "import App from './App.vue'\n"
                "createApp(App).mount('#app')\n"
            ),
        },
        "svelte": {
            "deps":     {},
            "devDeps":  {"svelte": "^5.0.0", "@sveltejs/vite-plugin-svelte": "^5.1.1", "vite": "^6.0.0"},
            "vite_cfg": (
                "import { defineConfig } from 'vite'\n"
                "import { svelte } from '@sveltejs/vite-plugin-svelte'\n"
                "export default defineConfig({ plugins: [svelte()] })\n"
            ),
            "root_id": "app",
            "entry":   "main.js",
            "entry_content": (
                "import App from './App.svelte'\n"
                "new App({ target: document.getElementById('app') })\n"
            ),
        },
    }
    cfg = CONFIGS[framework]
    root_id = cfg["root_id"]
    entry   = cfg["entry"]

    pkg = {
        "name": slug, "version": "0.0.0", "private": True,
        "scripts": {"dev": "vite", "build": "vite build", "preview": "vite preview"},
        "dependencies":    cfg["deps"],
        "devDependencies": cfg["devDeps"],
    }
    src = folder / "src"
    src.mkdir(parents=True, exist_ok=True)

    _write(folder / "package.json", json.dumps(pkg, indent=2))

    # Build index.html without mixing f-string quote styles
    index_html = (
        "<!doctype html>\n"
        "<html>\n"
        "  <head>\n"
        "    <meta charset='utf-8' />\n"
        "    <title>" + name + "</title>\n"
        "  </head>\n"
        "  <body>\n"
        "    <div id='" + root_id + "'></div>\n"
        "    <script type='module' src='/src/" + entry + "'></script>\n"
        "  </body>\n"
        "</html>\n"
    )
    _write(folder / "index.html", index_html)
    _write(folder / "vite.config.mjs", cfg["vite_cfg"])
    _write(src / entry, cfg["entry_content"])

    if framework == "vue":
        _write(src / "App.vue",
            "<template>\n  <main><h1>" + name + "</h1></main>\n</template>\n<script setup></script>\n"
        )
    elif framework == "svelte":
        _write(src / "App.svelte", "<main><h1>" + name + "</h1></main>\n")

    _write(folder / ".gitignore", _gitignore_node())
    _write(folder / "README.md", _readme(name,
        framework.capitalize() + " + Vite project.\n\n## Run\n```\nnpm install\nnpm run dev\n```"
    ))

    p(f"[yellow]Running npm install for {framework}...[/yellow]")
    extra = ["--legacy-peer-deps"] if framework == "svelte" else []
    _run_live([_npm(), "install"] + extra, cwd=folder)

    if _yn("Initialise git repo?", False):
        _run(["git", "init"], cwd=folder)
    if _yn("Start dev server now?"):
        _launch_dev(folder, "dev", p)
    else:
        p(f"\n[bold green]✓ {framework.capitalize()} project ready![/bold green]  {folder}")
        p("[dim]Start with: dev  (cd into the folder first)[/dim]")


def _new_react(name: str, slug: str, folder: Path, p: PFunc) -> None:
    _new_vite_frontend(name, slug, folder, p, "react")

def _new_vue(name: str, slug: str, folder: Path, p: PFunc) -> None:
    _new_vite_frontend(name, slug, folder, p, "vue")

def _new_svelte(name: str, slug: str, folder: Path, p: PFunc) -> None:
    _new_vite_frontend(name, slug, folder, p, "svelte")


def _new_next(name: str, slug: str, folder: Path, p: PFunc) -> None:
    p("[yellow]Creating Next.js project via create-next-app (needs Node + npx)...[/yellow]")
    parent = folder.parent
    _run_live([_npm(), "exec", "--yes", "create-next-app@latest", slug,
               "--ts", "--eslint", "--tailwind", "--no-app", "--src-dir",
               "--import-alias", "@/*"],
              cwd=parent)
    p(f"\n[bold green]✓ Next.js project ready![/bold green]  {folder}")
    if _yn("Start dev server now?") and folder.exists():
        _launch_dev(folder, "dev", p)


def _new_electron(name: str, slug: str, folder: Path, p: PFunc) -> None:
    pkg = {
        "name": slug, "version": "1.0.0", "private": True,
        "main": "main.js",
        "scripts": {"start": "electron ."},
        "devDependencies": {"electron": "^31.0.0"},
    }
    _write(folder / "package.json", json.dumps(pkg, indent=2))
    _write(folder / "main.js",
        "const { app, BrowserWindow } = require('electron')\n\n"
        "function createWindow() {\n"
        "  const win = new BrowserWindow({\n"
        "    width: 1024, height: 768,\n"
        "    webPreferences: { nodeIntegration: true, contextIsolation: false }\n"
        "  })\n"
        "  win.loadFile('index.html')\n"
        "}\n\n"
        "app.whenReady().then(createWindow)\n"
        "app.on('window-all-closed', () => {\n"
        "  if (process.platform !== 'darwin') app.quit()\n"
        "})\n"
    )
    _write(folder / "index.html",
        "<!DOCTYPE html>\n"
        "<html>\n"
        "  <head><meta charset='UTF-8'><title>" + name + "</title></head>\n"
        "  <body>\n"
        "    <h1>" + name + "</h1>\n"
        "    <p>Edit index.html and main.js to get started.</p>\n"
        "  </body>\n"
        "</html>\n"
    )
    _write(folder / ".gitignore", _gitignore_node())
    _write(folder / "README.md", _readme(name,
        "An Electron desktop app.\n\n## Run\n```\nnpm install\nnpm start\n```"
    ))
    p("[yellow]Running npm install (installs Electron — may take a minute)...[/yellow]")
    _run_live([_npm(), "install"], cwd=folder)
    if _yn("Initialise git repo?", False):
        _run(["git", "init"], cwd=folder)
    p(f"\n[bold green]✓ Electron project ready![/bold green]  {folder}")
    p("[dim]Start: npm start[/dim]")


def _new_discord(name: str, slug: str, folder: Path, p: PFunc) -> None:
    _write(folder / "bot.py",
        "import discord\n"
        "from discord.ext import commands\n"
        "from dotenv import load_dotenv\n"
        "import os\n\n"
        "load_dotenv()\n"
        "TOKEN = os.getenv('DISCORD_TOKEN')\n\n"
        "intents = discord.Intents.default()\n"
        "intents.message_content = True\n"
        "bot = commands.Bot(command_prefix='!', intents=intents)\n\n"
        "@bot.event\n"
        "async def on_ready():\n"
        "    print(f'Logged in as {bot.user}')\n\n"
        "@bot.command()\n"
        "async def hello(ctx):\n"
        "    await ctx.send('Hello from " + name + "!')\n\n"
        "bot.run(TOKEN)\n"
    )
    _write(folder / "requirements.txt", "discord.py\npython-dotenv\n")
    _write(folder / ".env", "DISCORD_TOKEN=your_bot_token_here\n")
    _write(folder / ".env.example", "DISCORD_TOKEN=your_bot_token_here\n")
    _write(folder / ".gitignore", _gitignore_python() + ".env\n")
    _write(folder / "README.md", _readme(name,
        "A Discord.py bot.\n\n## Setup\n"
        "1. Create a bot at https://discord.com/developers/applications\n"
        "2. Copy your token into `.env`\n"
        "3. Run:\n```\npython -m venv venv\nvenv\\Scripts\\activate\n"
        "pip install -r requirements.txt\npython bot.py\n```"
    ))
    if _yn("Create venv and install discord.py?"):
        _run_live([_python(), "-m", "venv", "venv"], cwd=folder)
        _pip_install(folder / "requirements.txt", folder / "venv")
    if _yn("Initialise git repo?", False):
        _run(["git", "init"], cwd=folder)
    p(f"\n[bold green]✓ Discord bot ready![/bold green]  {folder}")
    p("[dim]Add your bot token to .env before running![/dim]")


def _new_cli(name: str, slug: str, folder: Path, p: PFunc) -> None:
    _write(folder / "cli.py",
        "#!/usr/bin/env python3\n"
        '"""' + name + " — command-line tool.\"\"\"\n"
        "import argparse\n\n\n"
        "def main():\n"
        "    parser = argparse.ArgumentParser(description='" + name + "')\n"
        "    parser.add_argument('--version', action='version', version='1.0.0')\n"
        "    parser.add_argument('name', nargs='?', default='World', help='Who to greet')\n"
        "    args = parser.parse_args()\n"
        "    print(f'Hello, {args.name}!')\n\n\n"
        "if __name__ == '__main__':\n"
        "    main()\n"
    )
    _write(folder / "requirements.txt", "# Add your dependencies here\n")
    _write(folder / ".gitignore", _gitignore_python())
    _write(folder / "README.md", _readme(name,
        "A Python CLI tool.\n\n## Usage\n```\npython cli.py --help\npython cli.py Alice\n```"
    ))
    if _yn("Create virtual environment now?"):
        _run_live([_python(), "-m", "venv", "venv"], cwd=folder)
    if _yn("Initialise git repo?", False):
        _run(["git", "init"], cwd=folder)
    p(f"\n[bold green]✓ CLI project ready![/bold green]  {folder}")
    p("[dim]Run: python cli.py --help[/dim]")


# ===========================================================================
# ── ENV FILE MANAGER
# ===========================================================================

def _load_env(folder: Path) -> list:
    """Parse .env → list of (key, value) tuples, preserving order."""
    env_file = folder / ".env"
    if not env_file.exists():
        return []
    pairs = []
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, _, v = line.partition("=")
            pairs.append((k.strip(), v.strip()))
    return pairs


def _load_env_file(path: Path) -> list:
    pairs = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, _, v = line.partition("=")
            pairs.append((k.strip(), v.strip()))
    return pairs


def _save_env(folder: Path, pairs: list) -> None:
    lines = [k + "=" + v for k, v in pairs]
    (folder / ".env").write_text("\n".join(lines) + "\n", encoding="utf-8")


def handle_env(raw: str, cwd: Path, p: PFunc) -> None:
    parts = raw.strip().split(None, 2)
    sub = parts[1].lower() if len(parts) >= 2 else "list"

    if sub == "list":
        pairs = _load_env(cwd)
        if not pairs:
            p("[yellow]No .env file found (or empty). Use 'env set KEY=value' to add entries.[/yellow]")
            return
        p(f"[cyan].env[/cyan] — {len(pairs)} keys  [dim](values hidden — use 'env show' to reveal)[/dim]")
        for k, _ in pairs:
            p(f"  [bold]{k}[/bold]")
        return

    if sub == "show":
        pairs = _load_env(cwd)
        if not pairs:
            p("[yellow]No .env file found.[/yellow]")
            return
        p(f"[cyan].env[/cyan] — {len(pairs)} entries:")
        for k, v in pairs:
            p(f"  [bold]{k}[/bold] = [green]{v}[/green]")
        return

    if sub == "get" and len(parts) >= 3:
        key = parts[2].strip()
        for k, v in _load_env(cwd):
            if k == key:
                p(f"{key} = [green]{v}[/green]")
                return
        p(f"[yellow]Key '{key}' not found in .env[/yellow]")
        return

    if sub == "set" and len(parts) >= 3:
        assignment = parts[2].strip()
        if "=" not in assignment:
            p("[red]Usage:[/red] env set KEY=value")
            return
        new_key, _, new_val = assignment.partition("=")
        new_key = new_key.strip()
        pairs = _load_env(cwd)
        found = False
        for i, (k, v) in enumerate(pairs):
            if k == new_key:
                pairs[i] = (new_key, new_val)
                found = True
                break
        if not found:
            pairs.append((new_key, new_val))
        _save_env(cwd, pairs)
        action = "Updated" if found else "Added"
        p(f"[green]✓ {action}:[/green] {new_key}={new_val}")
        return

    if sub == "delete" and len(parts) >= 3:
        key = parts[2].strip()
        pairs = _load_env(cwd)
        before = len(pairs)
        pairs = [(k, v) for k, v in pairs if k != key]
        if len(pairs) == before:
            p(f"[yellow]Key '{key}' not found in .env[/yellow]")
        else:
            _save_env(cwd, pairs)
            p(f"[green]✓ Removed:[/green] {key}")
        return

    if sub == "template":
        pairs = _load_env(cwd)
        if not pairs:
            p("[yellow]No .env file to create a template from.[/yellow]")
            return
        lines = [k + "=" for k, _ in pairs]
        (cwd / ".env.example").write_text("\n".join(lines) + "\n", encoding="utf-8")
        p(f"[green]✓ Created .env.example[/green] with {len(pairs)} keys (values blanked)")
        return

    if sub == "check":
        example = cwd / ".env.example"
        if not example.exists():
            p("[yellow]No .env.example found. Run 'env template' to create one.[/yellow]")
            return
        example_keys = {k for k, v in _load_env_file(example)}
        env_keys     = {k for k, v in _load_env(cwd)}
        missing = example_keys - env_keys
        extra   = env_keys - example_keys
        if not missing and not extra:
            p("[green]✓ .env matches .env.example perfectly.[/green]")
        else:
            if missing:
                p(f"[red]Missing keys in .env:[/red] {', '.join(sorted(missing))}")
            if extra:
                p(f"[yellow]Extra keys (not in .env.example):[/yellow] {', '.join(sorted(extra))}")
        return

    # fallback help
    p("[cyan]env[/cyan] — .env file manager\n")
    p("  env list             List all keys (values hidden)")
    p("  env show             List all keys and values")
    p("  env get <KEY>        Show one value")
    p("  env set KEY=value    Add or update a key")
    p("  env delete <KEY>     Remove a key")
    p("  env template         Create .env.example (values blanked)")
    p("  env check            Compare .env vs .env.example")
