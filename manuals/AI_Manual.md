CMC AI MASTER MANUAL (SOURCE-ACCURATE)
Build snapshot: extracted from source code in this workspace
Date: 2026-02-20
Repo root: C:/Users/Wiggo/Desktop/CMC_Claude
Version marker: UpdateNotes/VERSION.txt = 366fed30a95f4d08b417b6f8acd708b4bc073ca1

Purpose
- This file is a strict, implementation-level manual for the current CMC build.
- It is written so external AI models can generate valid CMC commands and macros on first try.
- If this manual conflicts with older docs/help text/autocomplete hints, trust this manual.

============================================================
1) CORE PARSER RULES
============================================================

1.1 Command separators
- Top-level command chaining uses commas.
- Example: batch on, backup 'C:/Proj' 'C:/Backups', git update "before cleanup"

Splitter behavior:
- Commas inside quoted strings are NOT split.
- Full line is NOT split if the line starts with:
  - timer ...
  - macro add ...

1.2 Comment lines
- Any command line starting with # is ignored.

1.3 Case sensitivity
- Command matching is generally case-insensitive.

1.4 Quote behavior
- Many commands REQUIRE quoted paths (single quotes are safest).
- Some commands allow unquoted input (cd, open url, search web query text).
- For AI reliability, always use single-quoted paths.

1.5 Execution model
- CMC keeps its own virtual working directory (CWD variable).
- CMC does not call os.chdir() for normal navigation.
- Most commands respect CMC CWD, but see known defects section for exceptions.

============================================================
2) COMMAND EVALUATION ORDER (IMPORTANT)
============================================================

Command routing order inside handle_command is roughly:
1. config ...
2. space ...
3. model ... / ai-model ...
4. ai ...
5. cmd <inline shell command>
6. alias expansion
7. selftest commands
8. cmc update check / cmc update
9. git ... (delegated to CMC_Git.py)
10. docker ... (delegated to CMC_Docker.py)
11. setup / new ... / dev ... / env ...
12. timer / sleep / sendkeys / run
13. help / ? / status / batch / dry-run / ssl / log / undo / echo / exit
14. alias add/delete/list
15. java list/version/reload/change
16. sysinfo
17. file/navigation/search/download/index routes
18. cmd (interactive session)
19. unknown-command suggestions

Why this matters:
- Alias expansion happens before most command routes, so aliases can shadow built-ins.
- cmd <something> route executes before alias expansion.

============================================================
3) STATE, FLAGS, AND PERSISTENCE
============================================================

3.1 Runtime flags (STATE)
- batch: auto-confirms all prompt-based confirmations.
- dry_run: blocks operations that call confirm(...), but does NOT globally block all commands.
- ssl_verify: controls SSL verification for download requests.

3.2 Persisted files
- ~/.ai_helper/macros.json
- ~/.ai_helper/aliases.json
- ~/.ai_helper/.cmc_trash/   (for undoable delete)
- ~/.ai_helper/.cmc_first_run_done
- ~/.ai_helper/java.json
- ~/.ai_helper/cmc_update.json
- ~/.ai_helper/github.json (Git token + folder->repo map)
- src/CMC_Config.json (persistent config)
- src/CentreIndex/paths.db (path index DB used by /build and /find)

3.3 Undo system
- In-memory stack only, max depth 30.
- Not persisted across restarts.
- Undo supports: move, rename, delete (restore from trash), copy, create file/folder,
  write restore, macro add/delete/clear/edit, alias add/delete, config changes.

============================================================
4) SAFETY MODES (ACTUAL BEHAVIOR)
============================================================

4.1 batch on/off
- Commands:
  - batch on
  - batch off
- Effect: confirm(...) auto-returns yes.

4.2 dry-run on/off
- Commands:
  - dry-run on
  - dry-run off
- Effect: only impacts commands that use confirm(...).
- Commands that do NOT call confirm still execute even with dry-run ON (example: run, zip, unzip, java change, git, docker).

4.3 ssl on/off
- Commands:
  - ssl on
  - ssl off
- Effect: affects download requests SSL verification.

============================================================
5) CONTROL AND UTILITY COMMANDS
============================================================

5.1 Help and status
- help
- help <topic>
- ?
- status

