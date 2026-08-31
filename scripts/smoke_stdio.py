"""Prueba explícita en vivo del transporte MCP. No usa ni muestra datos privados."""

import asyncio
import json
from pathlib import Path

from mcp import Client
from mcp.client.stdio import StdioServerParameters


async def main():
    root = Path(__file__).resolve().parents[1]
    # A dedicated absent session ensures that this smoke test is public-only.
    config = root / ".local" / "public-smoke-no-session.json"
    if config.exists() or config.is_symlink():
        raise RuntimeError("La ruta de prueba pública debe estar vacía.")
    params = StdioServerParameters(
        command=str(root / ".venv" / "bin" / "biwenger"),
        args=["--config", str(config), "serve"],
        cwd=str(root),
    )
    async with Client(params, read_timeout_seconds=60) as client:
        tools = (await client.list_tools()).tools
        names = {tool.name for tool in tools}
        expected = {"get_context", "search_players", "get_player", "get_market_evolution"}
        assert names == expected, f"Capacidades inesperadas: {names}"
        context = await client.call_tool("get_context")
        assert not context.is_error
        data = context.structured_content["data"]
        assert data["connection"] == "public_only"
        search = await client.call_tool("search_players", {"query": "", "limit": 1})
        assert not search.is_error
        player_id = search.structured_content["data"]["players"][0]["id"]
        detail = await client.call_tool("get_player", {"player_id": player_id})
        assert not detail.is_error
        evolution = await client.call_tool("get_market_evolution", {"days": 2})
        assert not evolution.is_error
        forbidden = await client.call_tool("place_offer", {"amount": 1})
        assert forbidden.is_error
        print(
            json.dumps(
                {
                    "transport": "stdio",
                    "verified_tools": sorted(names),
                    "connection": data["connection"],
                    "season": data["season"],
                    "score_id": data["score_id"],
                    "write_tool_rejected": True,
                },
                ensure_ascii=False,
                indent=2,
            )
        )


if __name__ == "__main__":
    asyncio.run(main())
