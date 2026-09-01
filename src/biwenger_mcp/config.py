"""Configuración local con compatibilidad explícita para sesiones antiguas."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import tempfile
from pathlib import Path
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError, field_validator

from .errors import BiwengerError

SUPPORTED_SCORES = {
    1: "Diario AS",
    2: "SofaScore",
    3: "Estadísticas",
    5: "Media AS y SofaScore",
    6: "Biwenger Social",
    7: "Feeberse Score",
    8: "Media AS y Feeberse",
}
KEYCHAIN_SERVICE = "com.gentlemarc.biwenger-mcp"
KEYCHAIN_ACCOUNT = "default"


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_config_path() -> Path:
    """Ruta nueva sin secretos. BIWENGER_CONFIG conserva el modo de archivo explícito."""
    override = os.environ.get("BIWENGER_CONFIG")
    if override:
        return Path(override).expanduser()
    return Path.home() / "Library" / "Application Support" / "Biwenger MCP" / "settings.json"


def legacy_config_path() -> Path:
    return project_root() / ".local" / "session.json"


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    token: SecretStr | None = Field(default=None, exclude=True)
    league_id: int | None = Field(default=None, gt=0)
    user_id: int | None = Field(default=None, gt=0)
    client_version: str | None = None
    competition: Literal["la-liga"] = "la-liga"
    score_id: Literal[1, 2, 3, 5, 6, 7, 8] = 2
    expected_mode: Literal["classic"] = "classic"
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

    @property
    def score_name(self) -> str:
        return SUPPORTED_SCORES[self.score_id]


class SecretBackend(Protocol):
    def get(self, service: str, account: str) -> str | None: ...
    def set(self, service: str, account: str, value: str) -> None: ...
    def delete(self, service: str, account: str) -> None: ...


class KeyringBackend:
    """Adaptador pequeño para poder sustituir el llavero en pruebas."""

    @staticmethod
    def _keyring():
        try:
            import keyring
            from keyring.errors import KeyringError
        except ImportError:
            raise BiwengerError(
                "secure_storage_unavailable", "El llavero seguro no está disponible."
            ) from None
        return keyring, KeyringError

    def get(self, service: str, account: str) -> str | None:
        keyring, error = self._keyring()
        try:
            return keyring.get_password(service, account)
        except error:
            return SecurityCLIBackend().get(service, account)

    def set(self, service: str, account: str, value: str) -> None:
        keyring, error = self._keyring()
        try:
            keyring.set_password(service, account, value)
        except error:
            SecurityCLIBackend().set(service, account, value)

    def delete(self, service: str, account: str) -> None:
        keyring, error = self._keyring()
        try:
            keyring.delete_password(service, account)
        except keyring.errors.PasswordDeleteError:
            SecurityCLIBackend().delete(service, account)
        except error:
            SecurityCLIBackend().delete(service, account)


class SecurityCLIBackend:
    """Fallback al binario firmado de macOS; el secreto viaja por stdin, no por argv."""

    executable = "/usr/bin/security"

    def _run(self, arguments: list[str], *, input_value: str | None = None):
        try:
            return subprocess.run(
                [self.executable, *arguments],
                input=input_value,
                text=True,
                capture_output=True,
                timeout=45,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            raise BiwengerError(
                "secure_storage_unavailable", "El llavero de macOS no está disponible."
            ) from None

    def get(self, service: str, account: str) -> str | None:
        result = self._run(
            ["find-generic-password", "-a", account, "-s", service, "-w"]
        )
        if result.returncode == 44:
            return None
        if result.returncode != 0:
            raise BiwengerError(
                "secure_storage_unavailable", "No se pudo leer el llavero de macOS."
            )
        value = result.stdout.rstrip("\r\n")
        if not value:
            raise BiwengerError(
                "secure_storage_unavailable", "El llavero devolvió una sesión vacía."
            )
        return value

    def set(self, service: str, account: str, value: str) -> None:
        result = self._run(
            ["add-generic-password", "-a", account, "-s", service, "-U", "-w"],
            input_value=value + "\n" + value + "\n",
        )
        if result.returncode != 0:
            raise BiwengerError(
                "secure_storage_unavailable", "No se pudo guardar la sesión en el llavero."
            )

    def delete(self, service: str, account: str) -> None:
        result = self._run(["delete-generic-password", "-a", account, "-s", service])
        if result.returncode not in (0, 44):
            raise BiwengerError(
                "secure_storage_unavailable", "No se pudo eliminar la sesión del llavero."
            )


def _check_path(path: Path) -> None:
    if path.is_symlink() or path.parent.is_symlink():
        raise BiwengerError("unsafe_config", "No se permiten enlaces en la configuración.")


def _read_nonsecret(path: Path) -> dict:
    _check_path(path)
    if not path.exists():
        return {}
    try:
        info = path.stat()
        if not stat.S_ISREG(info.st_mode):
            raise BiwengerError("unsafe_config", "La configuración debe ser un archivo regular.")
        if info.st_mode & 0o077:
            raise BiwengerError("unsafe_config", "La configuración necesita permisos 600.")
        if info.st_size > 32768:
            raise ValueError()
        data = json.loads(path.read_text())
        if not isinstance(data, dict):
            raise ValueError()
        return data
    except BiwengerError:
        raise
    except (ValueError, OSError):
        raise BiwengerError("invalid_config", "La configuración local no es válida.") from None


def _atomic_write(path: Path, data: dict) -> None:
    _check_path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        path.parent.chmod(0o700)
    except OSError:
        pass
    descriptor, temporary = tempfile.mkstemp(prefix=".settings-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w") as output:
            os.fchmod(output.fileno(), 0o600)
            output.write(json.dumps(data, indent=2, ensure_ascii=False))
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class SecureSettingsStore:
    def __init__(self, path: Path | None = None, backend: SecretBackend | None = None):
        self.path = path or default_config_path()
        self.backend = backend or KeyringBackend()

    def load(self) -> Settings:
        data = _read_nonsecret(self.path)
        token = self.backend.get(KEYCHAIN_SERVICE, KEYCHAIN_ACCOUNT)
        if token:
            data["token"] = token
        try:
            return Settings.model_validate(data)
        except ValidationError:
            raise BiwengerError("invalid_config", "La configuración local no es válida.") from None

    def save(self, settings: Settings) -> None:
        if not settings.token:
            raise BiwengerError("invalid_config", "No hay una sesión que guardar.")
        previous = self.backend.get(KEYCHAIN_SERVICE, KEYCHAIN_ACCOUNT)
        self.backend.set(KEYCHAIN_SERVICE, KEYCHAIN_ACCOUNT, settings.token.get_secret_value())
        try:
            _atomic_write(self.path, settings.model_dump())
        except Exception:
            if previous:
                self.backend.set(KEYCHAIN_SERVICE, KEYCHAIN_ACCOUNT, previous)
            else:
                self.backend.delete(KEYCHAIN_SERVICE, KEYCHAIN_ACCOUNT)
            raise

    def disconnect(self) -> None:
        self.backend.delete(KEYCHAIN_SERVICE, KEYCHAIN_ACCOUNT)
        _check_path(self.path)
        if self.path.exists():
            try:
                self.path.unlink()
            except OSError:
                raise BiwengerError(
                    "disconnect_failed", "No se pudo eliminar la configuración local."
                ) from None


def load_settings(path: Path | None = None) -> Settings:
    """Carga el archivo antiguo solo cuando se indicó de forma explícita."""
    if path is None and not os.environ.get("BIWENGER_CONFIG"):
        return SecureSettingsStore().load()
    path = path or default_config_path()
    data = _read_nonsecret(path)
    if not data:
        return Settings()
    try:
        return Settings.model_validate(data)
    except ValidationError:
        raise BiwengerError(
            "invalid_config", "Configuración inválida; vuelve a conectar Biwenger."
        ) from None


def save_settings(settings: Settings, path: Path | None = None) -> None:
    """Guarda en modo antiguo si hay ruta; el modo nuevo utiliza el llavero."""
    if path is None and not os.environ.get("BIWENGER_CONFIG"):
        SecureSettingsStore().save(settings)
        return
    path = path or default_config_path()
    data = settings.model_dump()
    data["token"] = settings.token.get_secret_value() if settings.token else None
    _atomic_write(path, data)