5.2 Logs and undo
- log
- undo

5.3 Echo
- echo <text>
- echo 'text'
- echo "text"

5.4 Exit
- exit

5.5 Hidden dev command
- selftest commands
- Prints detected op_* functions and regex routes.

============================================================
6) NAVIGATION COMMANDS
============================================================

6.1 Working directory commands
- home
- cd home
- cd
- cd ~
- back
- cd ..
- ..
- cd..
- ../
- cd '<path>'
- cd <unquoted_path>
- pwd

Notes:
- back uses in-session path history; if no previous path, it prints warning.

============================================================
7) LISTING, INFO, SEARCH
============================================================

7.1 List
Accepted syntax:
- list
- list '<path>'
- list '<path>' depth <n>
- list '<path>' only files
- list '<path>' only dirs
- list '<path>' pattern <glob>   (e.g. *.py)

Behavior:
- Recursively walks depth=1 by default.
- depth clamps how many directory levels are walked.
- only files / only dirs filters the result type.
- pattern applies fnmatch filtering on file/dir names.
- Shows rows with full path + type.

7.2 Info
- info '<path>'

7.3 File name search
- find '<pattern>'
- findext '.ext'
- findext .ext

7.4 Time/size scans
- recent
- recent '<path>'
- biggest
- biggest '<path>'

7.5 Text search in files
- search '<text>'

7.6 Known behavior caveat
- find and findext currently search from Path.cwd() (OS process cwd), not CMC virtual CWD.
- recent, biggest, search '<text>', and list use CMC virtual CWD correctly.

============================================================
8) FILE/FOLDER COMMANDS (EXACT FORMS)
============================================================

8.1 Create
- create file '<name>' in '<folder>'
- create file '<name>' in '<folder>' with text='...'
- create file '<name>' in '<folder>' with text="..."
- create folder '<name>' in '<folder>'

8.2 Write
- write '<file_path>' text='...'
- write '<file_path>' text="..."

8.3 Read
- read '<file_path>'
- read '<file_path>' [head=50]

8.4 Move/copy/rename/delete
- move '<src>' to '<dst_folder>'
- copy '<src>' to '<dst_folder>'
- rename '<src>' to '<new_name_or_relative_target>'
- delete '<path>'

Important semantic details:
- move and copy treat destination as a folder, then place src.name inside it.
- rename is NOT an alias of move; it renames relative to src.parent.
- delete moves item into ~/.ai_helper/.cmc_trash, enabling undo restore.

8.5 Open/explore
- open '<file_or_url>'
- explore '<folder_or_file>'

8.6 Zip/unzip/backup
- zip '<source>'
- zip '<source>' to '<dest_folder>'
- unzip '<zip_file>'
- unzip '<zip_file>' to '<dest_folder>'
- backup '<source>' '<dest_folder>'

Notes:
- zip/unzip do not use confirm(), so dry-run does not block them.
- backup does use confirm(), so dry-run blocks it.
- backup output name: <name>_YYYY-MM-DD_HH-MM-SS.zip

============================================================
9) CMD AND RUN COMMANDS
============================================================

9.1 Inline shell command
- cmd <shell command>

Behavior:
- Runs with shell=True and captures stdout/stderr.
- Honors dry-run (prints would-run only).

9.2 Interactive cmd session
- cmd

Behavior:
- Opens full Windows cmd shell (os.system("cmd")).
- If batch off, asks confirmation first.
- dry-run skips opening.

9.3 run command
- run '<command_or_path>'
- run '<command_or_path>' in '<working_folder>'

Behavior:
- Uses subprocess.Popen(..., shell=True).
- No confirmation prompt.
- Not blocked by dry-run.
- Good for .py/.exe/.bat/.cmd/.vbs and arbitrary shell command text.

============================================================
10) AUTOMATION COMMANDS
============================================================

10.1 Sleep
- sleep <seconds>

10.2 Timer
- timer <seconds>
- timer <seconds> <action_or_message>

Timer behavior:
- If action starts with run ... or macro ..., timer executes that command when due.
- During timer-triggered run/macro execution, batch is forced ON temporarily.
- Otherwise timer prints action text as reminder.

