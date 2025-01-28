import asyncio
import sys

import rich

from fonk.cli_parser import parse_args
from fonk.config import (
    FLAG_CONCURRENT,
    FLAG_FAIL_QUICK,
    FLAG_HELP,
    FLAG_QUIET,
    FLAG_VERBOSE,
    Config,
    Flag,
    OptionInstance,
    get_config,
)
from fonk.errors import FonkCommandError, FonkConfigurationError
from fonk.render import render_help, render_help_command
from fonk.session import Session


def run(config: Config, flags: set[Flag | OptionInstance], runnables: list[str]) -> None:
    if FLAG_HELP in flags:
        if runnables:
            for runnable in runnables:
                render_help_command(config, runnable)
        else:
            render_help(config)

        return

    if not runnables:
        default = config.default

        if default is None:
            raise FonkCommandError("No runnables provided and no default command set")

        runnables.append(default.command)
        flags.update({flag for flag in config.flags if flag.name in default.flags})

    session = Session(
        config,
        FLAG_QUIET in flags,
        FLAG_VERBOSE in flags,
        FLAG_FAIL_QUICK in flags,
    )

    concurrent_flag: OptionInstance | None = next(
        (flag for flag in flags if flag.name == FLAG_CONCURRENT.name),  # type: ignore
        None,
    )

    if concurrent_flag:
        asyncio.run(
            session.run_runnables_concurrently(
                runnables,
                flags,
                concurrent_flag.value if isinstance(concurrent_flag.value, int) and concurrent_flag.value > 0 else None,
            )
        )
    else:
        session.run_runnables(runnables, flags)

    session.exit()


def app() -> None:
    try:
        config = get_config()
        flags, runnables = parse_args(config, sys.argv[1:])
        run(config, flags, runnables)
    except FonkConfigurationError as e:
        rich.print(f"💥[bold red] Your configuration is invalid: {e}")
        sys.exit(2)
    except FonkCommandError as e:
        rich.print(f"💥[bold red] Error when running your commands: {e}")
        sys.exit(3)
