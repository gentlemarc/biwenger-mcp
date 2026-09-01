import json

import httpx
import pytest
from pydantic import SecretStr

from biwenger_mcp.auth import ACCOUNT_URL, HOME_URL, LOGIN_URL, AuthenticationClient
from biwenger_mcp.config import SUPPORTED_SCORES, SecureSettingsStore, Settings
from biwenger_mcp.errors import BiwengerError


def account_league(score_id=2, **updates):
    value = {
        "id": 9001,
        "name": "Liga sintética",
        "competition": "la-liga",
        "mode": "classic",
        "scoreID": score_id,
        "user": {"id": 8001, "email": "private@example.test"},
        "settings": {"customScore": ""},
    }
    value.update(updates)
    return value


def auth_handler(requests, leagues, *, login_status=200, account_status=200, home_status=200):
    def handler(request):
        requests.append(request)
        if str(request.url) == LOGIN_URL:
            return httpx.Response(
                login_status,
                json={"status": login_status, "data": {"token": "synthetic-auth-token"}},
            )
        if str(request.url) == ACCOUNT_URL:
            return httpx.Response(
                account_status,
                json={"status": account_status, "data": {"version": 631, "leagues": leagues}},
            )
        if str(request.url) == HOME_URL:
            return httpx.Response(
                home_status,
                json={
                    "status": home_status,
                    "data": {"league": {"id": 9001, "scoreID": 2}, "user": {"id": 8001}},
                },
            )
        return httpx.Response(404, json={"status": 404, "data": {}})

    return handler


async def test_login_discovers_only_compatible_leagues_and_verifies_home():
    requests = []
    leagues = [
        account_league(),
        account_league(id=9002, mode="fantasy"),
        account_league(id=9003, competition="premier-league"),
        account_league(id=9004, scoreID=4),
        account_league(id=9005, settings={"customScore": {"formula": "private"}}),
    ]
    client = AuthenticationClient(
        http_transport=httpx.MockTransport(auth_handler(requests, leagues))
    )
    try:
        session = await client.authenticate("person@example.test", "synthetic-password")
        assert [league.league_id for league in session.leagues] == [9001]
        settings = await client.verify(session, session.leagues[0])
        assert settings.authenticated and settings.score_id == 2
        assert settings.client_version == "631"
        assert all(request.url.host == "biwenger.as.com" for request in requests)
        assert requests[0].method == "POST"
        assert all(request.method == "GET" for request in requests[1:])
    finally:
        await client.close()


@pytest.mark.parametrize("score_id", sorted(SUPPORTED_SCORES))
async def test_all_standard_scores_are_discovered(score_id):
    requests = []
    client = AuthenticationClient(
        http_transport=httpx.MockTransport(
            auth_handler(requests, [account_league(score_id=score_id)])
        )
    )
    try:
        session = await client.authenticate("person@example.test", "password")
        assert session.leagues[0].score_id == score_id
        assert session.leagues[0].score_name == SUPPORTED_SCORES[score_id]
    finally:
        await client.close()


@pytest.mark.parametrize(
    "login_status,account_status,code",
    [(401, 200, "invalid_credentials"), (403, 200, "invalid_credentials"), (200, 401, "auth_required")],
)
async def test_authentication_errors_are_closed_and_sanitized(
    login_status, account_status, code, caplog
):
    requests = []
    secret = "do-not-log-this-password"
    client = AuthenticationClient(
        http_transport=httpx.MockTransport(
            auth_handler(
                requests,
                [account_league()],
                login_status=login_status,
                account_status=account_status,
            )
        )
    )
    try:
        with pytest.raises(BiwengerError) as error:
            await client.authenticate("person@example.test", secret)
        assert error.value.code == code
        assert secret not in str(error.value) + caplog.text
    finally:
        await client.close()


class MemoryBackend:
    def __init__(self, *, fail=False):
        self.value = None
        self.fail = fail

    def get(self, service, account):
        if self.fail:
            raise BiwengerError("secure_storage_unavailable", "Llavero no disponible.")
        return self.value

    def set(self, service, account, value):
        if self.fail:
            raise BiwengerError("secure_storage_unavailable", "Llavero no disponible.")
        self.value = value

    def delete(self, service, account):
        self.value = None


def test_secure_store_keeps_token_out_of_file_and_supports_reconnect(tmp_path):
    backend = MemoryBackend()
    store = SecureSettingsStore(tmp_path / "settings.json", backend)
    first = Settings(token=SecretStr("first-token"), league_id=1, user_id=2)
    second = Settings(token=SecretStr("second-token"), league_id=3, user_id=4, score_id=7)
    store.save(first)
    assert "first-token" not in store.path.read_text()
    store.save(second)
    assert backend.value == "second-token"
    assert store.load().score_id == 7
    store.disconnect()
    assert backend.value is None and not store.path.exists()


def test_secure_store_fails_closed_when_keychain_is_unavailable(tmp_path):
    store = SecureSettingsStore(tmp_path / "settings.json", MemoryBackend(fail=True))
    with pytest.raises(BiwengerError) as error:
        store.save(Settings(token=SecretStr("token"), league_id=1, user_id=2))
    assert error.value.code == "secure_storage_unavailable"
    assert not store.path.exists()


def test_nonsecret_config_contains_no_credential_keys(tmp_path):
    backend = MemoryBackend()
    store = SecureSettingsStore(tmp_path / "settings.json", backend)
    store.save(Settings(token=SecretStr("token"), league_id=1, user_id=2))
    data = json.loads(store.path.read_text())
    assert not ({"token", "password", "email"} & set(data))