10.3 Send keys
- sendkeys "text{ENTER}more"

Behavior:
- Uses pyautogui.
- Splits {ENTER} tokens and presses Enter between chunks.

============================================================
11) PORT COMMANDS
============================================================

- ports
- kill <port_number>

Behavior:
- ports lists TCP LISTEN sockets with PID and process name (psutil).
- kill <port> kills processes listening on that TCP port.

============================================================
12) INTERNET/DOWNLOAD COMMANDS
============================================================

12.1 Open URL directly
- open url <url>
- open url '<url>'

12.2 Web search
- search web <query>

12.3 Download single
- download '<url>' to '<dest_folder>'

12.4 Download batch from file
- downloadlist '<file_with_urls>' to '<dest_folder>'

Download behavior details:
- Output filename is inferred from URL path; custom output filename is not supported by parser.
- 1 GB hard cap; aborts if content-length exceeds cap (HEAD or GET stream checks).
- Uses requests if installed, otherwise urllib fallback.
- Uses ssl_verify flag.
- Calls confirm() before download, so dry-run blocks writes.
- After download, asks whether to open containing folder.

============================================================
13) MACROS
============================================================

13.1 Commands
- macro add <name> = <command_chain>
- macro run <name>
- macro edit <name>
- macro list
- macro delete <name>
- macro clear

13.2 Macro variables expanded at runtime
- %DATE% -> YYYY-MM-DD
- %NOW%  -> YYYY-MM-DD_HH-MM-SS
- %HOME% -> user home path

13.3 Separators
- Preferred separator is comma.
- Backward compatibility: if macro body has semicolons and no commas, semicolon split is used.

13.4 Persistence
- Stored in ~/.ai_helper/macros.json

============================================================
14) ALIASES
============================================================

14.1 Commands
- alias add <name> = <command>
- alias delete <name>
- alias list

14.2 Alias expansion behavior
- Alias expansion occurs early in routing.
- If user types alias with extra args, they are appended:
  alias_target + " " + remaining_args

14.3 Important caveat
- This build does not block alias names that collide with built-in commands.
- So aliases can shadow native commands.

14.4 Persistence
- Stored in ~/.ai_helper/aliases.json

============================================================
15) CONFIG COMMANDS
============================================================

15.1 Commands
- config
- config help
- config list
- config get <key>
- config set <key> <value>
- config reset

15.2 Short key aliases accepted by config set/get
- batch -> batch
- dry_run -> dry_run
- ssl_verify -> ssl_verify
- open_browser -> git.open_browser
- show_update -> header.show_update
- show_path -> prompt.show_path
- default_depth -> space.default_depth
- auto_ai -> space.auto_ai
- auto_report -> space.auto_report

15.3 Value parsing
- Bool forms: 1/0, true/false, yes/no, on/off
- Then int parse
- Then float parse
- Else raw string

15.4 Persistent config file
- src/CMC_Config.json

15.5 Important caveat
- ai.model is not in DEFAULT_CONFIG schema, so config command does not manage it.

============================================================
16) JAVA COMMANDS
============================================================

16.1 Commands
- java list
- java version
- java reload
- java change <version_or_key_or_path>

16.2 java change behavior
- Accepts:
  - known key from detected JAVA_VERSIONS (example: 8, 17, 21)
  - partial match against key/path
  - full existing path
- Updates process JAVA_HOME/PATH immediately.
- Tries user-level registry env update (HKCU\Environment).
- Tries system-level env update (HKLM) and may request UAC elevation.

16.3 java reload behavior
- Reads JAVA_HOME from registry (user/system), applies to process env.

============================================================
17) SYSTEM INFO
============================================================

- sysinfo
- sysinfo save '<file_path>'

Outputs OS/CPU/cores/RAM/GPU/PSU/uptime summary.

============================================================
18) SPACE COMMAND (DISK USAGE)
============================================================

Entry route:
- Any command starting with space delegates to CMC_Space.op_space.

Accepted syntax patterns:
- space
- space '<path>'
- space '<path>' depth <n>
- space '<path>' report
- space '<path>' depth <n> report
- space '<path>' full
- space '<path>' full report

