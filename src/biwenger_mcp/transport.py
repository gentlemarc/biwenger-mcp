"""Transporte cerrado: solo GET a endpoints concretos, sin redirecciones ni proxy implícito."""

from __future__ import annotations

import asyncio
import copy
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

from .config import SUPPORTED_SCORES, Settings
from .errors import BiwengerError

PUBLIC = "https://cf.biwenger.com"
PRIVATE = "https://biwenger.as.com"
MAX_BYTES = 8 * 1024 * 1024
PLAYER_FIELDS = "*,team,fitness,reports,prices,competition,seasons,news"
USER_FIELDS = (
    "*,lineup(type,playersID),players(*,fitness,team,owner),market(*,-userID),offers,-trophies"
)


@dataclass(frozen=True)
class Endpoint:
    name: str
    path: str
    private: bool = False
    params: tuple[tuple[str, str], ...] = ()

    @property
    def url(self) -> str:
        return (PRIVATE if self.private else PUBLIC) + self.path


def catalog_endpoint(score_id: int) -> Endpoint:
    if score_id not in SUPPORTED_SCORES:
        raise BiwengerError("unsupported_score", "Sistema de puntuación no compatible.")
    return Endpoint(
        "catalog",
        "/api/v2/competitions/la-liga/data",
        params=(("lang", "es"), ("score", str(score_id))),
    )


CATALOG = catalog_endpoint(2)
EVOLUTION = Endpoint(
    "evolution",
    "/api/v2/competitions/la-liga/market",
    params=(("interval", "day"), ("includeValues", "true")),
)
HOME = Endpoint("home", "/api/v2/home", True)
USER = Endpoint("user", "/api/v2/user", True, (("fields", USER_FIELDS),))
MARKET = Endpoint("market", "/api/v2/market", True)
FIXED_ENDPOINTS = (EVOLUTION, HOME, USER, MARKET)


def player_endpoint(slug: str, score_id: int = 2) -> Endpoint:
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug) or len(slug) > 150:
        raise BiwengerError("invalid_player", "Identificador de jugador no válido.")
    return Endpoint(
        "player",
        f"/api/v2/players/la-liga/{slug}",
        params=(("fields", PLAYER_FIELDS), ("score", str(score_id)), ("lang", "es")),
    )


def validate_endpoint(endpoint: Endpoint) -> None:
    if endpoint in FIXED_ENDPOINTS:
        return
    if endpoint.name == "catalog" and endpoint.path == "/api/v2/competitions/la-liga/data":
        if endpoint in {catalog_endpoint(score_id) for score_id in SUPPORTED_SCORES}:
            return
    prefix = "/api/v2/players/la-liga/"
    if endpoint.name == "player" and endpoint.path.startswith(prefix):
        slug = endpoint.path[len(prefix) :]
        if endpoint in {player_endpoint(slug, score_id) for score_id in SUPPORTED_SCORES}:
            return
    raise BiwengerError(
        "request_blocked", "La operación no pertenece a la lista de consultas permitidas."
    )


@dataclass
class Snapshot:
    data: dict[str, Any]
    endpoint: str
    fetched_at: str
    expires_at: float


