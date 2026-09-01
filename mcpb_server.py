"""Punto de entrada autocontenido para Claude Desktop MCPB."""

import asyncio
import logging

from biwenger_mcp.client import BiwengerClient
from biwenger_mcp.config import load_settings
from biwenger_mcp.server import serve


def main() -> None:
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    asyncio.run(serve(BiwengerClient(load_settings())))


if __name__ == "__main__":
    main()