Token parsing notes:
- Parser uses shlex for the part after space.
- First non-keyword token becomes target path.
- depth is clamped to 1..6.
- full sets depth=4.

Outputs:
- Top folders
- Largest files
- Heuristic junk candidates
- Stores summary in state['last_space_scan']

Report mode:
- Writes JSON report to <target>/CMC_space_report.txt

AI integration:
- After scan, asks: Run AI cleanup suggestions? (y/n)
- If yes, sends summary JSON to embedded AI with strict safe-cleanup prompt.

Caveat:
- space config keys (space.default_depth, space.auto_ai, space.auto_report) exist in config,
  but current CMC_Space implementation uses hardcoded defaults unless command arguments override.

============================================================
19) PATH INDEX COMMANDS
============================================================

19.1 /find
- /find <query>
- /find <query> <limit_int>
- Default limit = 20.
- Uses src/path_index_local.py super_find() over sqlite DB.

19.2 /build
- /build <targets>
Examples that work best:
- /build C D
- /build C D E

Behavior details:
- Current route passes target text as one string into quick_build().
- quick_build iterates the string character-by-character.
- For drive-letter style input (C D E), this still works in practice.
- /build with no targets currently errors.

19.3 /qcount
- Route exists, but currently imports quick_count from path_index_local.py.
- quick_count is missing in current module.
- Result: /qcount fails in this build.

============================================================
20) AI COMMANDS
============================================================

20.1 Assistant commands
- ai <question>
- ai fix
- ai clear

20.2 Model manager commands
- ai-model list
- ai-model current
- ai-model set <model>
- model list
- model current
- model set <model>

ai-model list behavior:
- Tries Ollama from PATH first.
- Falls back to common Windows install paths:
  - %LOCALAPPDATA%/Programs/Ollama/ollama.exe
  - %ProgramFiles%/Ollama/ollama.exe
  - %ProgramFiles(x86)%/Ollama/ollama.exe

20.3 ai fix behavior
- Uses _LAST_CMD and _LAST_ERROR globals, set whenever a command fails OR is unrecognised.
- Works on both Python exceptions (error = exception message) AND unknown/typo commands (error = "Unknown command").
- When error is "Unknown command", asks AI what the user likely meant and what the correct syntax is.
- A one-time tip ("Tip: type 'ai fix'") is shown on the first unknown command; suppressed forever after via sentinel file ~/.ai_helper/.cmc_ai_fix_tip_shown.

20.4 Context passed to AI
- Current CWD listing (top-level truncated)
- Flags (batch/dry_run/ssl)
- Java version
- Full macros (name + body)
- Full aliases (name + command)
- Recent log entries
- recent_commands: rolling list of last 20 raw commands typed this session (includes typos/unknowns)
- last_issue: {command: str, error: str} for the most recently failed or unrecognised command

20.5 Manual selection behavior in assistant_core
- If model name contains 14b/32b/70b/72b -> loads manuals/CMC_AI_Manual_MEDIUM.md
- Else -> loads manuals/CMC_AI_Manual_MINI.md

20.6 Model persistence (current behavior)
- ai-model set persists to src/CMC_Config.json at key ai.model.
- Save flow performs write+reload verification before reporting success.
- Model can also be changed via:
  - config set ai_model <model>
  - config set ai.model <model>

============================================================
21) GIT COMMANDS (CMC_Git.py)
============================================================

21.1 Core supported commands
- git doctor
- git open
- git link <owner/repo|github_url>
- git repo list [all|mine]
- git repo delete <owner/repo|repoName>
- git download <owner/repo|url>
- git clone <owner/repo|url>   (alias of download path)
- git upload
- git update [repoSpec_or_repoName_or_message] [message] [--add <path>] [--add <path2> ...]
- git force upload
- git force update [repoSpec_or_repoName_or_message] [message] [--add <path>] [--add <path2> ...]
- git debug upload
- git debug update [repoSpec_or_repoName_or_message] [message] [--add <path>] [--add <path2> ...]
- git branch
- git branch list
- git branch create <name>
- git branch new <name>
- git branch switch <name>
- git branch go <name>
- git branch checkout <name>
- git branch delete <name>
- git branch merge <name>

21.2 Pass-through behavior
- Any unrecognized git ... command is forwarded to real git CLI.

