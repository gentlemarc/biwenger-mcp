"""Autenticación acotada para el asistente local; nunca expone contraseñas al MCP."""

from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass
from typing import Any

import httpx
from pydantic import SecretStr

from .config import SUPPORTED_SCORES, Settings
from .errors import BiwengerError

BASE_URL = "https://biwenger.as.com"
LOGIN_URL = BASE_URL + "/api/v2/auth/login"
ACCOUNT_URL = BASE_URL + "/api/v2/account"
HOME_URL = BASE_URL + "/api/v2/home"
MAX_AUTH_BYTES = 2 * 1024 * 1024


def _normalized(value: str) -> str:
    return "".join(
        char
        for char in unicodedata.normalize("NFKD", value.casefold())
        if not unicodedata.combining(char)
    )


def _integer(value: Any) -> int | None:
    return value if type(value) is int and value > 0 else None


@dataclass(frozen=True)
class LeagueChoice:
    league_id: int
    user_id: int
    name: str
    competition: str
    market_mode: str
    score_id: int
    score_name: str
    client_version: str | None

    def public(self) -> dict:
        return {
            "league_id": self.league_id,
            "name": self.name[:200],
            "competition": self.competition,
            "market_mode": self.market_mode,
            "score_id": self.score_id,
            "score_name": self.score_name,
        }

    def settings(self, token: SecretStr) -> Settings:
        return Settings(
            token=token,
            league_id=self.league_id,
            user_id=self.user_id,
            client_version=self.client_version,
            score_id=self.score_id,
            league_settings_confirmed=True,
        )


@dataclass
class AuthenticationSession:
    token: SecretStr
    leagues: tuple[LeagueChoice, ...]

    def clear(self) -> None:
        self.token = SecretStr("")


