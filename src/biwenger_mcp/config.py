"""Configuración privada fuera de argumentos MCP y excluida de Git."""

from __future__ import annotations

import json
import os
import stat
import tempfile
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError, field_validator

from .errors import BiwengerError


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_config_path() -> Path:
    return Path(os.environ.get("BIWENGER_CONFIG", project_root() / ".local" / "session.json"))


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    token: SecretStr | None = Field(default=None, exclude=True)
    league_id: int | None = Field(default=None, gt=0)
    user_id: int | None = Field(default=None, gt=0)
    client_version: str | None = None
    competition: Literal["la-liga"] = "la-liga"
    score_id: Literal[2] = 2
    expected_mode: Literal["classic"] = "classic"
    # Operator attestation used only when the API omits these settings.
    league_settings_confirmed: bool = False
    timeout_seconds: float = Field(default=15, ge=1, le=60)
    cache_seconds: int = Field(default=60, ge=0, le=300)

    @field_validator("token")
    @classmethod
    def token_valid(cls, value: SecretStr | None) -> SecretStr | None:
        if value is None:
            return None
        raw = value.get_secret_value().strip()
        if raw.lower().startswith("bearer "):
            raw = raw[7:].strip()
        if not raw or len(raw) > 16384 or any(c.isspace() for c in raw):
            raise ValueError("Token no válido")
        return SecretStr(raw)

    @field_validator("client_version")
    @classmethod
    def version_valid(cls, value: str | None) -> str | None:
        if value is not None and (len(value) > 100 or any(c in value for c in "\r\n")):
            raise ValueError("Versión no válida")
        return value

    @property
    def authenticated(self) -> bool:
        return bool(self.token and self.league_id and self.user_id)


def load_settings(path: Path | None = None) -> Settings:
    path = path or default_config_path()
    if path.is_symlink() or path.parent.is_symlink():
        raise BiwengerError("unsafe_config", "No se permiten enlaces en la configuración.")
    if not path.exists():
        return Settings()
    try:
        if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode):
            raise BiwengerError("unsafe_config", "La configuración debe ser un archivo regular.")
        if path.stat().st_mode & 0o077:
            raise BiwengerError("unsafe_config", "La configuración necesita permisos 600.")
        if path.stat().st_size > 32768:
            raise ValueError()
        return Settings.model_validate_json(path.read_text())
    except (ValueError, OSError, ValidationError):
        raise BiwengerError(
            "invalid_config", "Configuración inválida; ejecuta biwenger configure."
        ) from None


def save_settings(settings: Settings, path: Path | None = None) -> None:
    path = path or default_config_path()
    if path.is_symlink() or path.parent.is_symlink():
        raise BiwengerError("unsafe_config", "No se permiten enlaces en la configuración.")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    data = settings.model_dump()
    data["token"] = settings.token.get_secret_value() if settings.token else None
    descriptor, temporary = tempfile.mkstemp(prefix=".session-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w") as output:
            os.fchmod(output.fileno(), 0o600)
            output.write(json.dumps(data, indent=2))
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
