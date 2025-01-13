import asyncio
from fonk.config import (
    get_config,
    ConfigurationError,
    Flag,
    FLAG_CONCURRENT,
    FLAG_HELP,
    FLAG_FAIL_QUICK,
    FLAG_QUIET,
    FLAG_VERBOSE,
)
import sys
import rich
from fonk.render import render_help, render_help_command
from fonk.session import Session, SessionError


def app() -> None:
    try:
        config = get_config()
    except ConfigurationError as e:
        rich.print(f"💥[bold red] {e}")
        sys.exit(1)

    flags: set[Flag] = set()
    runnables: list[str] = []

    for arg in sys.argv[1:]:
        if arg.startswith("-"):
            if arg.startswith("--"):
                flag_name = arg[2:]
                for flag in config.flags:
                    if flag_name == flag.name:
                        flags.add(flag)
                        break
                else:
                    rich.print(f"💥[bold red] Unknown flag: {flag_name}")
                    sys.exit(1)
            else:
                shorthands = arg[1:]

                for flag in config.flags:
                    if flag.shorthand and flag.shorthand in shorthands:
                        flags.add(flag)
                        shorthands = shorthands.replace(flag.shorthand, "")

                if shorthands:
                    rich.print(f"💥[bold red] Unknown flag shorthand: {shorthands}")
                    sys.exit(1)

            for flag in config.flags:
                if arg == f"--{flag.name}" or arg == f"-{flag.shorthand}":
                    flags.add(flag)
                    break
        else:
            runnables.append(arg)

    if FLAG_HELP in flags:
        if runnables:
            for runnable in runnables:
                render_help_command(config, runnable)
        else:
            render_help(config)

        sys.exit(0)

    if not runnables:
        default = config.default

        if default is None:
            rich.print("💥[bold red] No runnables provided and no default set")
            sys.exit(1)

        runnables.append(default.command)
        flags.update({flag for flag in config.flags if flag.name in default.flags})

    session = Session(
        config,
        FLAG_QUIET in flags,
        FLAG_VERBOSE in flags,
        FLAG_FAIL_QUICK in flags,
    )

    try:
        if FLAG_CONCURRENT in flags:
            asyncio.run(session.run_runnables_concurrently(runnables, flags))
        else:
            session.run_runnables(runnables, flags)
    except SessionError as e:
        rich.print(f"💥[bold red] {e}")
        sys.exit(1)

    session.exit()