class ReadOnlyTransport:
    def __init__(
        self,
        settings: Settings,
        *,
        http_transport: httpx.AsyncBaseTransport | None = None,
        sleep=asyncio.sleep,
    ):
        self.settings = settings
        self._http = httpx.AsyncClient(
            timeout=settings.timeout_seconds,
            follow_redirects=False,
            trust_env=False,
            transport=http_transport,
            headers={"Accept": "application/json", "User-Agent": "biwenger-readonly-mcp/0.2"},
        )
        self._cache: dict[Endpoint, Snapshot] = {}
        self._locks: dict[Endpoint, asyncio.Lock] = {}
        self._semaphore = asyncio.Semaphore(2)
        self._sleep = sleep

    async def close(self) -> None:
        await self._http.aclose()

    def clear(self) -> None:
        self._cache.clear()

    async def read(self, endpoint: Endpoint) -> Snapshot:
        validate_endpoint(endpoint)
        if endpoint.private and not self.settings.authenticated:
            raise BiwengerError(
                "not_configured", "Conecta tu cuenta con la herramienta connect_biwenger."
            )
        async with self._locks.setdefault(endpoint, asyncio.Lock()):
            cached = self._cache.get(endpoint)
            if cached and cached.expires_at > time.monotonic():
                return copy.deepcopy(cached)
            async with self._semaphore:
                snapshot = await self._fetch(endpoint)
            self._cache[endpoint] = snapshot
            return copy.deepcopy(snapshot)

    async def _fetch(self, endpoint: Endpoint) -> Snapshot:
        headers = {"x-lang": "es"}
        if endpoint.private:
            headers.update(
                {
                    "authorization": "Bearer " + self.settings.token.get_secret_value(),
                    "x-league": str(self.settings.league_id),
                    "x-user": str(self.settings.user_id),
                }
            )
            if self.settings.client_version:
                headers["x-version"] = self.settings.client_version
        for attempt in range(3):
            try:
                async with self._http.stream(
                    "GET", endpoint.url, params=endpoint.params, headers=headers
                ) as response:
                    status = response.status_code
                    if status == 401:
                        self.clear()
                        raise BiwengerError(
                            "auth_required",
                            "La sesión ha caducado; usa connect_biwenger para renovarla.",
                        )
                    if status == 403:
                        self.clear()
                        raise BiwengerError(
                            "access_denied",
                            "Biwenger no permite esta consulta. No se intentará eludir el bloqueo.",
                        )
                    if status == 429 or 500 <= status < 600:
                        wait = self._retry_delay(response.headers.get("retry-after"), attempt)
                        if attempt < 2 and wait <= 5:
                            await self._sleep(wait)
                            continue
                        code = "rate_limited" if status == 429 else "upstream_unavailable"
                        raise BiwengerError(
                            code,
                            "Biwenger no está disponible para esta consulta; inténtalo más tarde.",
                            retryable=True,
                        )
                    if status != 200:
                        raise BiwengerError(
                            "upstream_http_error",
                            f"Consulta rechazada por Biwenger (HTTP {status}).",
                        )
                    if "json" not in response.headers.get("content-type", "").lower():
                        raise BiwengerError("invalid_response", "Biwenger no devolvió JSON.")
                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        body.extend(chunk)
                        if len(body) > MAX_BYTES:
                            raise BiwengerError(
                                "response_too_large", "Respuesta de Biwenger demasiado grande."
                            )
                    import json

                    try:
                        payload = json.loads(body)
                    except (ValueError, UnicodeDecodeError):
                        raise BiwengerError(
                            "invalid_response", "JSON no válido de Biwenger."
                        ) from None
                    if not isinstance(payload, dict):
                        raise BiwengerError(
                            "schema_changed", "La respuesta de Biwenger ha cambiado de estructura."
                        )
                    if payload.get("status") in (401, 403):
                        self.clear()
                        code = "auth_required" if payload["status"] == 401 else "access_denied"
                        raise BiwengerError(code, "Biwenger ha rechazado la sesión o el acceso.")
                    if payload.get("status") != 200 or not isinstance(payload.get("data"), dict):
                        raise BiwengerError(
                            "schema_changed", "Respuesta de Biwenger sin estado o datos válidos."
                        )
                    return Snapshot(
                        payload["data"],
                        endpoint.name,
                        datetime.now(timezone.utc).isoformat(),
                        time.monotonic() + self.settings.cache_seconds,
                    )
            except (httpx.TimeoutException, httpx.NetworkError):
                if attempt < 2:
                    await self._sleep(0.5 * (2**attempt))
                    continue
                raise BiwengerError(
                    "network_error",
                    "No se pudo consultar Biwenger dentro del tiempo permitido.",
                    retryable=True,
                ) from None
            except httpx.HTTPError:
                raise BiwengerError(
                    "network_error", "Error de transporte al consultar Biwenger.", retryable=True
                ) from None
        raise BiwengerError("network_error", "Consulta no completada.", retryable=True)

    @staticmethod
    def _retry_delay(value: str | None, attempt: int) -> float:
        if value:
            try:
                return max(0, float(value))
            except ValueError:
                try:
                    return max(
                        0,
                        (parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds(),
                    )
                except (ValueError, TypeError, OverflowError):
                    pass
        return 0.5 * (2**attempt)
