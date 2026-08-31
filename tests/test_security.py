import asyncio
import json

import httpx
import pytest
from pydantic import SecretStr, ValidationError

from biwenger_mcp.config import Settings, load_settings, save_settings
from biwenger_mcp.errors import BiwengerError
from biwenger_mcp.transport import (
    CATALOG,
    HOME,
    MARKET,
    Endpoint,
    player_endpoint,
)


@pytest.mark.parametrize(
    "endpoint",
    [
        Endpoint("offers", "/api/v2/offers", True),
        Endpoint("market", "/api/v2/market", False),
        Endpoint("catalog", "/api/v2/competitions/la-liga/data", True),
        Endpoint("home", "/api/v2/home", True, (("action", "delete"),)),
        Endpoint("player", "/api/v2/players/la-liga/../../offers"),
    ],
)
async def test_only_exact_allowlisted_endpoints_can_be_requested(client_factory, endpoint):
    client, requests, _ = client_factory()
    with pytest.raises(BiwengerError):
        await client.transport.read(endpoint)
    assert requests == []


@pytest.mark.parametrize(
    "slug",
    [
        "../../offers",
        "https://example.com",
        "name?token=x",
        "name%2f..",
        "a/b",
        "a\r\nb",
        "",
        "a" * 151,
    ],
)
def test_slug_cannot_change_host_path_or_query(slug):
    with pytest.raises(BiwengerError):
        player_endpoint(slug)


async def test_private_reads_need_config_before_network(client_factory):
    client, requests, _ = client_factory()
    with pytest.raises(BiwengerError) as error:
        await client.transport.read(MARKET)
    assert error.value.code == "not_configured"
    assert requests == []


@pytest.mark.parametrize(
    "status,code",
    [
        (401, "auth_required"),
        (403, "access_denied"),
        (404, "upstream_http_error"),
        (302, "upstream_http_error"),
    ],
)
async def test_http_errors_are_not_success_and_do_not_leak(
    client_factory, settings, caplog, status, code
):
    secret = settings.token.get_secret_value()
    client, requests, _ = client_factory(
        settings,
        handler=lambda r: httpx.Response(
            status, text=secret, headers={"location": "https://evil.example"}
        ),
    )
    with pytest.raises(BiwengerError) as error:
        await client.transport.read(HOME)
    assert error.value.code == code
    assert len(requests) == 1
    assert secret not in str(error.value) + caplog.text


@pytest.mark.parametrize(
    "body",
    [
        {"status": 401, "data": {}},
        {"status": 403, "data": {}},
        {"status": 500, "data": {}},
        {"data": {}},
        {"status": 200, "data": []},
    ],
)
async def test_http_200_does_not_hide_api_error(client_factory, settings, body):
    client, _, _ = client_factory(settings, handler=lambda r: httpx.Response(200, json=body))
    with pytest.raises(BiwengerError):
        await client.transport.read(HOME)


async def test_html_and_broken_json_fail_safely(client_factory):
    for response in [
        httpx.Response(200, text="<html>captcha</html>"),
        httpx.Response(200, content=b"{broken", headers={"content-type": "application/json"}),
    ]:
        client, _, _ = client_factory(handler=lambda r: response)
        with pytest.raises(BiwengerError) as error:
            await client.transport.read(CATALOG)
        assert error.value.code == "invalid_response"


@pytest.mark.parametrize("status", [429, 500, 503])
async def test_transient_errors_have_bounded_retries(client_factory, status):
    client, requests, _ = client_factory(
        handler=lambda r: httpx.Response(status, headers={"retry-after": "0"})
    )
    with pytest.raises(BiwengerError) as error:
        await client.transport.read(CATALOG)
    assert error.value.retryable is True
    assert len(requests) == 3


async def test_long_retry_after_returns_without_early_retry(client_factory):
    client, requests, _ = client_factory(
        handler=lambda r: httpx.Response(429, headers={"retry-after": "120"})
    )
    with pytest.raises(BiwengerError) as error:
        await client.transport.read(CATALOG)
    assert error.value.code == "rate_limited"
    assert len(requests) == 1


