<div align="center">

<img src="docs/terminal.svg" alt="CMC terminal demo" width="100%"/>

# Computer Main Centre

**A local command console for Windows** — file management, Git, Docker, AI assistant, macros, and more in one place.

[![Python](https://img.shields.io/badge/Python-3.10+-3776ab?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Windows](https://img.shields.io/badge/Windows-10%20%7C%2011-0078d4?style=flat-square&logo=windows)](https://microsoft.com/windows)
[![AI](https://img.shields.io/badge/AI-Ollama%20powered-7c3aed?style=flat-square)](https://ollama.com)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=flat-square)](LICENSE.txt)

</div>

---

## What is CMC?

CMC is a Python-powered console that brings together file operations, GitHub publishing, Docker control, a fully local AI assistant, automation macros, and more — all with one consistent, easy-to-remember command syntax.

No need to remember different CLI tools. One console, one language.

---

## Features

|   | Feature | Example |
|:--:|---|---|
| 🤖 | **Local AI assistant** — runs fully offline via Ollama | `ai how do I zip a folder and push it?` |
| 🚀 | **Git publishing** — create repos, commit, push in one step | `git upload`, `git update "my message"` |
| 🐳 | **Docker control** — simplified + power commands | `docker watch myapp`, `docker port-check` |
| 📁 | **File operations** — copy, move, zip, backup, search | `backup 'C:/Project' 'C:/Backups'` |
| 🔄 | **Macros & chains** — save and run multi-step automation | `macro add deploy = backup ..., git update` |
| 🔍 | **Fast global search** — index drives, search instantly | `/build C D`, `/find ProjectName` |
| ☕ | **Java version switcher** — switch versions, CMC handles UAC | `java change 17` |
| 🛡️ | **Dry-run + Undo** — preview or reverse almost any action | `dry-run on`, `undo` |
| 🏗️ | **Project scaffolding** — spin up Flask, React, Node, and more | `new flask`, `setup`, `dev` |
| 🐚 | **Dev server launcher** — auto-detect project, run, open browser | `dev`, `dev build`, `dev stop` |

---

## Quick Start

**1. Install Python 3.10+**
> [python.org/downloads](https://python.org/downloads) — check **"Add Python to PATH"** during install.

**2. Get CMC**
```
git clone https://github.com/Wiggo/CMC
```
Or download the ZIP from the GitHub page and extract anywhere.

**3. (Optional) Set up the AI assistant**
Install [Ollama](https://ollama.com/download), then run `CMC_AI_Ollama_Setup.cmd` from the CMC folder.

**4. Launch CMC**
Double-click `Start_CMC.vbs`

---

## Commands

<details>
<summary><b>🚀 Git — publish, update, branch</b></summary>

```
git upload                                          Create a new GitHub repo from the current folder
git update "message"                               Commit + push to the linked repo
git update Owner/Repo "message" --add src/app.py  Partial commit (one file or folder only)
git download Owner/Repo                            Clone a repo into the current folder
git link Owner/Repo                                Link current folder to an existing repo
git force update                                   Auto-fix common git problems and retry push
git branch create my-feature                       Create and switch to a new branch
git branch merge my-feature                        Merge a branch into current
git repo delete Owner/OldRepo                      Delete a remote repo (requires typing DELETE)
git doctor                                         Diagnose token, remote, branch issues
```

</details>

<details>
<summary><b>🤖 AI assistant</b></summary>

```
ai <question>                    Ask anything — uses your current folder, macros, and log as context
ai fix                           Auto-explain and suggest a fix for the last failed command
ai clear                         Reset conversation history
ai-model set qwen2.5:14b-instruct   Switch to the heavy model (better reasoning)
ai-model set llama3.1:8b            Switch to the light model (faster)
```

**Models:**
| Model | Size | Best for |
|---|---|---|
| `llama3.1:8b` | ~5 GB | Fast everyday questions (default) |
| `qwen2.5:14b-instruct` | ~9 GB | Complex reasoning, longer explanations |

The AI sees your current folder listing, recent command log, active macros, aliases, and flags — so answers are specific to your session.

</details>

<details>
<summary><b>🐳 Docker — containers, images, compose, power commands</b></summary>

Standard commands:
```
docker ps / docker ps all            List running / all containers
docker start|stop|restart <name>     Control a container
docker shell <name>                  Open interactive shell (bash or sh)
docker logs follow <name>            Stream logs live
docker run <image> -p 8080:80 -e KEY=VAL -n myname -d   Run with options
docker compose up|down|build         Manage compose services
docker clean                         Remove stopped containers + dangling images
docker doctor                        Check installation and daemon status
```

Power commands (not in standard Docker CLI):
```
docker wait <name>          Poll until container is running/healthy (max 60s)
docker errors <name>        Filter logs to error/warning lines only
docker env run <image>      Run image injecting .env vars from current folder
docker backup <name>        Save container config to a timestamped zip
docker clone <name> <new>   Duplicate container (same image + env, no port conflict)
docker watch <name>         Live logs + CPU/MEM stats overlay every 5 seconds
docker size <image>         Layer-by-layer size breakdown
docker port-check           Check compose file ports vs currently listening ports
docker prune-safe           Preview then safely remove stopped containers + dangling images
```

</details>

<details>
<summary><b>📁 Files, zip, backup</b></summary>

```
copy 'C:/A/file.txt' to 'C:/B/file.txt'
move 'notes.txt' to 'archive/notes.txt'
zip 'C:/Project' to 'C:/Backups'
unzip 'C:/archive.zip' to 'C:/Unpacked'
backup 'C:/Project' 'C:/Backups'         Timestamped zip (name_YYYY-MM-DD_HH-MM-SS.zip)
read 'config.json'                        Print file contents
delete 'C:/Temp/old_logs'                 Confirms unless batch ON; respects dry-run
undo                                      Undo the last action (up to 30 steps)
```

</details>

<details>
<summary><b>🔄 Macros & aliases</b></summary>

```
macro add deploy = batch on, backup 'C:/Proj' 'C:/Backups', git update "deploy", batch off
macro run deploy
macro list
macro edit deploy                          Re-opens the command pre-filled for editing
alias add dl = explore '%HOME%/Downloads'
```

Available variables: `%HOME%`  `%DATE%`  `%NOW%`

</details>

<details>
<summary><b>🏗️ Project tools</b></summary>

```
new flask / react / node / vue / fastapi / electron / discord   Create project from scratch
setup                                                           Auto-install deps for existing project
dev                                                             Start dev server + open browser
dev build                                                       Run specific package.json script
env set DATABASE_URL=postgres://localhost/mydb                  Add or update a .env key
env list                                                        Show all .env keys (values hidden)
env check                                                       Compare .env vs .env.example
```

</details>

<details>
<summary><b>🔍 Search & disk</b></summary>

```
find 'log'                       Filename search (recursive from current folder)
search 'java.io.IOException'     Search text inside files
/build C D                       Build path index for drives C and D
/find NBTExplorer 2.8            Global fuzzy search using the index
space 'C:/Downloads' depth 4 report   Disk usage with AI cleanup suggestions
```

</details>

---

## Safety

- **`dry-run on`** — preview what any command would do; nothing actually runs
- **`batch on`** — skip all confirmation prompts (useful inside macros)
- **`undo`** — reverse the last action; supports delete, move, copy, write, create, macros, aliases, config — up to 30 steps
- **`status`** — see current modes (Batch/DryRun/SSL), AI model, Java version, macro count, undo depth

---

## Requirements

- Windows 10 / 11
- Python 3.10+
- [Git for Windows](https://git-scm.com/) — for Git features
- [Ollama](https://ollama.com/download) — for the AI assistant (optional)

---

## Manuals

Full command references are in the `manuals/` folder:

- `CMC_AI_Manual_MINI.md` — compact reference for the light AI model (8b)
- `CMC_AI_Manual_MEDIUM.md` — full reference for the heavy AI model (14b)
- `AI_Manual.txt` — comprehensive technical reference for external AI use

---

*CMC is for local use only. Git operations respect `.gitignore` rules. Update CMC with `cmc update check` / `cmc update`.*