class AuthenticationClient:
    def __init__(
        self,
        *,
        http_transport: httpx.AsyncBaseTransport | None = None,
        timeout_seconds: float = 15,
    ):
        self._http = httpx.AsyncClient(
            timeout=timeout_seconds,
            follow_redirects=False,
            trust_env=False,
            transport=http_transport,
            headers={
                "Accept": "application/json",
                "User-Agent": "biwenger-readonly-mcp/0.2.2",
                "x-lang": "es",
            },
        )

    async def close(self) -> None:
        await self._http.aclose()

    @staticmethod
    async def _payload(response: httpx.Response) -> dict:
        if "json" not in response.headers.get("content-type", "").lower():
            raise BiwengerError("invalid_response", "Biwenger no devolvió JSON.")
        body = await response.aread()
        if len(body) > MAX_AUTH_BYTES:
            raise BiwengerError("response_too_large", "Respuesta de Biwenger demasiado grande.")
        try:
            payload = json.loads(body)
        except (ValueError, UnicodeDecodeError):
            raise BiwengerError("invalid_response", "Biwenger devolvió una respuesta no válida.") from None
        if not isinstance(payload, dict):
            raise BiwengerError("schema_changed", "La respuesta de acceso ha cambiado.")
        return payload

    @staticmethod
    def _status(response: httpx.Response, *, login: bool = False) -> None:
        if response.status_code in (401, 403):
            code = "invalid_credentials" if login else "auth_required"
            message = (
                "Correo o contraseña de Biwenger incorrectos."
                if login
                else "La sesión de Biwenger ha caducado."
            )
            raise BiwengerError(code, message)
        if response.status_code == 429:
            raise BiwengerError(
                "rate_limited", "Demasiados intentos; espera antes de volver a probar.", retryable=True
            )
        if response.status_code != 200:
            raise BiwengerError(
                "upstream_http_error",
                f"Biwenger rechazó la operación (HTTP {response.status_code}).",
            )

    async def authenticate(self, email: str, password: str) -> AuthenticationSession:
        if not isinstance(email, str) or not 3 <= len(email.strip()) <= 320 or "\n" in email:
            raise BiwengerError("invalid_credentials", "Introduce un correo válido.")
        if not isinstance(password, str) or not 1 <= len(password) <= 1024:
            raise BiwengerError("invalid_credentials", "Introduce tu contraseña de Biwenger.")
        try:
            response = await self._http.post(
                LOGIN_URL, json={"email": email.strip(), "password": password}
            )
        except (httpx.TimeoutException, httpx.NetworkError):
            raise BiwengerError(
                "network_error", "No se pudo conectar con Biwenger.", retryable=True
            ) from None
        finally:
            password = ""
        self._status(response, login=True)
        payload = await self._payload(response)
        # La API web actual devuelve el token en la raíz. Conservamos la
        # estructura antigua anidada para no romper instalaciones previas.
        token = payload.get("token")
        if token is None:
            data = payload.get("data")
            token = data.get("token") if isinstance(data, dict) else None
        if not isinstance(token, str) or not token.strip():
            raise BiwengerError("schema_changed", "Biwenger no devolvió una sesión válida.")
        token = token.strip()
        if any(character.isspace() for character in token):
            raise BiwengerError("schema_changed", "Biwenger no devolvió una sesión válida.")
        secret = SecretStr(token)
        leagues = await self.discover(secret)
        if not leagues:
            raise BiwengerError(
                "no_compatible_leagues",
                "No hay ligas compatibles: se admite LaLiga con fichajes Clásica y sistemas de puntuación predefinidos.",
            )
        return AuthenticationSession(secret, tuple(leagues))

    async def discover(self, token: SecretStr) -> list[LeagueChoice]:
        try:
            response = await self._http.get(
                ACCOUNT_URL, headers={"authorization": "Bearer " + token.get_secret_value()}
            )
        except (httpx.TimeoutException, httpx.NetworkError):
            raise BiwengerError(
                "network_error", "No se pudo consultar la cuenta de Biwenger.", retryable=True
            ) from None
        self._status(response)
        payload = await self._payload(response)
        data = payload.get("data")
        if not isinstance(data, dict) or not isinstance(data.get("leagues"), list):
            raise BiwengerError("schema_changed", "No se pudieron descubrir las ligas.")
        version_value = data.get("version")
        version = str(version_value) if isinstance(version_value, (int, str)) else None
        choices: list[LeagueChoice] = []
        for raw in data["leagues"]:
            if not isinstance(raw, dict):
                continue
            league_id = _integer(raw.get("id"))
            user = raw.get("user")
            user_id = _integer(user.get("id")) if isinstance(user, dict) else None
            competition = raw.get("competition")
            if isinstance(competition, dict):
                competition = competition.get("slug")
            api_mode = _normalized(str(raw.get("mode") or ""))
            league_type = _normalized(str(raw.get("type") or ""))
            market_mode = _normalized(str(raw.get("marketMode") or ""))
            score_id = _integer(raw.get("scoreID"))
            settings = raw.get("settings")
            custom = settings.get("customScore") if isinstance(settings, dict) else None
            if (
                league_id is None
                or user_id is None
                or competition != "la-liga"
                or api_mode != "league"
                or league_type != "normal"
                or market_mode != "classic"
                or score_id not in SUPPORTED_SCORES
                or bool(custom)
            ):
                continue
            name = raw.get("name")
            choices.append(
                LeagueChoice(
                    league_id=league_id,
                    user_id=user_id,
                    name=name if isinstance(name, str) and name.strip() else "Liga sin nombre",
                    competition="la-liga",
                    market_mode="classic",
                    score_id=score_id,
                    score_name=SUPPORTED_SCORES[score_id],
                    client_version=version,
                )
            )
        return choices

    async def verify(self, session: AuthenticationSession, choice: LeagueChoice) -> Settings:
        if choice not in session.leagues:
            raise BiwengerError("invalid_league", "La liga no pertenece a esta sesión.")
        headers = {
            "authorization": "Bearer " + session.token.get_secret_value(),
            "x-league": str(choice.league_id),
            "x-user": str(choice.user_id),
        }
        if choice.client_version:
            headers["x-version"] = choice.client_version
        try:
            response = await self._http.get(HOME_URL, headers=headers)
        except (httpx.TimeoutException, httpx.NetworkError):
            raise BiwengerError(
                "network_error", "No se pudo verificar la liga elegida.", retryable=True
            ) from None
        self._status(response)
        payload = await self._payload(response)
        data = payload.get("data")
        if not isinstance(data, dict):
            raise BiwengerError("schema_changed", "No se pudo verificar la liga elegida.")
        league = data.get("league")
        user = data.get("user")
        if (
            not isinstance(league, dict)
            or not isinstance(user, dict)
            or league.get("id") != choice.league_id
            or user.get("id") != choice.user_id
        ):
            raise BiwengerError("context_mismatch", "Biwenger devolvió otra liga o usuario.")
        observed_score = league.get("scoreID")
        if observed_score is not None and observed_score != choice.score_id:
            raise BiwengerError("context_mismatch", "La puntuación de la liga ha cambiado.")
        competition = data.get("competition")
        if isinstance(competition, dict):
            competition = competition.get("slug")
        if competition not in (None, choice.competition):
            raise BiwengerError("context_mismatch", "La competición de la liga ha cambiado.")
        if (
            _normalized(str(league.get("mode") or "")) not in {"", "league"}
            or _normalized(str(league.get("type") or "")) not in {"", "normal"}
            or _normalized(str(league.get("marketMode") or "")) not in {"", "classic"}
        ):
            raise BiwengerError("context_mismatch", "El tipo de liga ha cambiado.")
        return choice.settings(session.token)