async def test_timeout_has_bounded_retries_without_exception_details(client_factory):
    def handler(request):
        raise httpx.ReadTimeout("secret injected into error", request=request)

    client, requests, _ = client_factory(handler=handler)
    with pytest.raises(BiwengerError) as error:
        await client.transport.read(CATALOG)
    assert error.value.code == "network_error"
    assert "secret" not in str(error.value)
    assert len(requests) == 3


async def test_public_requests_never_receive_private_headers(client_factory, settings):
    client, requests, _ = client_factory(settings)
    await client.catalog()
    for header in ("authorization", "x-league", "x-user", "x-version"):
        assert header not in requests[0].headers


async def test_cache_coalesces_parallel_reads_and_is_not_mutable_by_caller(client_factory):
    client, requests, _ = client_factory()
    snapshots = await asyncio.gather(*(client.transport.read(CATALOG) for _ in range(5)))
    snapshots[0].data["scoreID"] = 99
    current = await client.transport.read(CATALOG)
    assert current.data["scoreID"] == 2
    assert len(requests) == 1
    client.transport.clear()
    await client.transport.read(CATALOG)
    assert len(requests) == 2


async def test_no_stale_success_after_cache_expiry(client_factory):
    calls = []

    def handler(request):
        calls.append(1)
        if len(calls) == 1:
            return httpx.Response(200, json={"status": 200, "data": {"ok": True}})
        return httpx.Response(401)

    client, _, _ = client_factory(Settings(cache_seconds=0), handler=handler)
    await client.transport.read(CATALOG)
    with pytest.raises(BiwengerError):
        await client.transport.read(CATALOG)


async def test_provider_cannot_echo_token_in_player_name(client_factory, settings):
    secret = settings.token.get_secret_value()
    client, _, _ = client_factory(
        settings, mutate=lambda d: d["catalog"]["players"]["101"].update(name=secret)
    )
    assert secret not in json.dumps(await client.search_players())


def test_configuration_permissions_and_secret_serialization(tmp_path, settings):
    path = tmp_path / ".local" / "session.json"
    save_settings(settings, path)
    assert path.stat().st_mode & 0o777 == 0o600
    assert path.parent.stat().st_mode & 0o777 == 0o700
    assert load_settings(path).token == settings.token
    assert "token" not in settings.model_dump()
    assert settings.token.get_secret_value() not in repr(settings)
    path.chmod(0o644)
    with pytest.raises(BiwengerError) as error:
        load_settings(path)
    assert error.value.code == "unsafe_config"


def test_symlinks_and_invalid_config_are_rejected(tmp_path, settings):
    path = tmp_path / "session.json"
    path.symlink_to(tmp_path / "missing.json")
    with pytest.raises(BiwengerError):
        load_settings(path)
    with pytest.raises(BiwengerError):
        save_settings(settings, path)
    path.unlink()
    path.write_text('{"token": "secret", "league_id": "invite-code"}')
    path.chmod(0o600)
    with pytest.raises(BiwengerError) as error:
        load_settings(path)
    assert "secret" not in str(error.value)


@pytest.mark.parametrize("token", ["bad\nheader", "bad\rheader", " ", "two words"])
def test_token_cannot_inject_headers(token):
    with pytest.raises(ValidationError):
        Settings(token=SecretStr(token))


def test_bearer_prefix_is_normalized():
    assert (
        Settings(token=SecretStr("Bearer synthetic-token")).token.get_secret_value()
        == "synthetic-token"
    )


async def test_redaction_handles_json_escaped_secret(client_factory):
    secret = 'synthetic-"quoted"-secret'
    settings = Settings(token=SecretStr(secret))
    client, _, _ = client_factory(settings)
    output = client.redact({"data": {"name": secret, "items": [secret]}})
    assert output["data"]["name"] == "[REDACTED]"
    assert output["data"]["items"] == ["[REDACTED]"]
