# CMC_Docker.py — Docker module for Computer Main Centre
#
# Simplified commands:
#   docker ps                    list running containers
#   docker ps all                list all containers (including stopped)
#   docker images                list local images
#   docker start <name>          start a stopped container
#   docker stop <name>           stop a running container
#   docker restart <name>        restart a container
#   docker remove <name>         stop + remove a container
#   docker shell <name>          open interactive shell in container (tries bash then sh)
#   docker logs <name>           show logs (last 50 lines)
#   docker logs follow <name>    stream logs live
#   docker stats                 live resource usage for all running containers
#   docker stats <name>          live resource usage for one container
#   docker build <tag>           build image from Dockerfile in current folder
#   docker build <tag> <path>    build image from Dockerfile at given path
#   docker pull <image>          pull image from Docker Hub
#   docker push <image>          push image to registry
#   docker run <image>           run a container (interactive prompt for options)
#   docker run <image> -p <host:container> -e KEY=VAL -n <name> -d
#   docker volumes               list volumes
#   docker volume remove <name>  remove a volume
#   docker networks              list networks
#   docker network remove <name> remove a network
#   docker clean                 remove stopped containers + dangling images
#   docker clean all             full system prune (containers, images, volumes, networks)
#   docker compose up            docker compose up -d in current folder
#   docker compose down          docker compose down in current folder
#   docker compose logs          stream compose logs
#   docker compose build         rebuild compose images
#   docker compose ps            list compose services
#   docker compose restart       restart all compose services
#   docker inspect <name>        show container/image details (formatted)
#   docker ip <name>             show container IP address
#   docker doctor                check docker installation + daemon status
#
# Pass-through:
#   Any unrecognised "docker ..." is forwarded to the real docker CLI.

import shutil
import subprocess
import shlex
from pathlib import Path
from typing import Callable, List, Tuple, Optional

PFunc = Callable[[str], None]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _docker_installed() -> bool:
    return bool(shutil.which("docker"))

def _docker_run(args: List[str], cwd=None) -> Tuple[int, str]:
    try:
        r = subprocess.run(
            ["docker"] + args,
            cwd=str(cwd) if cwd else None,
            text=True,
            capture_output=True,
        )
        out = (r.stdout or "").strip()
        err = (r.stderr or "").strip()
        combined = (out + ("\n" + err if err else "")).strip()
        return r.returncode, combined or "(done)"
    except Exception as e:
        return 1, str(e)

def _docker_run_live(args: List[str], cwd=None) -> None:
    """Run docker command with live output (for logs -f, stats, etc.)."""
    try:
        proc = subprocess.Popen(
            ["docker"] + args,
            cwd=str(cwd) if cwd else None,
            text=True,
        )
        proc.wait()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(str(e))

def _compose_installed() -> bool:
    rc, _ = _docker_run(["compose", "version"])
    return rc == 0

def _tokens(raw: str) -> List[str]:
    try:
        return shlex.split(raw, posix=False)
    except Exception:
        return raw.strip().split()

def _strip_quotes(s: str) -> str:
    return s.strip().strip('"').strip("'")


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------

