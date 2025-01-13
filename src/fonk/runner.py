from fonk.config import Command, Flag
from subprocess import run, CompletedProcess
import os
import rich
import sys
import asyncio


def _command_runner_prefix(command: Command) -> list[str]:
    match command.type:
        case "shell":
            return []
        case "python":
            return [sys.executable]
        case "uv":
            return ["uv", "run"]
        case "uvx":
            return ["uvx"]


def _command_mods_args(
    command: Command, flags: set[Flag]
) -> tuple[list[str], list[str]]:
    applied_mods: set[str] = set()
    arguments = command.arguments.copy()

    for flag in flags:
        for apply_flag in command.flags:
            if apply_flag.on == flag.name:
                if isinstance(apply_flag.add, list):
                    arguments.extend(apply_flag.add)
                elif isinstance(apply_flag.add, str):
                    arguments.append(apply_flag.add)
                if isinstance(apply_flag.remove, list):
                    arguments = [
                        arg for arg in arguments if arg not in apply_flag.remove
                    ]
                elif isinstance(apply_flag.remove, str):
                    arguments.remove(apply_flag.remove)
                applied_mods.add(flag.name)

    return sorted(applied_mods), _command_runner_prefix(command) + arguments


def run_command(
    command: Command, flags: set[Flag], quiet: bool, verbose: bool
) -> CompletedProcess[bytes]:
    applied_mods, arguments = _command_mods_args(command, flags)

    if not quiet:
        rich.print(
            f"[bold red]🔥 Running {command.name}"
            + (f"([green]{', '.join(applied_mods)}[/])" if applied_mods else "")
        )

    if verbose:
        rich.print(f"[bold]⋙[/] {' '.join(arguments)}")

    return run(arguments)


async def run_commands_concurrently(
    commands_with_flags: list[tuple[Command, set[Flag]]],
    quiet: bool,
    verbose: bool,
) -> dict[str, int]:
    failures: dict[str, int] = {}
    names_mods_args: list[tuple[str, list[str], list[str]]] = []
    tasks: list[asyncio.Task[asyncio.subprocess.Process]] = []
    env = os.environ.copy()
    env["FORCE_COLOR"] = "1"

    for command, flags in commands_with_flags:
        mods, args = _command_mods_args(command, flags)
        names_mods_args.append((command.name, mods, args))
        tasks.append(
            asyncio.create_task(
                coro=asyncio.create_subprocess_exec(
                    *args,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=env,
                )
            )
        )

    processes = await asyncio.gather(*tasks)

    for (name, mods, arguments), process in zip(names_mods_args, processes):
        stdout, stderr = await process.communicate()
        if not quiet:
            if mods:
                rich.print(f"[bold red]🔥 Ran {name} ([green]{', '.join(mods)}[/])")
            else:
                rich.print(f"[bold red]🔥 Ran {name}")

        if verbose:
            rich.print(f"[bold]>>[/] {' '.join(arguments)}")

        retcode = process.returncode
        if retcode and retcode != 0:
            failures[name] = retcode

        if (not quiet or retcode != 0) and stdout:
            print(stdout.decode().rstrip())
        if (not quiet or retcode != 0) and stderr:
            print(stderr.decode().rstrip())

    return failures
