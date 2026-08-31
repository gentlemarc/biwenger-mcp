"""Añade únicamente mcp_servers.biwenger, conservando las otras opciones de Codex."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import sys
import tomllib
from pathlib import Path


def register(config_path: Path, root: Path) -> str:
    if config_path.is_symlink():
        raise RuntimeError("No se modifica una configuración enlazada.")
    executable = root / ".venv" / "bin" / "biwenger"
    if not executable.is_file():
        raise RuntimeError("Instala primero las dependencias con uv sync --frozen.")
    expected = {
        "command": str(executable),
        "args": ["--config", str(root / ".local" / "session.json"), "serve"],
        "startup_timeout_sec": 60,
        "tool_timeout_sec": 60,
    }
    # r+ deliberately requires an existing file and writes only to the approved file.
    with config_path.open("r+") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        original = handle.read()
        data = tomllib.loads(original)
        existing = data.get("mcp_servers", {}).get("biwenger")
        if existing == expected:
            return "already_registered"
        if existing is not None:
            raise RuntimeError("Ya existe otra entrada biwenger; no se ha sobrescrito.")
        block = "\n\n[mcp_servers.biwenger]\n"
        for key, value in expected.items():
            block += key + " = " + json.dumps(value, ensure_ascii=False) + "\n"
        updated = tomllib.loads(original + block)
        del updated["mcp_servers"]["biwenger"]
        if "mcp_servers" not in data:
            del updated["mcp_servers"]
        if updated != data:
            raise RuntimeError("El cambio afectaría a otras opciones; no se ha escrito nada.")
        handle.seek(0, os.SEEK_END)
        handle.write(block)
        handle.flush()
        os.fsync(handle.fileno())
    return "registered"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "config.toml",
    )
    args = parser.parse_args()
    try:
        print(register(args.config, Path(__file__).resolve().parents[1]))
    except (OSError, ValueError, RuntimeError):
        print(
            "No se ha podido registrar el MCP. Revisa permisos o una entrada biwenger ya existente; no se muestran valores de la configuración.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