def handle_docker_commands(raw: str, low: str, cwd, p: PFunc) -> bool:
    """
    Return True if matched (so CMC stops parsing further).
    """
    if not (low == "docker" or low.startswith("docker ")):
        return False

    if not _docker_installed():
        p("[red]❌ Docker is not installed or not found in PATH.[/red]")
        p("Fix: install Docker Desktop from https://docs.docker.com/get-docker/")
        return True

    toks = _tokens(raw)
    if len(toks) < 2:
        p("[yellow]Try: docker ps | docker images | docker help[/yellow]")
        p("[yellow]Or: help docker[/yellow]")
        return True

    cmd = toks[1].lower()

    # -------------------------------------------------------------------------
    # docker doctor
    # -------------------------------------------------------------------------
    if cmd == "doctor":
        rc, out = _docker_run(["--version"])
        p(f"docker: {'OK — ' + out if rc == 0 else '❌ ' + out}")

        rc2, out2 = _docker_run(["info", "--format", "Server Version: {{.ServerVersion}}"])
        if rc2 == 0:
            p(f"daemon: running ({out2})")
        else:
            p("[red]daemon: not running — start Docker Desktop[/red]")

        rc3, _ = _docker_run(["compose", "version"])
        p(f"compose: {'available' if rc3 == 0 else 'not available'}")
        return True

    # -------------------------------------------------------------------------
    # docker ps [all]
    # -------------------------------------------------------------------------
    if cmd == "ps":
        show_all = len(toks) >= 3 and toks[2].lower() == "all"
        args = ["ps", "--format", "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"]
        if show_all:
            args.insert(1, "-a")
        rc, out = _docker_run(args)
        p(out)
        return True

    # -------------------------------------------------------------------------
    # docker images
    # -------------------------------------------------------------------------
    if cmd == "images":
        rc, out = _docker_run(["images", "--format", "table {{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.CreatedSince}}"])
        p(out)
        return True

    # -------------------------------------------------------------------------
    # docker start <name>
    # -------------------------------------------------------------------------
    if cmd == "start":
        if len(toks) < 3:
            p("[red]❌ Usage:[/red] docker start <container>")
            return True
        name = _strip_quotes(toks[2])
        rc, out = _docker_run(["start", name])
        p(f"✅ Started: {name}" if rc == 0 else f"[red]❌ Failed:[/red]\n{out}")
        return True

    # -------------------------------------------------------------------------
    # docker stop <name>
    # -------------------------------------------------------------------------
    if cmd == "stop":
        if len(toks) < 3:
            p("[red]❌ Usage:[/red] docker stop <container>")
            return True
        name = _strip_quotes(toks[2])
        rc, out = _docker_run(["stop", name])
        p(f"✅ Stopped: {name}" if rc == 0 else f"[red]❌ Failed:[/red]\n{out}")
        return True

    # -------------------------------------------------------------------------
    # docker restart <name>
    # -------------------------------------------------------------------------
    if cmd == "restart":
        if len(toks) < 3:
            p("[red]❌ Usage:[/red] docker restart <container>")
            return True
        name = _strip_quotes(toks[2])
        rc, out = _docker_run(["restart", name])
        p(f"✅ Restarted: {name}" if rc == 0 else f"[red]❌ Failed:[/red]\n{out}")
        return True

    # -------------------------------------------------------------------------
    # docker remove <name>  — stop + rm in one go
    # -------------------------------------------------------------------------
    if cmd in ("remove", "rm"):
        if len(toks) < 3:
            p("[red]❌ Usage:[/red] docker remove <container>")
            return True
        name = _strip_quotes(toks[2])
        # stop first (ignore error if already stopped), then remove
        _docker_run(["stop", name])
        rc, out = _docker_run(["rm", name])
        p(f"✅ Removed: {name}" if rc == 0 else f"[red]❌ Failed:[/red]\n{out}")
        return True

    # -------------------------------------------------------------------------
    # docker shell <name>  — open interactive shell (bash fallback sh)
    # -------------------------------------------------------------------------
    if cmd == "shell":
        if len(toks) < 3:
            p("[red]❌ Usage:[/red] docker shell <container>")
            return True
        name = _strip_quotes(toks[2])
        # Try bash first, fall back to sh
        rc, _ = _docker_run(["exec", name, "which", "bash"])
        shell = "bash" if rc == 0 else "sh"
        p(f"Opening {shell} in {name}... (exit to return to CMC)")
        try:
            subprocess.run(["docker", "exec", "-it", name, shell])
        except Exception as e:
            p(f"[red]❌ Failed:[/red] {e}")
        return True

    # -------------------------------------------------------------------------
    # docker logs <name> [follow]
    # docker logs follow <name>
    # -------------------------------------------------------------------------
    if cmd == "logs":
        if len(toks) < 3:
            p("[red]❌ Usage:[/red] docker logs <container>  |  docker logs follow <container>")
            return True

        follow = False
        if toks[2].lower() == "follow":
            follow = True
            if len(toks) < 4:
                p("[red]❌ Usage:[/red] docker logs follow <container>")
                return True
            name = _strip_quotes(toks[3])
        else:
            name = _strip_quotes(toks[2])
            if len(toks) >= 4 and toks[3].lower() == "follow":
                follow = True

        if follow:
            p(f"Streaming logs for {name}... (Ctrl+C to stop)")
            _docker_run_live(["logs", "-f", "--tail", "50", name])
        else:
            rc, out = _docker_run(["logs", "--tail", "50", name])
            p(out)
        return True

    # -------------------------------------------------------------------------
    # docker stats [name]
    # -------------------------------------------------------------------------
    if cmd == "stats":
        if len(toks) >= 3:
            name = _strip_quotes(toks[2])
            p(f"Live stats for {name}... (Ctrl+C to stop)")
            _docker_run_live(["stats", name])
        else:
            p("Live stats for all containers... (Ctrl+C to stop)")
            _docker_run_live(["stats"])
        return True

    # -------------------------------------------------------------------------
    # docker inspect <name>
    # -------------------------------------------------------------------------
    if cmd == "inspect":
        if len(toks) < 3:
            p("[red]❌ Usage:[/red] docker inspect <container|image>")
            return True
        name = _strip_quotes(toks[2])
        # Show a friendly subset rather than raw JSON
        fmt = (
            "Name:    {{.Name}}\n"
            "Image:   {{.Config.Image}}\n"
            "Status:  {{.State.Status}}\n"
            "Started: {{.State.StartedAt}}\n"
            "IP:      {{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}\n"
            "Ports:   {{json .NetworkSettings.Ports}}"
        )
        rc, out = _docker_run(["inspect", "--format", fmt, name])
        if rc != 0:
            # Maybe it's an image, try that
            rc2, out2 = _docker_run(["inspect", "--format",
                "ID:      {{.Id}}\nCreated: {{.Created}}\nSize:    {{.Size}}\nTags:    {{json .RepoTags}}",
                name])
            p(out2 if rc2 == 0 else out)
        else:
            p(out)
        return True

    # -------------------------------------------------------------------------
    # docker ip <name>
    # -------------------------------------------------------------------------
    if cmd == "ip":
        if len(toks) < 3:
            p("[red]❌ Usage:[/red] docker ip <container>")
            return True
        name = _strip_quotes(toks[2])
        rc, out = _docker_run(["inspect", "--format",
            "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}", name])
        if rc == 0 and out.strip():
            p(f"{name}: {out.strip()}")
        elif rc == 0:
            p(f"{name}: no IP (container may not be running)")
        else:
            p(f"[red]❌ Not found:[/red] {name}")
        return True

    # -------------------------------------------------------------------------
    # docker build <tag> [path]
    # -------------------------------------------------------------------------
    if cmd == "build":
        if len(toks) < 3:
            p("[red]❌ Usage:[/red] docker build <tag>  |  docker build <tag> <path>")
            return True
        tag = _strip_quotes(toks[2])
        build_path = _strip_quotes(toks[3]) if len(toks) >= 4 else "."
        p(f"Building image [{tag}] from {build_path}...")
        _docker_run_live(["build", "-t", tag, build_path])
        return True

    # -------------------------------------------------------------------------
    # docker pull <image>
    # -------------------------------------------------------------------------
    if cmd == "pull":
        if len(toks) < 3:
            p("[red]❌ Usage:[/red] docker pull <image>")
            return True
        image = _strip_quotes(toks[2])
        p(f"Pulling {image}...")
        _docker_run_live(["pull", image])
        return True

    # -------------------------------------------------------------------------
    # docker push <image>
    # -------------------------------------------------------------------------
    if cmd == "push":
        if len(toks) < 3:
            p("[red]❌ Usage:[/red] docker push <image>")
            return True
        image = _strip_quotes(toks[2])
        p(f"Pushing {image}...")
        _docker_run_live(["push", image])
        return True

    # -------------------------------------------------------------------------
    # docker run <image> [-p host:container] [-e KEY=VAL] [-n name] [-d]
    # -------------------------------------------------------------------------
    if cmd == "run":
        if len(toks) < 3:
            p("[red]❌ Usage:[/red] docker run <image> [-p host:port] [-e KEY=VAL] [-n name] [-d]")
            return True
        image = _strip_quotes(toks[2])
        args = ["run"]
        i = 3
        detached = False
        while i < len(toks):
            t = toks[i].lower()
            if t == "-p" and i + 1 < len(toks):
                args += ["-p", _strip_quotes(toks[i + 1])]
                i += 2
            elif t == "-e" and i + 1 < len(toks):
                args += ["-e", _strip_quotes(toks[i + 1])]
                i += 2
            elif t in ("-n", "--name") and i + 1 < len(toks):
                args += ["--name", _strip_quotes(toks[i + 1])]
                i += 2
            elif t == "-d":
                detached = True
                i += 1
            else:
                i += 1
        if detached:
            args.append("-d")
            args.append(image)
            rc, out = _docker_run(args)
            p(f"✅ Started: {out}" if rc == 0 else f"[red]❌ Failed:[/red]\n{out}")
        else:
            args += ["-it", "--rm", image]
            p(f"Running {image} interactively... (exit to return to CMC)")
            try:
                subprocess.run(["docker"] + args)
            except Exception as e:
                p(f"[red]❌ Failed:[/red] {e}")
        return True

    # -------------------------------------------------------------------------
    # docker volumes
    # -------------------------------------------------------------------------
    if cmd == "volumes":
        rc, out = _docker_run(["volume", "ls", "--format", "table {{.Name}}\t{{.Driver}}"])
        p(out)
        return True

    # -------------------------------------------------------------------------
    # docker volume remove <name>
    # -------------------------------------------------------------------------
    if cmd == "volume":
        if len(toks) >= 4 and toks[2].lower() in ("remove", "rm"):
            name = _strip_quotes(toks[3])
            rc, out = _docker_run(["volume", "rm", name])
            p(f"✅ Volume removed: {name}" if rc == 0 else f"[red]❌ Failed:[/red]\n{out}")
        else:
            p("[yellow]Usage: docker volume remove <name>  |  docker volumes[/yellow]")
        return True

    # -------------------------------------------------------------------------
    # docker networks
    # -------------------------------------------------------------------------
    if cmd == "networks":
        rc, out = _docker_run(["network", "ls", "--format", "table {{.Name}}\t{{.Driver}}\t{{.Scope}}"])
        p(out)
        return True

    # -------------------------------------------------------------------------
    # docker network remove <name>
    # -------------------------------------------------------------------------
    if cmd == "network":
        if len(toks) >= 4 and toks[2].lower() in ("remove", "rm"):
            name = _strip_quotes(toks[3])
            rc, out = _docker_run(["network", "rm", name])
            p(f"✅ Network removed: {name}" if rc == 0 else f"[red]❌ Failed:[/red]\n{out}")
        else:
            p("[yellow]Usage: docker network remove <name>  |  docker networks[/yellow]")
        return True

    # -------------------------------------------------------------------------
    # docker clean        — remove stopped containers + dangling images
    # docker clean all    — full system prune including volumes
    # -------------------------------------------------------------------------
    if cmd == "clean":
        full = len(toks) >= 3 and toks[2].lower() == "all"
        if full:
            p("Removing all stopped containers, unused images, volumes and networks...")
            rc, out = _docker_run(["system", "prune", "-af", "--volumes"])
            p(out)
        else:
            p("Removing stopped containers and dangling images...")
            rc1, out1 = _docker_run(["container", "prune", "-f"])
            rc2, out2 = _docker_run(["image", "prune", "-f"])
            p(out1)
            p(out2)
        return True

    # -------------------------------------------------------------------------
    # docker compose <sub>
    # -------------------------------------------------------------------------
    if cmd == "compose":
        if len(toks) < 3:
            p("[yellow]Usage: docker compose up|down|logs|build|ps|restart[/yellow]")
            return True

        sub = toks[2].lower()

        if sub == "up":
            p("Starting compose services in background...")
            _docker_run_live(["compose", "up", "-d", "--build"], cwd=cwd)

        elif sub == "down":
            p("Stopping and removing compose services...")
            _docker_run_live(["compose", "down"], cwd=cwd)

        elif sub == "logs":
            follow = len(toks) >= 4 and toks[3].lower() == "follow"
            if follow:
                p("Streaming compose logs... (Ctrl+C to stop)")
                _docker_run_live(["compose", "logs", "-f", "--tail", "50"], cwd=cwd)
            else:
                rc, out = _docker_run(["compose", "logs", "--tail", "50"], cwd=cwd)
                p(out)

        elif sub == "build":
            p("Rebuilding compose images...")
            _docker_run_live(["compose", "build", "--no-cache"], cwd=cwd)

        elif sub == "ps":
            rc, out = _docker_run(["compose", "ps"], cwd=cwd)
            p(out)

        elif sub == "restart":
            p("Restarting compose services...")
            _docker_run_live(["compose", "restart"], cwd=cwd)

        else:
            p(f"[yellow]Unknown compose subcommand: {sub}[/yellow]")
            p("[yellow]Usage: docker compose up|down|logs|logs follow|build|ps|restart[/yellow]")

        return True

    # -------------------------------------------------------------------------
    # Pass-through — forward everything else to real docker
    # -------------------------------------------------------------------------
    args = toks[1:]
    rc, out = _docker_run([a.strip('"').strip("'") for a in args], cwd=cwd)
    p(out)
    return True
