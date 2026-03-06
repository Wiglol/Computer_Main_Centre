<div align="center">

<img src="docs/terminal.svg" alt="CMC terminal demo" width="100%"/>

# Computer Main Centre

**A local command console for Windows, Linux and macOS** — file management, Git, Docker, AI assistant, network tools, media conversion, macros, and more in one place.

[![Python](https://img.shields.io/badge/Python-3.10+-3776ab?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-0078d4?style=flat-square)](https://github.com/Wiglol/Computer_Main_Centre)
[![AI](https://img.shields.io/badge/AI-Multi%20backend-7c3aed?style=flat-square)](https://github.com/Wiglol/Computer_Main_Centre)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=flat-square)](LICENSE.txt)

</div>

---

## What is CMC?

CMC is a Python-powered console that brings together file operations, GitHub publishing, Docker control, network diagnostics, media/FFmpeg tools, a multi-backend AI assistant, automation macros, and more — all with one consistent, easy-to-remember command syntax.

No need to remember different CLI tools. One console, one language.

---

## Features

|   | Feature | Example |
|:--:|---|---|
| 🚀 | **Git publishing** — create repos, commit, push in one step | `git upload`, `git update "my message"` |
| 🔄 | **Macros & chains** — save and run multi-step automation | `macro add deploy = backup ..., git update` |
| 🤖 | **AI assistant** — Ollama, Claude Code, OpenAI, Anthropic, OpenRouter | `ai how do I zip a folder and push it?` |
| 📁 | **File operations** — copy, move, zip, backup, search | `backup 'C:/Project' 'C:/Backups'` |
| 🌐 | **Network toolkit** — ping, DNS, traceroute, WiFi, speed test | `ping google.com`, `speedtest` |
| 🎬 | **Media tools** — convert, trim, compress, resize (FFmpeg) | `convert 'video.mp4' to gif` |
| 🛡️ | **Dry-run + Undo** — preview or reverse almost any action | `dry-run on`, `undo` |
| 🔍 | **Fast global search** — index drives, search instantly | `/build C D`, `/find ProjectName` |
| ☕ | **Java version switcher** — switch versions, handles registry/PATH | `java change 17` |
| 🏗️ | **Project scaffolding** — spin up Flask, React, Node, and more | `new flask`, `setup`, `dev` |
| 🐳 | **Docker** — container control + power commands | `docker ps`, `docker watch myapp` |

---

## Quick Start

**1. Install Python 3.10+**
> [python.org/downloads](https://python.org/downloads) — check **"Add Python to PATH"** during install.

**2. Get CMC**
```
git clone https://github.com/Wiglol/Computer_Main_Centre
```
Or download the ZIP from the GitHub page and extract anywhere.

**3. (Optional) Set up the AI assistant**
Run `CMC_AI_Setup.cmd` from the CMC folder.
If you want local/offline AI, install [Ollama](https://ollama.com/download) first.

**4. Launch CMC**

| Platform | Method |
|---|---|
| Windows | Double-click `Start_CMC.vbs` |
| Linux / macOS | `python3 src/Computer_Main_Centre.py` |

---

## Git — publish anything in seconds

CMC wraps Git into a handful of commands that handle the things you actually do 90% of the time. No init, no remote add, no branch juggling unless you need it.

```
git upload                                          Create a new GitHub repo from the current folder.
                                                    Handles init, first commit, push — all in one.

git update "message"                                Commit + push to the linked repo.

git update Owner/Repo "message" --add src/app.py   Partial commit — only stages one file or folder.

git download Owner/Repo                             Clone any repo into the current folder.

git link Owner/Repo                                 Link current folder to an existing repo.

git force update                                    When git is broken — auto-repairs and retries.

git branch create my-feature                        New branch, switches to it immediately.
git branch merge my-feature                         Merges into current branch.

git repo delete Owner/OldRepo                       Deletes remote repo. Requires typing DELETE.

git doctor                                          Diagnoses token, remote, and branch issues.
```

---

## Macros — automate anything

Macros are the most powerful part of CMC. They chain any commands together with commas, support variables, and run the entire chain in one word. Build them once, run them forever.

```
macro add <name> = <cmd1>, <cmd2>, <cmd3>
macro run <name>
macro edit <name>      Re-opens the command pre-filled for editing
macro list
```

**Variables:** `%HOME%`  `%DATE%`  `%NOW%`

**Examples:**

```
macro add backup = backup 'C:/MyProject' '%HOME%/Backups'

macro add deploy = batch on, backup 'C:/MyProject' '%HOME%/Backups', git update "deploy %NOW%", batch off

macro add clean = dry-run on, space '%HOME%/Downloads' depth 3 report
```

Running `deploy` does a timestamped backup and a git push — all in one word, no confirmations.

---

## Aliases

For single-command shortcuts:

```
alias add dl = explore '%HOME%/Downloads'
alias add proj = cd 'C:/MyProject'
```

---

## AI Assistant

Supports local and cloud backends:
- Ollama (local/offline after model download)
- Claude Code CLI
- OpenAI API
- Anthropic API
- OpenRouter API

The AI sees your current folder listing, recent command log, active macros, and aliases, so answers are specific to your session.

```
ai <question>                 Ask anything — context-aware
ai fix                        Auto-explain the last failed command
ai clear                      Reset conversation history

ai-model pick                 Interactive model/backend picker (arrow keys)
ai-model list                 Show available backends/models + status
ai-model current              Show active model (and effort when applicable)

ai key set <backend> <key>    Save API key (openai/anthropic/openrouter)
ai key clear <backend>        Remove saved API key
ai key detect                 Show which keys are currently set
```

Claude Code and OpenAI support effort selection (`default`, `low`, `medium`, `high`) from `ai-model pick`.

---

## Network Toolkit

A full set of network diagnostics built in — no need to remember `ipconfig` vs `ip addr` vs `ifconfig`. CMC picks the right command for your OS.

```
ping <host>                   Ping a host
ip                            Show your local + public IP
dns <domain>                  DNS lookup (A, AAAA, MX, NS, TXT)
traceroute <host>             Trace network route
wifi                          Show WiFi SSID, signal, speed, channel
mobile                        Show cellular/mobile broadband info
speedtest                     Download speed test (Mbps)
net status                    Network adapter details
flush dns                     Flush DNS resolver cache
ports                         List listening ports
headers <url>                 Show HTTP response headers
```

---

## Media Tools (FFmpeg)

Simplified media conversion and editing. CMC auto-detects FFmpeg even if it's not in your PATH.

```
convert 'video.mp4' to gif                Convert between any format
extract audio 'video.mp4'                 Pull audio track from video
trim 'video.mp4' 00:01:00 00:02:30        Cut a clip
resize 'image.png' 800x600                Resize video or image
rotate 'video.mp4' 90                     Rotate 90/180/270 degrees
volume 'audio.mp3' 200%                   Adjust audio volume
compress 'video.mp4'                      Reduce file size (shows % saved)
merge 'part1.mp4' 'part2.mp4'             Concatenate media files
media info 'file.mp4'                     Show duration, codec, bitrate, resolution
thumbnail 'video.mp4' 00:00:30            Extract a single frame as image
```

---

## Other Commands

<details>
<summary>📁 Files, zip, backup</summary>

```
copy 'C:/A/file.txt' to 'C:/B/file.txt'
move 'notes.txt' to 'archive/notes.txt'
zip 'C:/Project' to 'C:/Backups'
unzip 'C:/archive.zip' to 'C:/Unpacked'
backup 'C:/Project' 'C:/Backups'         Timestamped zip (name_YYYY-MM-DD_HH-MM-SS.zip)
read 'config.json'
delete 'C:/Temp/old_logs'                Confirms unless batch ON; respects dry-run
undo                                     Up to 30 steps
```

</details>

<details>
<summary>🔍 Search & disk</summary>

```
find 'log'                       Filename search, recursive from current folder
search 'java.io.IOException'     Search text inside files
/build C D                       Build path index for drives C and D
/find NBTExplorer 2.8            Global fuzzy search using the index
space 'C:/Downloads' depth 4 report   Disk usage with AI cleanup suggestions
```

</details>

<details>
<summary>🏗️ Project tools</summary>

```
new flask / react / node / vue / fastapi / electron / discord   Create project from scratch
setup                                                           Auto-install deps for existing project
dev                                                             Start dev server + open browser
dev build                                                       Run specific package.json script
env set DATABASE_URL=postgres://localhost/mydb
env list / env check
```

</details>

<details>
<summary>☕ Java</summary>

```
java list                        Show all detected Java installations
java change 17                   Switch to Java 17 (updates PATH + JAVA_HOME)
java set 'C:/path/to/jdk'       Set a specific Java path
```

On Windows, CMC updates the registry and requests UAC elevation for system-wide changes.
On Linux/Mac, it updates `~/.bashrc` or `~/.zshrc`.

</details>

<details>
<summary>🐳 Docker</summary>

Standard Docker commands simplified (`ps`, `start`, `stop`, `shell`, `logs`, `build`, `compose`, etc.) plus some power commands not in the standard CLI:

```
docker wait <name>          Poll until healthy
docker errors <name>        Filter logs to errors only
docker env run <image>      Inject .env vars and run
docker backup <name>        Save config to timestamped zip
docker clone <name> <new>   Duplicate a container
docker watch <name>         Live logs + stats overlay
docker size <image>         Layer-by-layer size breakdown
docker port-check           Check compose ports vs system
```

Type `help 15` inside CMC for the full Docker reference.

</details>

---

## Safety

- **`dry-run on`** — preview what any command would do; nothing actually runs
- **`batch on`** — skip all confirmation prompts (useful inside macros)
- **`undo`** — reverse the last action up to 30 steps
- **`status`** — see current modes, AI model, Java version, macro count, undo depth
- **`log`** — view command history with timestamps

---

## Requirements

- Python 3.10+
- **Windows 10/11**, **Linux**, or **macOS**
- [Git](https://git-scm.com/) — for Git features
- [Ollama](https://ollama.com/download) — optional local/offline AI backend
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) — optional backend (no API key required)
- [FFmpeg](https://ffmpeg.org/) — optional, for media commands
- Optional API keys for OpenAI / Anthropic / OpenRouter if using those backends

---

## Help System

CMC has a built-in categorized help system. Type `help` for the overview or `help <number>` for a specific section:

| # | Section |
|---|---|
| 1 | Navigation |
| 2 | File Operations |
| 3 | Search |
| 4 | Zip & Backup |
| 5 | Git |
| 6 | Macros & Aliases |
| 7 | AI Assistant |
| 8 | Java |
| 9 | Project Tools |
| 10 | System & Info |
| 11 | Automation |
| 12 | Appearance |
| 13 | Network & Connectivity |
| 14 | Media Tools (FFmpeg) |
| 15 | Docker |
| 16 | Flags & Modes |

---

## Manuals

Full command references are in the `manuals/` folder:

- `CMC_AI_Manual_MINI.md` — compact reference for the light AI model (8b)
- `CMC_AI_Manual_MEDIUM.md` — full reference for the heavy AI model (14b)
- `AI_Manual.md` — comprehensive technical reference for external AI use

---

*CMC is for local use only. Git operations respect `.gitignore` rules. Update with `cmc update check` / `cmc update`.*
