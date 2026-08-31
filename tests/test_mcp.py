import json

from mcp import Client

from biwenger_mcp.diagnostics import diagnose
from biwenger_mcp.server import build_server


async def test_mcp_handshake_discovery_and_structured_call(client_factory):
    client, _, _ = client_factory()
    server = build_server(client, await diagnose(client))
    async with Client(server) as mcp:
        tools = (await mcp.list_tools()).tools
        assert {tool.name for tool in tools} == {
            "get_context",
            "search_players",
            "get_player",
            "get_market_evolution",
        }
        for tool in tools:
            assert tool.annotations.read_only_hint is True
            assert tool.annotations.destructive_hint is False
            schema = json.dumps(tool.input_schema)
            assert "token" not in schema and "password" not in schema
        result = await mcp.call_tool("search_players", {"query": "alvaro"})
        assert not result.is_error
        assert result.structured_content["data"]["total"] == 1


async def test_mcp_enables_private_tools_only_after_verification(client_factory, settings):
    client, requests, _ = client_factory(settings)
    server = build_server(client, await diagnose(client))
    async with Client(server) as mcp:
        names = {tool.name for tool in (await mcp.list_tools()).tools}
        assert "get_budget" in names and len(names) == 9
        result = await mcp.call_tool("get_budget")
        assert result.structured_content["data"]["balance"] == 5000000
        before = len(requests)
        rejected = await mcp.call_tool("place_offer", {"amount": 1})
        assert rejected.is_error
        assert len(requests) == before


async def test_mcp_error_flag_and_unknown_field_validation(client_factory):
    client, requests, _ = client_factory()
    server = build_server(client, await diagnose(client))
    async with Client(server) as mcp:
        result = await mcp.call_tool("get_player", {"player_id": 99999})
        assert result.is_error
        assert result.structured_content["error"]["code"] == "player_not_found"
        before = len(requests)
        result = await mcp.call_tool("get_player", {"player_id": "../../offers"})
        assert result.is_error
        assert len(requests) == before


async def test_mcp_has_context_even_if_provider_unavailable(client_factory):
    client, _, _ = client_factory(mutate=lambda d: d["catalog"].pop("players"))
    server = build_server(client, await diagnose(client))
    async with Client(server) as mcp:
        result = await mcp.call_tool("get_context")
        assert result.is_error
        assert "traceback" not in json.dumps(result.model_dump()).lower()
