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
#   docker wait <name>           poll until container is running/healthy (max 60s)
#   docker errors <name>         filter container logs to error/warning lines only
#   docker env run <image>       run image injecting all vars from .env file
#   docker prune-safe            show then remove stopped containers + dangling images
#   docker backup <name>         save container config to a timestamped zip
#   docker clone <name> <new>    duplicate container (same image + env, no port conflict)
#   docker watch <name>          stream logs with periodic CPU/MEM stats overlay
#   docker size <image>          show layer-by-layer size breakdown
#   docker port-check            check compose file ports vs currently listening ports
#
# Pass-through:
#   Any unrecognised "docker ..." is forwarded to the real docker CLI.

import shutil
import subprocess
import shlex
import time
import datetime
import zipfile
import json
import re
import threading
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
    # docker wait <container>  — poll until running/healthy (max 60s)
    # -------------------------------------------------------------------------
    if cmd == "wait":
        if len(toks) < 3:
            p("[red]❌ Usage:[/red] docker wait <container>")
            return True
        name = _strip_quotes(toks[2])
        p(f"Waiting for [bold]{name}[/bold] to be ready... (Ctrl+C to cancel)")
        try:
            for attempt in range(60):
                rc_s, status = _docker_run(["inspect", "--format", "{{.State.Status}}", name])
                if rc_s != 0:
                    p(f"[red]❌ Container not found:[/red] {name}")
                    return True
                status = status.strip()
                rc_h, health = _docker_run(["inspect", "--format", "{{.State.Health.Status}}", name])
                health = health.strip() if rc_h == 0 else ""
                if status == "running":
                    if health in ("", "healthy"):
                        suffix = f", health: {health}" if health else ""
                        p(f"✅ {name} is ready (status: {status}{suffix})")
                        return True
                    elif health == "unhealthy":
                        p(f"[red]❌ {name} is unhealthy — check with: docker errors {name}[/red]")
                        return True
                    else:
                        p(f"  [{attempt+1}s] running, health: {health}...")
                else:
                    p(f"  [{attempt+1}s] status: {status}...")
                time.sleep(1)
            p(f"[yellow]⚠ Timeout: {name} did not become ready within 60s[/yellow]")
        except KeyboardInterrupt:
            p("[yellow]Cancelled.[/yellow]")
        return True

    # -------------------------------------------------------------------------
    # docker errors <container>  — filter logs to error/exception lines
    # -------------------------------------------------------------------------
    if cmd == "errors":
        if len(toks) < 3:
            p("[red]❌ Usage:[/red] docker errors <container>")
            return True
        name = _strip_quotes(toks[2])
        rc, out = _docker_run(["logs", "--tail", "500", name])
        if rc != 0:
            p(f"[red]❌ Failed:[/red] {out}")
            return True
        keywords = ("error", "fatal", "exception", "traceback", "critical", "failed", "panic", "warn")
        error_lines = [l for l in out.splitlines() if any(kw in l.lower() for kw in keywords)]
        if error_lines:
            p(f"Found [bold]{len(error_lines)}[/bold] notable lines in {name}:")
            for line in error_lines[-50:]:
                p(f"[red]{line}[/red]")
            if len(error_lines) > 50:
                p(f"[yellow]... showing last 50 of {len(error_lines)} lines[/yellow]")
        else:
            p(f"[green]✅ No error/warning lines found in {name}'s logs (last 500 lines).[/green]")
        return True

    # -------------------------------------------------------------------------
    # docker env run <image>  — inject .env file vars and run container
    # -------------------------------------------------------------------------
    if cmd == "env":
        sub = toks[2].lower() if len(toks) >= 3 else ""
        if sub == "run":
            if len(toks) < 4:
                p("[red]❌ Usage:[/red] docker env run <image>")
                return True
            image = _strip_quotes(toks[3])
            env_file = (Path(cwd) if cwd else Path(".")) / ".env"
            env_args: List[str] = []
            if env_file.exists():
                env_lines = env_file.read_text(encoding="utf-8").splitlines()
                count = 0
                for ev in env_lines:
                    ev = ev.strip()
                    if not ev or ev.startswith("#") or "=" not in ev:
                        continue
                    env_args += ["-e", ev]
                    count += 1
                p(f"Injecting [bold]{count}[/bold] var(s) from {env_file.name} into {image}...")
            else:
                p("[yellow]No .env file in current folder — running without extra env vars.[/yellow]")
            run_args = ["run", "--rm", "-it"] + env_args + [image]
            p(f"Running {image}... (exit to return to CMC)")
            try:
                subprocess.run(["docker"] + run_args)
            except Exception as e:
                p(f"[red]❌ Failed:[/red] {e}")
        else:
            p("[yellow]Usage: docker env run <image>[/yellow]")
        return True

    # -------------------------------------------------------------------------
    # docker prune-safe  — preview then remove stopped containers + dangling images
    # -------------------------------------------------------------------------
    if cmd == "prune-safe":
        rc1, stopped = _docker_run(["ps", "-a", "--filter", "status=exited",
                                    "--format", "{{.Names}} ({{.Image}})"])
        rc2, dangling = _docker_run(["images", "-f", "dangling=true",
                                     "--format", "{{.Repository}}:{{.Tag}} ({{.Size}})"])
        has_stopped = rc1 == 0 and stopped.strip()
        has_dangling = rc2 == 0 and dangling.strip()
        if not has_stopped and not has_dangling:
            p("[green]✅ Nothing to remove — system is already tidy.[/green]")
            return True
        if has_stopped:
            p("Stopped containers to remove:")
            for line in stopped.strip().splitlines():
                p(f"  • {line}")
        if has_dangling:
            p("Untagged images to remove:")
            for line in dangling.strip().splitlines():
                p(f"  • {line}")
        p("\nRemoving...")
        if has_stopped:
            _docker_run(["container", "prune", "-f"])
        if has_dangling:
            _docker_run(["image", "prune", "-f"])
        p("[green]✅ Safe prune complete.[/green]")
        p("[yellow](Volumes, networks and in-use images were not touched)[/yellow]")
        return True

    # -------------------------------------------------------------------------
    # docker backup <container>  — save container config to timestamped zip
    # -------------------------------------------------------------------------
    if cmd == "backup":
        if len(toks) < 3:
            p("[red]❌ Usage:[/red] docker backup <container>")
            return True
        name = _strip_quotes(toks[2])
        rc, config_raw = _docker_run(["inspect", name])
        if rc != 0:
            p(f"[red]❌ Container not found:[/red] {name}")
            return True
        ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        zip_name = f"docker_backup_{name}_{ts}.zip"
        zip_path = (Path(cwd) if cwd else Path(".")) / zip_name
        rc2, image_name = _docker_run(["inspect", "--format", "{{.Config.Image}}", name])
        image_name = image_name.strip()
        readme = (
            f"# Docker Container Backup\n"
            f"Container : {name}\n"
            f"Image     : {image_name}\n"
            f"Timestamp : {ts}\n\n"
            f"## Files\n"
            f"- inspect.json  full container configuration (env, ports, mounts, etc.)\n\n"
            f"## Restore example\n"
            f"  docker run --name {name} [add -p/-e from inspect.json] {image_name}\n\n"
            f"## Volume data\n"
            f"Volume DATA is NOT included in this backup.\n"
            f"To backup a named volume manually:\n"
            f"  docker run --rm -v <vol>:/data alpine tar czf - /data > vol_backup.tar.gz\n"
        )
        try:
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("inspect.json", config_raw)
                zf.writestr("README.md", readme)
            p(f"✅ Backup saved: {zip_name}")
            p("[yellow]Note: Only container config included. Volume data requires a separate step.[/yellow]")
        except Exception as e:
            p(f"[red]❌ Backup failed:[/red] {e}")
        return True

    # -------------------------------------------------------------------------
    # docker clone <container> <new-name>  — duplicate container (same image + env)
    # -------------------------------------------------------------------------
    if cmd == "clone":
        if len(toks) < 4:
            p("[red]❌ Usage:[/red] docker clone <container> <new-name>")
            return True
        src = _strip_quotes(toks[2])
        dst = _strip_quotes(toks[3])
        rc, image = _docker_run(["inspect", "--format", "{{.Config.Image}}", src])
        if rc != 0:
            p(f"[red]❌ Container not found:[/red] {src}")
            return True
        image = image.strip()
        rc2, env_json = _docker_run(["inspect", "--format", "{{json .Config.Env}}", src])
        rc3, restart = _docker_run(["inspect", "--format", "{{.HostConfig.RestartPolicy.Name}}", src])
        restart = restart.strip()
        run_args = ["run", "-d", "--name", dst]
        if restart and restart != "no":
            run_args += ["--restart", restart]
        try:
            env_list = json.loads(env_json) if rc2 == 0 else []
            for ev in env_list:
                run_args += ["-e", ev]
        except Exception:
            pass
        run_args.append(image)
        p(f"Cloning [bold]{src}[/bold] → [bold]{dst}[/bold] (image: {image})...")
        rc_r, out_r = _docker_run(run_args)
        if rc_r == 0:
            p(f"✅ Clone created: {dst}")
            p("[yellow]Tip: Port bindings were NOT copied (would conflict). Add -p manually if needed.[/yellow]")
        else:
            p(f"[red]❌ Failed:[/red]\n{out_r}")
        return True

    # -------------------------------------------------------------------------
    # docker watch <container>  — live logs + periodic stats overlay
    # -------------------------------------------------------------------------
    if cmd == "watch":
        if len(toks) < 3:
            p("[red]❌ Usage:[/red] docker watch <container>")
            return True
        name = _strip_quotes(toks[2])
        p(f"Watching [bold]{name}[/bold]... (Ctrl+C to stop)")
        p("[dim]Stats will appear every 5 seconds between log lines.[/dim]")
        stop_flag: List[bool] = [False]

        def _stats_loop():
            while not stop_flag[0]:
                time.sleep(5)
                if stop_flag[0]:
                    break
                rc_st, st_out = _docker_run(
                    ["stats", "--no-stream", "--format",
                     "CPU {{.CPUPerc}}  MEM {{.MemUsage}}  NET {{.NetIO}}", name]
                )
                if rc_st == 0:
                    p(f"[dim]── {st_out.strip()} ──[/dim]")

        t = threading.Thread(target=_stats_loop, daemon=True)
        t.start()
        try:
            _docker_run_live(["logs", "-f", "--tail", "20", name])
        except KeyboardInterrupt:
            pass
        finally:
            stop_flag[0] = True
        return True

    # -------------------------------------------------------------------------
    # docker size <image>  — layer-by-layer size breakdown
    # -------------------------------------------------------------------------
    if cmd == "size":
        if len(toks) < 3:
            p("[red]❌ Usage:[/red] docker size <image>")
            return True
        image = _strip_quotes(toks[2])
        rc, out = _docker_run(["history", "--no-trunc", "--format",
                               "{{.Size}}\t{{.CreatedBy}}", image])
        if rc != 0:
            p(f"[red]❌ Image not found:[/red] {image}")
            return True
        p(f"Layer breakdown for [bold]{image}[/bold]:")
        for line in out.splitlines():
            if "\t" in line:
                sz, layer_cmd = line.split("\t", 1)
                layer_cmd = layer_cmd.strip()
                layer_cmd = re.sub(r"^/bin/sh -c (#\(nop\) )?", "", layer_cmd)
                if len(layer_cmd) > 72:
                    layer_cmd = layer_cmd[:69] + "..."
                p(f"  {sz:>10}  {layer_cmd}")
            elif line.strip():
                p(f"  {line}")
        rc2, total_out = _docker_run(["images", "--format", "{{.Size}}", image])
        if rc2 == 0 and total_out.strip():
            p(f"\n  [bold]Total: {total_out.strip().splitlines()[0]}[/bold]")
        return True

    # -------------------------------------------------------------------------
    # docker port-check  — check compose file ports vs currently listening ports
    # -------------------------------------------------------------------------
    if cmd == "port-check":
        compose_file = None
        for fname in ("docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"):
            cf = (Path(cwd) if cwd else Path(".")) / fname
            if cf.exists():
                compose_file = cf
                break
        if not compose_file:
            p("[red]❌ No docker-compose file found in current folder.[/red]")
            return True
        text = compose_file.read_text(encoding="utf-8")
        port_pairs = re.findall(r'"?\'?(\d{2,5}):(\d{2,5})"?\'?', text)
        if not port_pairs:
            p("[yellow]No port mappings found in compose file.[/yellow]")
            return True
        try:
            result = subprocess.run(
                ["netstat", "-ano"], capture_output=True, text=True, timeout=5
            )
            listening_text = result.stdout
        except Exception:
            listening_text = ""
        p(f"Port check from [bold]{compose_file.name}[/bold]:")
        seen: set = set()
        for host_port, container_port in port_pairs:
            if host_port in seen:
                continue
            seen.add(host_port)
            in_use = (f":{host_port} " in listening_text or
                      f":{host_port}\t" in listening_text)
            status = "[red]IN USE ⚠[/red]" if in_use else "[green]free ✅[/green]"
            p(f"  {host_port:>5} → {container_port:<5}  {status}")
        return True

    # -------------------------------------------------------------------------
    # Pass-through — forward everything else to real docker
    # -------------------------------------------------------------------------
    args = toks[1:]
    rc, out = _docker_run([a.strip('"').strip("'") for a in args], cwd=cwd)
    p(out)
    return True
