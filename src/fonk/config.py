from tomli import load
from pathlib import Path
from typing import Literal, Self
from dataclasses import dataclass
from fonk.locator import get_pyproject


class ConfigurationError(Exception):
    pass


@dataclass(kw_only=True)
class ApplyFlag:
    on: str
    add: str | list[str] | None = None
    remove: str | list[str] | None = None

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        return cls(
            on=data["on"],
            add=data.get("add"),
            remove=data.get("remove"),
        )


@dataclass(kw_only=True)
class Command:
    name: str
    description: str | None = None
    type: Literal["shell", "python", "uv", "uvx"]
    arguments: list[str]
    flags: list[ApplyFlag]

    @classmethod
    def from_dict(cls, name: str, data: dict) -> Self:
        return cls(
            name=name,
            description=data.get("description"),
            type=data["type"],
            arguments=data.get("arguments", []),
            flags=[ApplyFlag.from_dict(flag) for flag in data.get("flags", [])],
        )


@dataclass(kw_only=True)
class Alias:
    commands: list[str]
    flags: list[str]
    description: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        return cls(
            commands=data.get("commands", []),
            flags=data.get("flags", []),
            description=data.get("description"),
        )


@dataclass(kw_only=True)
class Flag:
    name: str
    shorthand: str | None = None
    description: str | None = None
    is_builtin: bool = False

    def __post_init__(self):
        if self.shorthand and len(self.shorthand) > 1:
            raise ConfigurationError("Shorthand must be a single character")

    def __hash__(self):
        return hash(self.name)

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        return cls(
            name=data["name"],
            shorthand=data.get("shorthand"),
            description=data.get("description"),
        )


FLAG_QUIET = Flag(
    name="quiet", shorthand="q", description="Suppress output", is_builtin=True
)
FLAG_VERBOSE = Flag(
    name="verbose",
    shorthand="v",
    description="Print command before running",
    is_builtin=True,
)
FLAG_FAIL_QUICK = Flag(
    name="fail-quick",
    shorthand="x",
    description="Exit on first failure",
    is_builtin=True,
)
FLAG_HELP = Flag(name="help", shorthand="h", description="Show help", is_builtin=True)
FLAG_CONCURRENT = Flag(
    name="concurrent",
    shorthand="j",
    description="Run commands concurrently",
    is_builtin=True,
)


@dataclass(kw_only=True)
class Default:
    command: str
    flags: list[str]
    description: str | None

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        return cls(
            command=data["command"],
            flags=data.get("flags", []),
            description=data.get("description"),
        )


@dataclass(kw_only=True)
class Config:
    project_name: str | None
    default: Default | None = None
    commands: dict[str, Command]
    aliases: dict[str, Alias]
    flags: list[Flag]

    def __post_init__(self):
        if (
            self.default
            and self.default.command not in self.commands
            and self.default.command not in self.aliases
        ):
            raise ConfigurationError("Default command not found in commands")

        flags_in_use = set()
        shorthands_in_use = set()

        for flag in self.flags:
            if flag.name in flags_in_use:
                raise ConfigurationError(f"Duplicate flag flag: {flag.name}")

            if flag.shorthand and flag.shorthand in shorthands_in_use:
                raise ConfigurationError(f"Duplicate flag shorthand: {flag.shorthand}")

            flags_in_use.add(flag.name)
            if flag.shorthand:
                shorthands_in_use.add(flag.shorthand)

        for command in self.commands.values():
            for flag in command.flags:
                if flag.on not in flags_in_use:
                    raise ConfigurationError(
                        f"Unknown flag flag {flag.on} used in {command.name}"
                    )

    @classmethod
    def from_dict(cls, project_name: str | None, data: dict) -> Self:
        return cls(
            project_name=project_name,
            default=Default.from_dict(data["default"]) if "default" in data else None,
            commands={
                name: Command.from_dict(name, command)
                for name, command in data.get("command", {}).items()
            },
            aliases={
                name: Alias.from_dict(alias)
                for name, alias in data.get("alias", {}).items()
            },
            flags=[Flag.from_dict(flag) for flag in data.get("flags", [])]
            + [
                FLAG_QUIET,
                FLAG_VERBOSE,
                FLAG_FAIL_QUICK,
                FLAG_HELP,
                FLAG_CONCURRENT,
            ],
        )


def get_config(cwd: Path | None = None) -> Config:
    with get_pyproject(cwd).open("rb") as file:
        pyproject = load(file)

    project_name = pyproject.get("project", {}).get("name")
    this_tool_config = pyproject.get("tool", {}).get("fonk", {})

    return Config.from_dict(project_name, this_tool_config)
