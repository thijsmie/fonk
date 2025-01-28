from argparse import ArgumentParser
from pathlib import Path

from fonk.config import Config, Flag, Option, OptionInstance

_ARGPARSE_TYPES = {
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "file": Path,
    "directory": Path,
}


def _parser_from_config(config: Config) -> ArgumentParser:
    parser = ArgumentParser(add_help=False, allow_abbrev=False)

    for flag in config.flags:
        name = flag.name
        shorthand = flag.shorthand
        args = [f"--{name}"]

        if shorthand:
            args.append(f"-{shorthand}")

        if isinstance(flag, Option):
            if flag.default is not None:
                parser.add_argument(
                    *args,
                    action="store",
                    nargs="?",
                    default=None,
                    const=flag.default,
                    type=_ARGPARSE_TYPES[flag.type],
                )
            else:
                parser.add_argument(
                    *args,
                    action="store",
                    type=_ARGPARSE_TYPES[flag.type],
                )
        elif isinstance(flag, Flag):
            parser.add_argument(
                *args,
                action="store_true",
            )

    parser.add_argument("runnables", nargs="*")

    return parser


def parse_args(config: Config, args: list[str]) -> tuple[set[Flag | OptionInstance], list[str]]:
    parser = _parser_from_config(config)
    parsed = parser.parse_args(args)

    flags: set[Flag | OptionInstance] = set()
    runnables: list[str] = parsed.runnables

    for flag in config.flags:
        if isinstance(flag, Option):
            if getattr(parsed, flag.name.replace("-", "_"), None) is not None:
                flags.add(
                    OptionInstance(
                        name=flag.name,
                        shorthand=flag.shorthand,
                        description=flag.description,
                        is_builtin=flag.is_builtin,
                        type=flag.type,
                        default=flag.default,
                        value=getattr(parsed, flag.name.replace("-", "_")),
                    )
                )
        elif isinstance(flag, Flag) and getattr(parsed, flag.name.replace("-", "_"), False):
            flags.add(flag)

    return flags, runnables
