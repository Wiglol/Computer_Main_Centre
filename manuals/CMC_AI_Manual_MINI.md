CMC_AI_MINI_SPEC (v4)
GROUND TRUTH. Use ONLY these commands + their documented variants.
Paths MUST use single quotes. Chain commands with ',' (no trailing ',').

═══════════════════════════════════════
CORE RULES
═══════════════════════════════════════
- Paths: ALWAYS single quotes: cd 'C:/Users/Name/Desktop'
- Chain: cmd1, cmd2, cmd3  (no trailing comma)
- If user asks "what do I type" → output commands inside a ```cmc``` block
- Destructive commands only if user explicitly asked (delete, git repo delete, /gitclean, etc.)
- Prefer: dry-run on before risky ops
- batch on auto-confirms all prompts (use carefully)
- ssl on/off affects downloads
- When unsure → ask ONE short clarifying question

═══════════════════════════════════════
STATUS / SAFETY
═══════════════════════════════════════
status            show full status: Batch / SSL / Dry-Run, AI model, Java, CMC update, macro/alias counts, undo depth
log               show recent operation log
undo              undo the last action (move, rename, delete, copy, write,
                  create file/folder, macro add/delete/clear,
                  alias add/delete, config set/reset)
cmd               open a Windows CMD session inside CMC

Modes (toggle):
  batch on / batch off
  dry-run on / dry-run off
  ssl on / ssl off

═══════════════════════════════════════
NAVIGATION
═══════════════════════════════════════
cd '<path>'       change directory
cd ..             go up one level
cd                go to HOME
home              go to HOME (explicit)
back              go back to previous directory
pwd               show current path

═══════════════════════════════════════
LISTING
═══════════════════════════════════════
list                          list current folder
list '<path>'
list '<path>' depth <n>
list '<path>' only files
list '<path>' only dirs
list '<path>' pattern <glob>   e.g. *.py

═══════════════════════════════════════
OPEN / EXPLORE
═══════════════════════════════════════
open '<file-or-url>'      open in default app or browser
explore '<folder>'        open folder in Windows Explorer

═══════════════════════════════════════
FILES
═══════════════════════════════════════
read '<file>'              print full file contents

create folder '<name>' in '<path>'
create file '<name>' in '<path>'

write '<file>' <text>      overwrite file (confirms; respects dry-run)

copy '<src>' to '<dst>'
move '<src>' to '<dst>'
rename '<src>' to '<dst>'
delete '<path>'            danger — confirms unless batch on; respects dry-run

═══════════════════════════════════════
ZIP / BACKUP
═══════════════════════════════════════
zip '<source>' to '<destination-folder>'
zip '<source>'                              (zips to source's parent)
unzip '<zipfile.zip>' to '<destination-folder>'
backup '<source>' '<destination-folder>'    timestamped zip

═══════════════════════════════════════
SEARCH
═══════════════════════════════════════
find '<pattern>'           recursive filename search (current folder)
findext '.ext'             find by extension
recent                     recently modified files
biggest                    largest files
search '<text>'            search text inside files
info '<path>'              show file/folder details

═══════════════════════════════════════
PATH INDEX (fast global)
═══════════════════════════════════════
/build C D E               build index of drives C, D, E
/find <query>              fuzzy search across index
/qcount                    show how many paths are indexed

═══════════════════════════════════════
SPACE (disk usage)
═══════════════════════════════════════
space                             current folder
space '<path>'
space '<path>' depth <n>
space '<path>' depth <n> report   generate cleanup suggestions
space '<path>' full               all subdirs

Rules for space report suggestions:
- Only suggest caches, temp, duplicates
- Never suggest deleting system/OS folders
- Always confirm before deletion plan

═══════════════════════════════════════
CONFIG
═══════════════════════════════════════
config list
config get <key>
config set <key> <value>
config reset

Notable keys:
  ai.model            active AI model
  batch               true/false
  dry_run             true/false
  space.default_depth number
  space.auto_ai       true/false

═══════════════════════════════════════
MACROS
═══════════════════════════════════════
macro add <name> = <cmd1>, <cmd2>, ...
macro run <name>
macro list
macro delete <name>
macro clear

Runtime variables: %HOME%  %DATE%  %NOW%
Rules: single quotes on paths, commas between commands, no trailing comma

Example:
  macro add publish = batch on, zip '%HOME%/Project' to '%HOME%/Desktop', git update "release %NOW%", batch off

═══════════════════════════════════════
ALIASES (single command only, no commas)
═══════════════════════════════════════
alias add <name> = <cmd>
alias list
alias delete <name>

Example:
  alias add dl = explore '%HOME%/Downloads'

═══════════════════════════════════════
GIT (friendly)
═══════════════════════════════════════
git upload
  New GitHub repo from current folder. Inits git if needed, commits, pushes, stores mapping.
  Creates/updates .gitignore (untracked-only).

git update
  Commit + push to the linked repo for this folder.

git update "<message>"
  Commit with custom message (does NOT change repo link).

git update <owner>/<repo> ["message"]
  Relink to that repo, then commit + push.

git update <owner>/<repo> ["message"] --add <file-or-folder>
  Partial commit: only stage that path, then push.

git download <owner>/<repo>
  Clone repo into current folder.

git link <owner>/<repo>   (or GitHub URL)
  Set origin for current folder.

git status
git log
git doctor
git repo list
git repo delete <repo>    danger — deletes on GitHub; local untouched

Self-healing (when git is cursed):
  git force upload
  git force update [<owner>/<repo>] ["message"] [--add <path>]
  git debug upload
  git debug update [<owner>/<repo>] ["message"] [--add <path>]

Force/debug auto-fixes: missing init, wrong branch, index.lock, origin mismatch.
If origin contains '<you>' placeholder → tell user to run git link first.

═══════════════════════════════════════
JAVA
═══════════════════════════════════════
java list                  show detected Java installations
java version               show active Java version
java change <8|17|21>      switch Java (updates JAVA_HOME + Path, may request UAC)
java reload                reload Java from registry

═══════════════════════════════════════
PROJECT / WEB
═══════════════════════════════════════
projectsetup
websetup
webcreate

═══════════════════════════════════════
RUN / AUTOMATION
═══════════════════════════════════════
run '<path>'
run '<script>' in '<folder>'
sleep <sec>
timer <sec> [message]
sendkeys "text{ENTER}"     only if user explicitly asked

═══════════════════════════════════════
DOWNLOAD / WEB
═══════════════════════════════════════
search web <query>
open url '<url>'
download '<url>' to '<destination-folder>'
downloadlist '<urls.txt>' to '<destination-folder>'

═══════════════════════════════════════
AI
═══════════════════════════════════════
ai <question>
ai fix                     diagnose the last failed command
ai clear                   reset conversation history
ai-model list              list installed Ollama models
ai-model current           show active model
ai-model set <model>       switch model

Available models:
  llama3.1:8b              light / fast (default)
  qwen2.5:14b-instruct     heavier / more capable

Aliases: model list | model current | model set <model>

CONTEXT AVAILABLE TO AI:
The AI can see: current folder listing, macro names+bodies, alias names+commands,
recent log, java version, and active flags. Use this to give specific answers.

═══════════════════════════════════════
SYSINFO
═══════════════════════════════════════
sysinfo                    show system info panel
sysinfo save '<file>'      save sysinfo to file

═══════════════════════════════════════
HELP
═══════════════════════════════════════
help                       full help index
help <topic>               help for specific section