21.3 git update argument parsing rules (important)
Given tokens after git update (or force/debug update):
- If first token looks like owner/repo or github URL -> repo spec.
- Else if first token contains spaces -> commit message.
- Else if first token is --add -> no repo/message yet.
- Else single-word token is treated as repo spec (back-compat), not message.

Practical guidance:
- If commit message is one word, quote it anyway.
- Best safe forms:
  - git update "my message"
  - git update owner/repo "my message"
  - git update owner/repo "my message" --add src/file.py

21.4 GitHub credentials and mapping
- Token and folder mapping saved in ~/.ai_helper/github.json
- Stores:
  - token
  - repos[folder_path] = {owner, name, remote}

21.5 git upload behavior summary
- Prompts for repo name, visibility, token if needed, commit message.
- Ensures repo initialized and branch main.
- Ensures/updates .gitignore with DEFAULT_GITIGNORE_PATTERNS.
- Commits and pushes.
- Saves folder mapping.
- Opens browser if config git.open_browser = true.

21.6 git update behavior summary
- Uses explicit repo arg, origin remote, or remembered mapping.
- Auto commit message default: Update YYYY-MM-DD HH:MM
- Supports partial staging with repeated --add <path>.

21.7 force/debug flows
- Try to auto-repair common issues (missing init, branch mismatch, lock files, remote mismatch).
- debug mode prints richer step output.
- On failure, writes CMC_GIT_DEBUG_*.txt report in repo root.

21.8 git repo delete
- Requires typing DELETE exactly.
- Deletes remote GitHub repo only; local files remain.

============================================================
22) DOCKER COMMANDS (CMC_Docker.py)
============================================================

22.1 Container inspection/control
- docker ps
- docker ps all
- docker start <container>
- docker stop <container>
- docker restart <container>
- docker remove <container>
- docker rm <container>   (same route)
- docker shell <container>
- docker logs <container>
- docker logs <container> follow
- docker logs follow <container>
- docker stats
- docker stats <container>
- docker inspect <container_or_image>
- docker ip <container>

22.2 Images/build/run
- docker images
- docker build <tag>
- docker build <tag> <path>
- docker pull <image>
- docker push <image>
- docker run <image>
- docker run <image> -d
- docker run <image> -p <host:container> -e KEY=VAL -n <name> -d

Run details:
- Detached mode: docker run ... -d
- Non-detached mode: runs interactive with -it --rm.

22.3 Volumes/networks
- docker volumes
- docker volume remove <name>
- docker volume rm <name>
- docker networks
- docker network remove <name>
- docker network rm <name>

22.4 Cleanup
- docker clean                           removes stopped containers + dangling images
- docker clean all                       full system prune (containers, images, volumes, networks)
- docker prune-safe                      previews what will be removed, then removes stopped containers + dangling images (volumes/networks untouched)

22.5 Compose
- docker compose up
- docker compose down
- docker compose logs
- docker compose logs follow
- docker compose build
- docker compose ps
- docker compose restart

22.6 Diagnostics
- docker doctor

22.7 Power commands (CMC-only, not in standard Docker CLI)
- docker wait <container>
  Poll until container is running + healthy (max 60s, 1s interval). Prints status each second.
  Reports "unhealthy" if healthcheck fails.

- docker errors <container>
  Fetches last 500 log lines and filters to lines matching: error, fatal, exception, traceback, critical, failed, panic, warn.
  Shows at most 50 matches. Returns green message if none found.

- docker env run <image>
  Reads .env from current working directory and passes each key=value as -e to docker run.
  Runs interactively with --rm.

- docker prune-safe
  Lists stopped containers (status=exited) and dangling images, then removes them.
  Does NOT touch volumes, networks or in-use images.

- docker backup <container>
  Saves docker inspect output (JSON) + a README.md to a zip:
  docker_backup_<name>_YYYY-MM-DD_HH-MM-SS.zip in current folder.
  Does NOT include volume data (instructions for that are in README.md).

- docker clone <container> <new-name>
  Reads image + env + restart policy from source container.
  Starts a detached clone under new-name.
  Port bindings are NOT copied (would conflict; user adds -p manually).

