# CMC_Platform.py — Cross-platform utilities for Computer Main Centre
"""
Centralizes all platform-specific logic so other modules don't need
to scatter sys.platform checks everywhere.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

# ── Platform detection ──────────────────────────────────────────
IS_WINDOWS = sys.platform == "win32"
IS_MACOS = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")


# ── Config directory ────────────────────────────────────────────
def get_config_dir() -> Path:
    """Return ~/.ai_helper (works on all platforms)."""
    d = Path.home() / ".ai_helper"
    d.mkdir(parents=True, exist_ok=True)
    return d


# ── Open file / URL / file-manager ──────────────────────────────
def open_file(path: str) -> None:
    """Open a file with the OS default application."""
    if IS_WINDOWS:
        os.startfile(str(path))
    elif IS_MACOS:
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def open_url(url: str) -> None:
    """Open a URL in the default browser."""
    import webbrowser
    webbrowser.open(url)


def open_file_manager(path: str) -> None:
    """Open a folder in the native file manager."""
    if IS_WINDOWS:
        subprocess.Popen(["explorer", str(path)])
    elif IS_MACOS:
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


# ── Tool discovery ──────────────────────────────────────────────
def find_npm() -> str | None:
    """Find npm executable (handles .cmd on Windows)."""
    if IS_WINDOWS:
        for name in ["npm.cmd", "npm.exe", "npm"]:
            found = shutil.which(name)
            if found:
                return found
    return shutil.which("npm")


def find_claude_cli() -> str | None:
    """Find the Claude CLI executable."""
    for name in ["claude", "claude.cmd", "claude.exe"]:
        found = shutil.which(name)
        if found:
            return found
    return None


def find_git() -> bool:
    """Return True if git is installed."""
    return bool(shutil.which("git"))


def find_ollama() -> str | None:
    """Find the Ollama executable."""
    for name in ["ollama", "ollama.exe"]:
        found = shutil.which(name)
        if found:
            return found
    # Check common install locations on Windows
    if IS_WINDOWS:
        local = os.environ.get("LOCALAPPDATA", "")
        if local:
            candidate = Path(local) / "Programs" / "Ollama" / "ollama.exe"
            if candidate.exists():
                return str(candidate)
    return None


# ── Virtual environment helpers ─────────────────────────────────
def get_venv_activate(venv_path) -> str:
    """Return the venv activation command for the current platform."""
    venv_path = Path(venv_path)
    if IS_WINDOWS:
        return str(venv_path / "Scripts" / "activate.bat")
    return str(venv_path / "bin" / "activate")


def get_venv_activate_instruction(venv_name: str = "venv") -> str:
    """Return human-readable venv activation instruction."""
    if IS_WINDOWS:
        return f"{venv_name}\\Scripts\\activate"
    return f"source {venv_name}/bin/activate"


def get_venv_pip(venv_path) -> str:
    """Return the path to pip inside a venv."""
    venv_path = Path(venv_path)
    if IS_WINDOWS:
        pip = venv_path / "Scripts" / "pip.exe"
        if pip.exists():
            return str(pip)
    else:
        pip = venv_path / "bin" / "pip"
        if pip.exists():
            return str(pip)
    return "pip"


# ── Terminal spawning ───────────────────────────────────────────
def spawn_terminal(cmd: str, cwd=None) -> None:
    """Open a new terminal window running `cmd`."""
    if IS_WINDOWS:
        subprocess.Popen(f'start cmd /k {cmd}', shell=True, cwd=cwd)
    elif IS_MACOS:
        # Use osascript to open Terminal.app
        script = f'tell application "Terminal" to do script "cd {cwd} && {cmd}"'
        subprocess.Popen(["osascript", "-e", script])
    else:
        # Try common Linux terminal emulators
        for term in ["gnome-terminal", "konsole", "xfce4-terminal", "xterm"]:
            if shutil.which(term):
                if term == "gnome-terminal":
                    subprocess.Popen([term, "--", "bash", "-c", f"cd {cwd} && {cmd}; exec bash"])
                elif term == "xterm":
                    subprocess.Popen([term, "-e", f"bash -c 'cd {cwd} && {cmd}; exec bash'"])
                else:
                    subprocess.Popen([term, "-e", f"bash -c 'cd {cwd} && {cmd}; exec bash'"])
                return
        # Fallback: just run in background
        subprocess.Popen(["bash", "-c", cmd], cwd=cwd)


# ── getch (cross-platform single keypress) ──────────────────────
def getch() -> bytes:
    """Read a single keypress without waiting for Enter."""
    if IS_WINDOWS:
        import msvcrt
        return msvcrt.getch()
    else:
        import tty
        import termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.buffer.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch


# ── Claude CLI execution ───────────────────────────────────────
def run_claude_cli(claude_cmd: str, args: list, **kwargs) -> subprocess.CompletedProcess:
    """Run the Claude CLI, handling .cmd/.bat wrapping on Windows."""
    if IS_WINDOWS and claude_cmd.lower().endswith((".cmd", ".bat")):
        run_args = ["cmd.exe", "/c", claude_cmd] + args
    else:
        run_args = [claude_cmd] + args
    return subprocess.run(run_args, **kwargs)


# ── Network command helpers ─────────────────────────────────────
def get_traceroute_cmd() -> list:
    """Return the traceroute command for this platform."""
    if IS_WINDOWS:
        return ["tracert", "-d", "-w", "2000"]
    return ["traceroute", "-n", "-w", "2"]


def get_flush_dns_cmd() -> list:
    """Return the DNS flush command for this platform."""
    if IS_WINDOWS:
        return ["ipconfig", "/flushdns"]
    elif IS_MACOS:
        return ["sudo", "dscacheutil", "-flushcache"]
    return ["systemd-resolve", "--flush-caches"]


def get_ports_cmd() -> list:
    """Return command to list listening ports."""
    if IS_WINDOWS:
        return ["netstat", "-ano"]
    return ["ss", "-tlnp"]


def get_network_info_cmd() -> list:
    """Return command to show network adapter info."""
    if IS_WINDOWS:
        return ["ipconfig", "/all"]
    elif IS_MACOS:
        return ["ifconfig"]
    return ["ip", "addr"]


# ── Script generation ───────────────────────────────────────────
def generate_start_script(content_windows: str, content_unix: str,
                          dest_dir, name: str = "start_server") -> Path:
    """Generate a platform-appropriate start script."""
    dest_dir = Path(dest_dir)
    if IS_WINDOWS:
        script = dest_dir / f"{name}.bat"
        script.write_text(content_windows, encoding="utf-8")
    else:
        script = dest_dir / f"{name}.sh"
        script.write_text(f"#!/bin/sh\n{content_unix}\n", encoding="utf-8")
        script.chmod(0o755)
    return script


# ── OS shell ────────────────────────────────────────────────────
def open_system_shell() -> None:
    """Open the native system shell."""
    if IS_WINDOWS:
        os.system("cmd")
    else:
        shell = os.environ.get("SHELL", "/bin/bash")
        os.system(shell)


# ── Path separator ──────────────────────────────────────────────
PATH_SEP = ";" if IS_WINDOWS else ":"
