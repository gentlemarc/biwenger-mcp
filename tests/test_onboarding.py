import httpx
from pydantic import SecretStr

from biwenger_mcp.auth import AuthenticationSession, LeagueChoice
from biwenger_mcp.config import Settings
from biwenger_mcp.errors import BiwengerError
from biwenger_mcp.onboarding import MAX_FORM_BYTES, WizardSession


class MemoryStore:
    def __init__(self):
        self.saved = None
        self.disconnected = False

    def save(self, settings):
        self.saved = settings

    def disconnect(self):
        self.disconnected = True
        self.saved = None


class FakeAuth:
    def __init__(self, *, reject=False):
        self.reject = reject

    async def authenticate(self, email, password):
        if self.reject:
            raise BiwengerError("invalid_credentials", "Correo o contraseña incorrectos.")
        choice = LeagueChoice(9001, 8001, "Liga sintética", "la-liga", "classic", 2, "SofaScore", "631")
        return AuthenticationSession(SecretStr("synthetic-token"), (choice,))

    async def verify(self, session, choice):
        return choice.settings(session.token)

    async def close(self):
        return None


def post(client, session, path, values, **kwargs):
    return client.post(
        path,
        data={"nonce": session.nonce, **values},
        headers={"Origin": session.origin, **kwargs.pop("headers", {})},
        **kwargs,
    )


def test_connect_wizard_login_selection_and_no_credentials_in_result():
    store = MemoryStore()
    session = WizardSession("connect", store, FakeAuth)
    session.start(open_browser=False)
    try:
        with httpx.Client(base_url=session.origin, trust_env=False) as client:
            page = client.get(f"/connect/{session.nonce}")
            assert page.status_code == 200
            login = post(
                client,
                session,
                f"/api/login/{session.nonce}",
                {"email": "person@example.test", "password": "synthetic-password"},
            )
            assert login.status_code == 200
            assert "password" not in login.text and "synthetic-token" not in login.text
            selected = post(
                client,
                session,
                f"/api/select/{session.nonce}",
                {"league_id": "9001"},
            )
            assert selected.json() == {"connected": True, "restart_required": True}
            assert isinstance(store.saved, Settings) and store.saved.authenticated
    finally:
        session.stop()


def test_login_failure_is_sanitized_and_session_can_be_cancelled():
    store = MemoryStore()
    session = WizardSession("connect", store, lambda: FakeAuth(reject=True))
    session.start(open_browser=False)
    try:
        with httpx.Client(base_url=session.origin, trust_env=False) as client:
            result = post(
                client,
                session,
                f"/api/login/{session.nonce}",
                {"email": "person@example.test", "password": "secret-value"},
            )
            assert result.status_code == 400
            assert result.json()["error"]["code"] == "invalid_credentials"
            assert "secret-value" not in result.text
    finally:
        session.stop()
    assert store.saved is None


def test_csrf_host_expiry_and_body_limits():
    store = MemoryStore()
    session = WizardSession("connect", store, FakeAuth)
    session.start(open_browser=False)
    try:
        with httpx.Client(base_url=session.origin, trust_env=False) as client:
            missing_origin = client.post(
                f"/api/login/{session.nonce}", data={"nonce": session.nonce}
            )
            assert missing_origin.json()["error"]["code"] == "csrf_rejected"
            wrong_host = client.get(
                f"/connect/{session.nonce}",
                headers={"Host": f"localhost:{session.server.server_port}"},
            )
            assert wrong_host.status_code == 403
            too_large = post(
                client,
                session,
                f"/api/login/{session.nonce}",
                {"email": "x" * MAX_FORM_BYTES, "password": "x"},
            )
            assert too_large.status_code == 413
            session.expires_at = 0
            assert client.get(f"/connect/{session.nonce}").status_code == 410
    finally:
        session.stop()


def test_disconnect_requires_local_confirmation():
    store = MemoryStore()
    session = WizardSession("disconnect", store, FakeAuth)
    session.start(open_browser=False)
    try:
        with httpx.Client(base_url=session.origin, trust_env=False) as client:
            refused = post(
                client, session, f"/api/disconnect/{session.nonce}", {"confirm": "no"}
            )
            assert refused.json()["error"]["code"] == "confirmation_required"
            accepted = post(
                client,
                session,
                f"/api/disconnect/{session.nonce}",
                {"confirm": "disconnect"},
            )
            assert accepted.json()["disconnected"] is True
            assert store.disconnected is True
    finally:
        session.stop()


def test_connect_page_is_distinct_local_and_platform_neutral():
    session = WizardSession("connect", MemoryStore(), FakeAuth)
    session.start(open_browser=False)
    try:
        with httpx.Client(base_url=session.origin, trust_env=False) as client:
            response = client.get(f"/connect/{session.nonce}")
        page = response.text
        policy = response.headers["content-security-policy"]
        assert response.status_code == 200
        assert "Biwenger MCP" in page
        assert "Proyecto no oficial" in page
        assert "localmente en tu ordenador" in page
        assert "almacenamiento seguro del sistema" in page
        assert "Solo lectura" in page
        assert "Google, Apple o Facebook" in page
        assert "www.biwenger.com/faq/cuentas-contrasenas-combinar-cuentas/" in page
        assert "llavero" not in page.casefold() and "tu mac" not in page.casefold()
        assert "cdn.biwenger" not in page and "<script src=" not in page
        assert "innerHTML" not in page and "textContent = league.name" in page
        assert 'role="group" aria-label="Ligas compatibles"' in page
        assert "setAttribute('role', 'listitem')" not in page
        assert page.count("<script nonce=") == 1
        assert f"script-src 'nonce-{session.script_nonce}'" in policy
        assert "default-src 'none'" in policy and "connect-src 'self'" in policy
    finally:
        session.stop()


def test_disconnect_page_uses_the_same_safe_design_language():
    session = WizardSession("disconnect", MemoryStore(), FakeAuth)
    session.start(open_browser=False)
    try:
        with httpx.Client(base_url=session.origin, trust_env=False) as client:
            response = client.get(f"/disconnect/{session.nonce}")
        page = response.text
        assert response.status_code == 200
        assert "Desconecta <em>con control.</em>" in page
        assert "almacenamiento seguro del sistema" in page
        assert "No elimina tu cuenta de Biwenger" in page
        assert "Proyecto no oficial" in page
        assert "llavero" not in page.casefold() and "macos" not in page.casefold()
        assert "<script src=" not in page and page.count("<script nonce=") == 1
    finally:
        session.stop()
