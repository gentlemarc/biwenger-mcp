import importlib.util
import tomllib
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "register_codex", Path(__file__).resolve().parents[1] / "scripts" / "register_codex.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_registration_preserves_other_config_and_is_idempotent(tmp_path):
    root = tmp_path / "project"
    executable = root / ".venv" / "bin" / "biwenger"
    executable.parent.mkdir(parents=True)
    executable.touch()
    config = tmp_path / "config.toml"
    original = '# preserve comments\nmodel = "example"\n[mcp_servers.other]\ncommand = "other"\n[mcp_servers.other.env]\nPRIVATE_VALUE = "do-not-echo"\n'
    config.write_text(original)
    assert module.register(config, root) == "registered"
    result = config.read_text()
    assert result.startswith(original)
    parsed = tomllib.loads(result)
    assert parsed["mcp_servers"]["other"]["env"]["PRIVATE_VALUE"] == "do-not-echo"
    assert parsed["mcp_servers"]["biwenger"]["startup_timeout_sec"] == 60
    assert module.register(config, root) == "already_registered"
    assert config.read_text() == result


def test_registration_refuses_to_overwrite_an_existing_server(tmp_path):
    executable = tmp_path / ".venv" / "bin" / "biwenger"
    executable.parent.mkdir(parents=True)
    executable.touch()
    config = tmp_path / "config.toml"
    original = '[mcp_servers.biwenger]\ncommand = "someone-else"\n'
    config.write_text(original)
    with pytest.raises(RuntimeError):
        module.register(config, tmp_path)
    assert config.read_text() == original