- docker watch <container>
  Streams docker logs -f (tail 20) in foreground.
  Background thread prints CPU/MEM/NET stats every 5 seconds.
  Ctrl+C stops both.

- docker size <image>
  Runs docker history --no-trunc and shows each layer's size + command.
  Strips /bin/sh -c prefix for readability. Shows total from docker images.

- docker port-check
  Reads docker-compose.yml (or compose.yml) from current folder.
  Extracts host:container port pairs (regex). Checks each host port against
  netstat -ano output. Reports each port as free or IN USE.

22.8 Pass-through
- Unrecognized docker ... commands are forwarded to real docker CLI.

============================================================
23) PROJECT SCAFFOLD/DEV/ENV COMMANDS (CMC_Scaffold.py)
============================================================

23.1 setup
- setup
- Auto-detects project type and performs setup tasks (dependency installs, env copy, etc).

23.2 new
- new
- new python
- new node
- new flask
- new fastapi
- new react
- new vue
- new svelte
- new next
- new electron
- new discord
- new cli
- new web   (delegates to CMC_Web_Create.op_web_create wizard)

23.3 dev
- dev
- dev <npm_script>
- dev stop

23.4 env manager
- env list
- env show
- env get <KEY>
- env set KEY=value
- env delete <KEY>
- env template
- env check

23.5 Known setup caveat in current build
- CMC_Scaffold.handle_setup references _launch_dev and _launch_dev_python,
  but those functions are missing in this file.
- If setup path reaches those calls, it can error.

============================================================
24) WEB CREATE WIZARD (USED BY `new web`)
============================================================

Interactive flow:
1. Ask project name.
2. Ask target folder.
3. Ask frontend: none|vanilla|react|vue|svelte
4. Ask backend: none|express|flask|fastapi
5. Confirm and generate structure.

Generated components include:
- client/ (if frontend selected)
- server/ (if backend selected)
- start_app.bat launcher
- root README.md

============================================================
25) UPDATE COMMANDS
============================================================

25.1 Commands
- cmc update check
- cmc update

25.2 Update behavior
If install is a git repo:
- creates backup zip first
- git fetch --all --prune
- git reset --hard origin/<branch>
- git clean -fd with exclusions:
  - .ai_helper
  - CentreIndex
  - paths.db

If install is non-git (zip style):
- fetches latest zipball from GitHub API
- copies files over with skip rules
- preserves excluded local/generated files per skip list

State files updated:
- ~/.ai_helper/cmc_update.json installed_sha
- UpdateNotes/VERSION.txt

Caution:
- cmc update in git mode is destructive to uncommitted tracked changes due hard reset.

============================================================
26) REMOVED OR NON-ROUTED LEGACY NAMES
============================================================

26.1 Removed legacy command names (do not use):
- websetup
- webcreate (direct command; now replaced by new web route)
- projectsetup

26.2 Names suggested in hints/autocomplete but not routed:
- /gitsetup
- /gitlink
- /gitupdate
- /gitpull
- /gitstatus
- /gitlog
- /gitbranch
- /gitignore add
- /gitclean
- /gitdoctor
- /gitfix
- /gitlfs setup

Additional mismatches:
- projectscan command has been fully removed (handler deleted from handle_command).
- /qcount route calls missing quick_count in path_index_local.py (fails).
- Help text mentions download_list and optional output filename for download; parser accepts only:
  - download '<url>' to '<dest_folder>'
  - downloadlist '<urls_file>' to '<dest_folder>'

============================================================
27) RELIABILITY TEMPLATES FOR AI-GENERATED MACROS
============================================================

Use these exact templates when generating commands for users.

27.1 Safe file workflow
- dry-run on, list, find 'target', dry-run off

27.2 Backup + git push
- backup '%HOME%/MyProject' '%HOME%/Desktop', git update "backup before changes"

27.3 Partial git update
- git update owner/repo "update one file" --add src/main.py

27.4 Download workflow
- download 'https://example.com/file.zip' to 'C:/Users/User/Downloads'

27.5 Space report
- space 'C:/Users/User/Downloads' depth 4 report

27.6 Java switch
- java list
- java change 17
- java version

27.7 Dev run for known npm script
- dev build

