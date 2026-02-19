# Computer Main Centre (CMC)
**A local command console for Windows** — file management, Git publishing, AI assistance, macros, and more in one place.

---

## Highlights

- **Git integration** — push, pull, clone, status, and more with simple commands like `git upload` and `git update`
- **Embedded AI assistant** — ask questions, get valid CMC commands, fix errors automatically. Runs fully offline via Ollama
- **Undo system** — undo almost any action (delete, move, copy, write, macros, aliases, config) up to 30 steps
- **Macros & aliases** — save and chain commands with commas: `macro add deploy = git upload, status`
- **Safe execution modes** — Dry-Run previews commands without running them; Batch skips all confirmations
- **Java version switching** — `java list`, `java change 21` (with automatic UAC elevation if needed)
- **Fast global file search** — index your drives with `/build` then search with `/find`
- **Download helpers** — `download`, `search web`
- **Project setup tools** — `projectsetup`, `websetup`, `webcreate`

---

## Requirements

- Windows 10 / 11
- Python 3.10+
- [Git for Windows](https://git-scm.com/) — for Git features
- [Ollama](https://ollama.com/download) — for the AI assistant (optional)

---

## Installation

**1. Install Python**
Download from https://python.org/downloads — check **"Add Python to PATH"** during install.

**2. Get CMC**
Download or clone this repository anywhere on your system.

**3. (Optional) Set up the AI**
Install [Ollama](https://ollama.com/download), then run `CMC_AI_Ollama_Setup.cmd` to download a model.

**4. Launch CMC**
Double-click `Start_CMC.vbs`

---

## Git Integration

CMC makes GitHub publishing straightforward:

```
git upload          push local changes to GitHub (stages, commits, pushes)
git update          pull latest changes from GitHub
git download        clone a repo into the current folder
git link            connect the current folder to an existing GitHub repo
git status          show branch, staged/unstaged changes
git log             recent commit history
git doctor          diagnose common git problems
```

---

## AI Assistant

The AI runs locally via Ollama — no internet required after setup.

```
ai how do I zip this folder?
ai create a macro that backs up my project
ai fix                          diagnose and explain the last failed command
ai clear                        reset conversation history
```

The assistant sees your current folder, recent command log, macros, aliases, and active flags — so answers are specific to your session. Answers are short by default; ask for more detail if needed.

**Models** (switch with `ai-model set <model>`):
| Model | Size | Use |
|---|---|---|
| `llama3.1:8b` | ~5 GB | Fast, everyday tasks (default) |
| `qwen2.5:14b-instruct` | ~9 GB | More capable, better reasoning |

---

## Macros & Aliases

```
macro add backup = git upload, status     chain commands with commas
macro run backup
macro list
alias add gs = git status
```

---

## Safety

- **`dry-run on`** — preview what a command would do, nothing actually runs
- **`batch on`** — skip all confirmation prompts (use carefully)
- **`undo`** — undo the last action; supports delete, move, copy, write, create, macros, aliases, config. Up to 30 steps.
- **`status`** — see all active modes, AI model, Java version, CMC update status, macro/alias counts, undo depth

---

## Manuals

Full command references are in the `manuals/` folder:
- `CMC_AI_Manual_MINI.md` — compact reference used by the light AI model
- `CMC_AI_Manual_MEDIUM.md` — full reference used by the heavy AI model

---

## Notes

- CMC is for local use — not remote execution
- Git operations respect `.gitignore` rules
- CMC updates itself: `cmc update check` / `cmc update`
