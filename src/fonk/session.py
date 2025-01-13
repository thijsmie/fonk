from fonk.config import Command, Config, Flag
from fonk.runner import run_command, run_commands_concurrently
import sys
from fonk.render import render_failures, render_header
from rich.console import Console


class SessionError(Exception):
    pass


class Session:
    def __init__(
        self, config: Config, quiet: bool, verbose: bool, fail_quick: bool = False
    ) -> None:
        self.failed: dict[str, int] = {}
        self.config = config
        self.fail_quick = fail_quick
        self.quiet = quiet
        self.verbose = verbose
        self.console = Console()
        render_header(quiet)

    def gather_commands(
        self, runnable: str, flags: set[Flag]
    ) -> list[tuple[Command, set[Flag]]]:
        if alias := self.config.aliases.get(runnable):
            mods = flags.union((m for m in self.config.flags if m.name in alias.flags))
            return sum(
                (self.gather_commands(runnable, mods) for runnable in alias.commands),
                [],
            )
        elif command := self.config.commands.get(runnable):
            return [(command, flags)]

        raise SessionError(f"Unknown command or alias: {runnable}")

    def gather_commands_deduped(
        self, runnables: list[str], flags: set[Flag]
    ) -> list[tuple[Command, set[Flag]]]:
        commands_with_flags = []

        for runnable in runnables:
            for command, mods in self.gather_commands(runnable, flags):
                if (command, mods) not in commands_with_flags:
                    commands_with_flags.append((command, mods))

        return commands_with_flags

    def run_runnables(self, runnables: list[str], flags: set[Flag]) -> None:
        for command, mods in self.gather_commands_deduped(runnables, flags):
            self.run_command(command, mods)

    async def run_runnables_concurrently(
        self, runnables: list[str], flags: set[Flag]
    ) -> None:
        commands_with_flags = self.gather_commands_deduped(runnables, flags)

        failed = await run_commands_concurrently(
            commands_with_flags, self.quiet, self.verbose
        )
        self.failed.update(failed)

    def run_command(self, command: Command, flags: set[Flag]) -> None:
        result = run_command(command, flags, self.quiet, self.verbose)
        if result.returncode != 0:
            if self.fail_quick:
                sys.exit(1)

            self.failed[command.name] = result.returncode

    def exit(self) -> None:
        render_failures(self.failed, self.quiet)
        sys.exit(1 if self.failed else 0)
