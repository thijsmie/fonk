import asyncio
import os
import sys
from contextlib import nullcontext
from subprocess import CompletedProcess, run

import rich

from fonk.config import ApplyFlag, Command, Flag, OptionInstance


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
        case "poetry":
            return ["poetry", "run"]


def _apply_add_flags(flag: Flag, apply: ApplyFlag, args: list[str]) -> None:
    if not apply.add:
        return

    to_add = apply.add if isinstance(apply.add, list) else [apply.add]

    if isinstance(flag, OptionInstance):
        to_add = [arg.replace("{arg}", str(flag.value)) for arg in to_add]

    args.extend(to_add)


def _command_mods_args(command: Command, flags: set[Flag]) -> tuple[list[str], list[str]]:
    applied_mods: set[str] = set()
    arguments = command.arguments.copy()

    for flag in flags:
        for apply_flag in command.flags:
            if apply_flag.on == flag.name:
                if isinstance(apply_flag.remove, list):
                    arguments = [arg for arg in arguments if arg not in apply_flag.remove]
                elif isinstance(apply_flag.remove, str):
                    arguments.remove(apply_flag.remove)

                _apply_add_flags(flag, apply_flag, arguments)
                applied_mods.add(flag.name)

    return sorted(applied_mods), _command_runner_prefix(command) + arguments


def run_command(command: Command, flags: set[Flag], quiet: bool, verbose: bool) -> CompletedProcess[bytes]:
    applied_mods, arguments = _command_mods_args(command, flags)

    if not quiet:
        rich.print(
            f"[bold red]🔥 Running {command.name}" + (f"([green]{', '.join(applied_mods)}[/])" if applied_mods else "")
        )

    if verbose:
        rich.print(f"[bold]🔹[/] {' '.join(arguments)}")

    result = run(arguments, check=False)
    print()
    return result


def _process_command(
    stdout: bytes,
    stderr: bytes,
    retcode: int,
    name: str,
    arguments: list[str],
    quiet: bool,
    verbose: bool,
    mods: list[str],
) -> None:
    if not quiet or retcode != 0:
        if mods:
            rich.print(f"[bold red]🔥 Ran {name} ([green]{', '.join(mods)}[/])")
        else:
            rich.print(f"[bold red]🔥 Ran {name}")

    if verbose:
        rich.print(f"[bold]🔹[/] {' '.join(arguments)}")

    if (not quiet or retcode != 0) and stdout:
        print(stdout.decode().rstrip())
    if (not quiet or retcode != 0) and stderr:
        print(stderr.decode().rstrip())
    if (not quiet or retcode != 0) and (stdout or stderr):
        print()


async def _async_subprocess_limited(
    name: str,
    arguments: list[str],
    env: dict[str, str],
    quiet: bool,
    verbose: bool,
    mods: list[str],
    lock: asyncio.Lock,
    semaphore: asyncio.Semaphore | None,
) -> tuple[str, int]:
    async with semaphore or nullcontext():
        process = await asyncio.create_subprocess_exec(
            *arguments,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        stdout, stderr = await process.communicate()

    async with lock:
        retcode: int = process.returncode  # type: ignore
        _process_command(stdout, stderr, retcode, name, arguments, quiet, verbose, mods)

    return name, retcode


async def run_commands_concurrently(
    commands_with_flags: list[tuple[Command, set[Flag]]],
    quiet: bool,
    verbose: bool,
    limit_concurrency: int | None = None,
) -> dict[str, int]:
    tasks: list[asyncio.Task[tuple[str, int]]] = []
    env = os.environ.copy()
    env["FORCE_COLOR"] = "1"

    semaphore = asyncio.Semaphore(limit_concurrency) if limit_concurrency else None
    print_lock = asyncio.Lock()

    for command, flags in commands_with_flags:
        mods, args = _command_mods_args(command, flags)
        tasks.append(
            asyncio.create_task(
                coro=_async_subprocess_limited(
                    name=command.name,
                    arguments=args,
                    env=env,
                    quiet=quiet,
                    verbose=verbose,
                    mods=mods,
                    lock=print_lock,
                    semaphore=semaphore,
                )
            )
        )

    processes = await asyncio.gather(*tasks)
    return {name: retcode for name, retcode in processes if retcode != 0}
