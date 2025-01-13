from pathlib import Path


def get_pyproject(cwd: Path | None = None) -> Path:
    cwd = cwd or Path.cwd()

    while not (cwd / "pyproject.toml").exists():
        cwd = cwd.parent

        if cwd.parent == cwd:
            raise FileNotFoundError("pyproject.toml not found")

    return cwd / "pyproject.toml"
