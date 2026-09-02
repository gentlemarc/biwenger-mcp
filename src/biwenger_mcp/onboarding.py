"""Asistente web efímero, limitado a loopback, para conectar y desconectar Biwenger."""

from __future__ import annotations

import asyncio
import hmac
import json
import secrets
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Callable
from urllib.parse import parse_qs, urlparse

from .auth import AuthenticationClient, AuthenticationSession, LeagueChoice
from .config import SecureSettingsStore
from .errors import BiwengerError
from .onboarding_ui import render_page

MAX_FORM_BYTES = 16 * 1024
WIZARD_TTL_SECONDS = 10 * 60


class _LoopbackServer(HTTPServer):
    allow_reuse_address = False


class WizardSession:
    def __init__(
        self,
        mode: str,
        store: SecureSettingsStore,
        auth_factory: Callable[[], AuthenticationClient],
        ttl_seconds: int = WIZARD_TTL_SECONDS,
    ):
        if mode not in {"connect", "disconnect"}:
            raise ValueError("invalid wizard mode")
        self.mode = mode
        self.store = store
        self.auth_factory = auth_factory
        self.nonce = secrets.token_urlsafe(32)
        self.script_nonce = secrets.token_urlsafe(18)
        self.expires_at = time.monotonic() + ttl_seconds
        self.pending: AuthenticationSession | None = None
        self.server: _LoopbackServer | None = None
        self.thread: threading.Thread | None = None
        self.complete = False
        self.login_attempts = 0

    @property
    def origin(self) -> str:
        if not self.server:
            raise RuntimeError("wizard not started")
        return f"http://127.0.0.1:{self.server.server_port}"

    @property
    def url(self) -> str:
        return f"{self.origin}/{self.mode}/{self.nonce}"

    def expired(self) -> bool:
        return time.monotonic() >= self.expires_at

    def start(self, *, open_browser: bool = True) -> dict:
        session = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "BiwengerSetup/0.3"
            sys_version = ""

            def log_message(self, format, *args):
                return

            def _allowed(self) -> bool:
                expected_host = f"127.0.0.1:{self.server.server_port}"
                return self.client_address[0] == "127.0.0.1" and self.headers.get("Host") == expected_host

            def _headers(self, status: int, content_type: str, length: int) -> None:
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(length))
                self.send_header("Cache-Control", "no-store, max-age=0")
                self.send_header("Pragma", "no-cache")
                self.send_header("Referrer-Policy", "no-referrer")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("X-Frame-Options", "DENY")
                self.send_header(
                    "Content-Security-Policy",
                    "default-src 'none'; style-src 'unsafe-inline'; "
                    f"script-src 'nonce-{session.script_nonce}'; connect-src 'self'; "
                    "form-action 'self'; frame-ancestors 'none'; base-uri 'none'",
                )
                self.end_headers()

            def _send(self, status: int, body: str, content_type: str = "text/html; charset=utf-8") -> None:
                encoded = body.encode("utf-8")
                self._headers(status, content_type, len(encoded))
                self.wfile.write(encoded)

            def _json(self, status: int, value: dict) -> None:
                self._send(status, json.dumps(value, ensure_ascii=False), "application/json; charset=utf-8")

            def _valid_nonce(self, supplied: str) -> bool:
                return not session.expired() and hmac.compare_digest(supplied, session.nonce)

            def _read_form(self) -> dict[str, str]:
                if self.headers.get("Origin") != session.origin:
                    raise BiwengerError("csrf_rejected", "La solicitud local no es válida.")
                if self.headers.get("Transfer-Encoding"):
                    raise BiwengerError("invalid_request", "Formato de solicitud no permitido.")
                content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip()
                if content_type != "application/x-www-form-urlencoded":
                    raise BiwengerError("invalid_request", "Formato de solicitud no permitido.")
                try:
                    length = int(self.headers.get("Content-Length", ""))
                except ValueError:
                    raise BiwengerError("invalid_request", "Longitud de solicitud no válida.") from None
                if not 0 <= length <= MAX_FORM_BYTES:
                    raise BiwengerError("request_too_large", "La solicitud es demasiado grande.")
                body = self.rfile.read(length)
                try:
                    values = parse_qs(body.decode("utf-8"), strict_parsing=True, max_num_fields=8)
                except (UnicodeDecodeError, ValueError):
                    raise BiwengerError("invalid_request", "Formulario no válido.") from None
                result = {key: rows[0] for key, rows in values.items() if len(rows) == 1}
                if not self._valid_nonce(result.pop("nonce", "")):
                    raise BiwengerError("nonce_expired", "El enlace ha caducado; vuelve a abrirlo desde Claude.")
                return result

            def do_GET(self):
                parsed = urlparse(self.path)
                if not self._allowed():
                    self._send(403, "Acceso local rechazado.", "text/plain; charset=utf-8")
                    return
                if parsed.query or parsed.path != f"/{session.mode}/{session.nonce}":
                    self._send(404, "No encontrado.", "text/plain; charset=utf-8")
                    return
                if session.expired():
                    self._send(410, "El enlace ha caducado. Vuelve a Claude para generar otro.")
                    return
                self._send(200, session._page())

            def do_POST(self):
                parsed = urlparse(self.path)
                if not self._allowed():
                    self._json(403, {"error": {"code": "loopback_only", "message": "Acceso local rechazado."}})
                    return
                try:
                    fields = self._read_form()
                    if parsed.query:
                        raise BiwengerError("invalid_request", "Ruta no válida.")
                    if parsed.path == f"/api/login/{session.nonce}" and session.mode == "connect":
                        session._login(fields)
                        self._json(200, {"leagues": [choice.public() for choice in session.pending.leagues]})
                    elif parsed.path == f"/api/select/{session.nonce}" and session.mode == "connect":
                        session._select(fields)
                        self._json(200, {"connected": True, "restart_required": True})
                        session._finish()
                    elif parsed.path == f"/api/disconnect/{session.nonce}" and session.mode == "disconnect":
                        session._disconnect(fields)
                        self._json(200, {"disconnected": True, "restart_required": True})
                        session._finish()
                    else:
                        raise BiwengerError("invalid_request", "Ruta no válida.")
                except BiwengerError as error:
                    self._json(400 if error.code != "request_too_large" else 413, {"error": error.public()})
                except Exception:
                    self._json(500, {"error": {"code": "local_setup_failed", "message": "No se pudo completar la configuración.", "retryable": False}})

        self.server = _LoopbackServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True, name="biwenger-setup")
        self.thread.start()
        opened = webbrowser.open(self.url) if open_browser else False
        return {"status": "browser_opened" if opened else "ready", "url": self.url, "expires_in_seconds": int(self.expires_at - time.monotonic())}

    def _login(self, fields: dict[str, str]) -> None:
        self.login_attempts += 1
        if self.login_attempts > 5:
            raise BiwengerError(
                "local_rate_limited", "Demasiados intentos en este enlace; abre uno nuevo."
            )
        email = fields.pop("email", "")
        password = fields.pop("password", "")
        if fields:
            raise BiwengerError("invalid_request", "El formulario contiene campos no permitidos.")

        async def perform():
            client = self.auth_factory()
            try:
                return await client.authenticate(email, password)
            finally:
                await client.close()

        try:
            pending = asyncio.run(perform())
        finally:
            password = ""
        if self.pending:
            self.pending.clear()
        self.pending = pending

    def _select(self, fields: dict[str, str]) -> None:
        if not self.pending:
            raise BiwengerError("login_required", "Inicia sesión antes de elegir una liga.")
        if set(fields) != {"league_id"}:
            raise BiwengerError("invalid_request", "Selección no válida.")
        try:
            league_id = int(fields["league_id"])
        except ValueError:
            raise BiwengerError("invalid_league", "Liga no válida.") from None
        choice = next((item for item in self.pending.leagues if item.league_id == league_id), None)
        if choice is None:
            raise BiwengerError("invalid_league", "La liga no pertenece a esta cuenta.")

        async def perform() -> LeagueChoice | object:
            client = self.auth_factory()
            try:
                return await client.verify(self.pending, choice)
            finally:
                await client.close()

        settings = asyncio.run(perform())
        self.store.save(settings)
        self.pending.clear()
        self.pending = None

    def _disconnect(self, fields: dict[str, str]) -> None:
        if fields != {"confirm": "disconnect"}:
            raise BiwengerError("confirmation_required", "Confirma la desconexión en la página.")
        self.store.disconnect()

    def _finish(self) -> None:
        self.complete = True
        threading.Timer(1.0, self.stop).start()

    def stop(self) -> None:
        if self.pending:
            self.pending.clear()
            self.pending = None
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None

    def _page(self) -> str:
        return render_page(self.mode, self.nonce, self.script_nonce)


class WizardManager:
    def __init__(
        self,
        store: SecureSettingsStore | None = None,
        auth_factory: Callable[[], AuthenticationClient] = AuthenticationClient,
    ):
        self.store = store or SecureSettingsStore()
        self.auth_factory = auth_factory
        self._active: WizardSession | None = None
        self._lock = threading.Lock()

    def start(self, mode: str, *, open_browser: bool = True) -> dict:
        with self._lock:
            if self._active and not self._active.expired() and not self._active.complete:
                if self._active.mode == mode:
                    opened = webbrowser.open(self._active.url) if open_browser else False
                    return {"status": "browser_opened" if opened else "ready", "url": self._active.url, "expires_in_seconds": int(self._active.expires_at - time.monotonic())}
                self._active.stop()
            self._active = WizardSession(mode, self.store, self.auth_factory)
            return self._active.start(open_browser=open_browser)


wizard_manager = WizardManager()