27.8 Env management
- env set API_URL=https://api.example.com
- env check

============================================================
28) STRICT COMMAND INDEX (ONE-LINE FORMS)
============================================================

Control:
- help
- help <topic>
- ?
- status
- log
- undo
- exit
- echo <text>
- selftest commands

Modes:
- batch on
- batch off
- dry-run on
- dry-run off
- ssl on
- ssl off

Navigation:
- home
- back
- cd
- cd ~
- cd ..
- cd '<path>'
- cd <path>
- pwd
- list
- list '<path>'
- list '<path>' depth <n>
- list '<path>' only files
- list '<path>' only dirs
- list '<path>' pattern <glob>

Search:
- info '<path>'
- find '<pattern>'
- findext '.ext'
- recent
- recent '<path>'
- biggest
- biggest '<path>'
- search '<text>'

File ops:
- create file '<name>' in '<folder>'
- create file '<name>' in '<folder>' with text='...'
- create folder '<name>' in '<folder>'
- write '<file>' text='...'
- read '<file>'
- read '<file>' [head=50]
- move '<src>' to '<dst_folder>'
- copy '<src>' to '<dst_folder>'
- rename '<src>' to '<new_name>'
- delete '<path>'
- zip '<source>'
- zip '<source>' to '<dest_folder>'
- unzip '<zipfile>'
- unzip '<zipfile>' to '<dest_folder>'
- open '<file_or_url>'
- explore '<folder>'
- backup '<src>' '<dest_folder>'

Shell/run:
- cmd
- cmd <shell command>
- run '<command_or_path>'
- run '<command_or_path>' in '<folder>'
- sleep <sec>
- timer <sec> [action_or_message]
- sendkeys "text{ENTER}"
- ports
- kill <port>

Web/download:
- open url <url>
- open url '<url>'
- search web <query>
- download '<url>' to '<dest_folder>'
- downloadlist '<urls_file>' to '<dest_folder>'

Macros/aliases:
- macro add <name> = <chain>
- macro run <name>
- macro edit <name>
- macro list
- macro delete <name>
- macro clear
- alias add <name> = <command>
- alias delete <name>
- alias list

Config:
- config
- config list
- config get <key>
- config set <key> <value>
- config reset

Java/sys:
- java list
- java version
- java reload
- java change <ver_or_path>
- sysinfo
- sysinfo save '<file>'

Space/index:
- space
- space '<path>' [depth <n>] [report] [full]
- /build C D E
- /find <query> [limit]
- /qcount (currently broken)

AI:
- ai <question>
- ai fix
- ai clear
- ai-model list
- ai-model current
- ai-model set <model>
- model list
- model current
- model set <model>

Scaffold/dev/env:
- setup
- new
- new python|node|flask|fastapi|react|vue|svelte|next|electron|discord|cli|web
- dev
- dev <script>
- dev stop
- env list|show|get|set|delete|template|check

Git:
- git doctor
- git open
- git link <owner/repo|url>
- git repo list [all|mine]
- git repo delete <owner/repo|repoName>
- git download <owner/repo|url>
- git clone <owner/repo|url>
- git upload
- git update ...
- git force upload
- git force update ...
- git debug upload
- git debug update ...
- git branch [list|create|switch|delete|merge]
- git <anything_else> (pass-through)

Docker:
- docker doctor
- docker ps [all]
- docker images
- docker start|stop|restart <name>
- docker remove|rm <name>
- docker shell <name>
- docker logs <name>|follow <name>
- docker stats [name]
- docker inspect <name>
- docker ip <name>
- docker build <tag> [path]
- docker pull <image>
- docker push <image>
- docker run <image> [-p ...] [-e ...] [-n ...] [-d]
- docker volumes
- docker volume remove|rm <name>
- docker networks
- docker network remove|rm <name>
- docker clean [all]
- docker prune-safe
- docker compose up|down|logs [follow]|build|ps|restart
- docker wait <name>
- docker errors <name>
- docker env run <image>
- docker backup <name>
- docker clone <name> <new-name>
- docker watch <name>
- docker size <image>
- docker port-check
- docker <anything_else> (pass-through)

Update:
- cmc update check
- cmc update

============================================================
END OF MANUAL
============================================================
