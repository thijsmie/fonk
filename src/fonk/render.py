from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from fonk.config import Config


def render_help(config: Config) -> None:
    console = Console()

    commands = Table(
        "[bold green]Commands:",
        "",
        box=None,
        pad_edge=False,
        header_style="",
    )

    for command in config.commands.values():
        commands.add_row(
            f" [bold]•[/] [cyan]{command.name}[/]",
            "[italic]" + (command.description or ""),
        )

    flags = Table(
        "[bold green]Flags:",
        "",
        box=None,
        pad_edge=False,
        header_style="",
    )

    for flag in config.flags:
        flags.add_row(
            f" [bold]•[/] [yellow]--{flag.name}"
            + (f"/-{flag.shorthand}" if flag.shorthand else ""),
            "[italic]" + (flag.description or ""),
        )

    aliases = Table(
        "[bold green]Aliases:",
        "",
        "",
        "",
        box=None,
        pad_edge=False,
        header_style="",
    )

    for alias, conf in config.aliases.items():
        aliases.add_row(
            f" [bold]•[/] [magenta]{alias}[/]",
            "[yellow]" + ", ".join(f"--{f}" for f in conf.flags),
            "[cyan]" + ", ".join(conf.commands),
            "[italic]" + (conf.description or ""),
        )

    help = Group(
        Markdown("*A `pyproject.toml` driven task runner*"),
        "",
        "[bold green]Usage:[/][cyan] fonk \\[commands] \\[aliases] \\[flags][/]",
        "",
        commands,
        "",
        flags,
        "",
        aliases,
    )

    if config.default is not None:
        color = "magenta" if config.default.command in config.aliases else "cyan"

        default_help = Table(
            "[bold green]Default:",
            "",
            "",
            box=None,
            pad_edge=False,
            header_style="",
        )
        default_help.add_row(
            f" [bold]•[/] [{color}]{config.default.command}[/]",
            "[yellow]" + ", ".join(f"--{f}" for f in config.default.flags),
            "[italic]" + (config.default.description or ""),
        )

        help.renderables.extend(
            [
                "",
                default_help,
            ]
        )

    console.print(
        Panel(
            help,
            title=(
                f"[bold red]🔥 Fonk {config.project_name} 🔥"
                if config.project_name
                else "[bold red]🔥 Fonk 🔥"
            ),
            expand=True,
        )
    )

    return


def render_header(quiet: bool) -> None:
    if quiet:
        return
    console = Console()
    console.rule(title="[bold red]🔥 Fonk 🔥", style="")
    return


def render_failures(failed: dict[str, int], quiet: bool) -> None:
    console = Console()

    if not failed:
        if not quiet:
            console.rule(title="[bold green]✨ Fonky Fresh! ✨[/]", style="green")
        return

    failures = [f"{fail} has returncode {status}" for fail, status in failed.items()]

    console.print(
        Panel(
            "\n".join(failures),
            title="[bold red]💥 Fonked Out! 💥[/]",
            expand=True,
            border_style="red",
            padding=(0, 6),
        )
    )

    return


def render_help_command(config: Config, cmd: str) -> None:
    console = Console()
    help_content: list[str | Table] = []
    title = ""

    if cmd in config.commands:
        title = f"[bold green]Command: [cyan]{cmd}"
        command = config.commands[cmd]
        help_content.extend(
            (
                "[italic]" + (command.description or ""),
                "",
                "[bold green]Usage: [cyan]" + command.name + " \\[flags]",
                "",
            )
        )

        flags = Table(
            "[bold green]Flags",
            "",
            box=None,
            pad_edge=False,
            header_style="",
        )

        for flag in config.flags:
            if not flag.is_builtin and not any(
                m.on == flag.name for m in command.flags
            ):
                continue

            flags.add_row(
                f" [bold]•[/] [yellow]--{flag.name}"
                + (f"/-{flag.shorthand}" if flag.shorthand else ""),
                "[italic]" + (flag.description or ""),
            )

        help_content.append(flags)

    elif cmd in config.aliases:
        alias = config.aliases[cmd]
        title = f"[bold green]Alias: [magenta]{cmd}"
        help_content.extend(
            (
                "[italic]" + (alias.description or ""),
                "",
                "[bold green]Commands:",
            )
        )
        for subcommand in alias.commands:
            applicable_mods = []
            for modd in config.commands[subcommand].flags:
                if modd.on in alias.flags:
                    applicable_mods.append(f"--{modd.on}")
            help_content.append(
                f"  [cyan]{subcommand}[/] [yellow]" + " ".join(applicable_mods)
            )
    else:
        title = f"[bold red]Unknown {cmd}"
        help_content.append(f"[bold red]Unknown command or alias: {cmd}")

    console.print(Panel(Group(*help_content), title=title, expand=True))

    return
