import json
import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
APPLICATIONS = ROOT / "applications"
USER_AGENT = "job-hunter/1.0 (personal job alert script; low volume)"


def load_yaml(name: str) -> dict:
    return yaml.safe_load((ROOT / name).read_text(encoding="utf-8"))


def load_json(path: Path, default):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def find_todos(obj, path: str = "") -> list[str]:
    """Return the dotted paths of profile values that still contain TODO."""
    if isinstance(obj, dict):
        return [p for k, v in obj.items() for p in find_todos(v, f"{path}.{k}" if path else str(k))]
    if isinstance(obj, list):
        return [p for i, v in enumerate(obj) for p in find_todos(v, f"{path}[{i}]")]
    if isinstance(obj, str) and "TODO" in obj:
        return [path]
    return []


def load_env() -> None:
    """For running on your own computer: read KEY=value lines from .env."""
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            key, sep, value = line.partition("=")
            if sep and not key.strip().startswith("#"):
                os.environ.setdefault(key.strip(), value.strip())
