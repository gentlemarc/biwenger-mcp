"""Datos sintéticos; ningún ID, token o nombre procede de una cuenta real."""

import copy

import httpx
import pytest
from pydantic import SecretStr

from biwenger_mcp.client import BiwengerClient
from biwenger_mcp.config import Settings
from biwenger_mcp.transport import ReadOnlyTransport


@pytest.fixture
def payloads():
    return {
        "catalog": {
            "id": 1,
            "slug": "la-liga",
            "name": "Primera División",
            "currency": "€",
            "scoreID": 2,
            "scores": [{"id": 2, "name": "SofaScore"}, {"id": 5, "name": "Media AS y SofaScore"}],
            "season": {"id": "2027", "name": "Temporada 2026/2027", "slug": "2026-2027"},
            "players": {
                "101": {
                    "id": 101,
                    "name": "Álvaro Sintético",
                    "slug": "alvaro-sintetico",
                    "teamID": 10,
                    "position": 2,
                    "price": 1000000,
                    "priceIncrement": 20000,
                    "points": 14,
                    "fitness": [7, "injured", None],
                },
                "102": {
                    "id": 102,
                    "name": "Jugador Beta",
                    "slug": "jugador-beta",
                    "teamID": 10,
                    "position": 4,
                    "price": None,
                    "points": None,
                },
            },
            "teams": {"10": {"id": 10, "name": "Club Sintético"}},
        },
        "player": {
            "id": 101,
            "name": "Álvaro Sintético",
            "slug": "alvaro-sintetico",
            "competition": {"slug": "la-liga"},
            "reports": [
                {
                    "home": True,
                    "points": {"1": 2, "2": 7, "5": 5},
                    "match": {"id": 901, "date": 1787592600, "round": {"name": "Jornada 2"}},
                    "rawStats": {"minutesPlayed": 90},
                }
            ],
            "prices": [[260830, 1000000], [260829, 980000]],
            "news": [{"title": "Noticia sintética", "url": "https://example.com/noticia"}],
        },
        "home": {
            "league": {"id": 9001, "name": "Liga de pruebas", "mode": "classic", "scoreID": 2},
            "user": {"id": 8001, "name": "Usuario sintético"},
            "competition": "la-liga",
            "events": [],
        },
        "user": {
            "id": 8001,
            "players": [{"id": 101, "owner": {"price": 900000, "date": 1787592600}}, {"id": 999}],
            "lineup": {"type": "4-4-2", "playersID": [101, None, 0]},
            "balance": 5000000,
        },
        "market": {
            "sales": [
                {"player": {"id": 102}, "user": {"id": 0}, "price": 1200000},
                {"player": {"id": 101}, "user": {"id": 8001}, "price": 100},
            ],
            "offers": [
                {
                    "id": 401,
                    "requestedPlayers": [101, 102],
                    "amount": 2000000,
                    "from": {"id": 8002},
                },
                {"id": 402, "requestedPlayers": [], "amount": 500000, "from": {"id": 0}},
            ],
            "status": {"balance": 5000000, "maximumBid": 7500000},
        },
        "evolution": {
            "competition": {"slug": "la-liga", "currency": "€"},
            "values": [[260830, 100000000], [260829, 99000000]],
            "ups": [
                {
                    "id": 101,
                    "name": "Álvaro Sintético",
                    "price": 1000000,
                    "oldPrice": 980000,
                    "points": 123,
                }
            ],
            "downs": [],
        },
    }


@pytest.fixture
def settings():
    return Settings(
        token=SecretStr("synthetic-secret-do-not-print"),
        league_id=9001,
        user_id=8001,
        client_version="test",
        cache_seconds=60,
    )


@pytest.fixture
def client_factory(payloads):
    clients = []

    def factory(settings=None, mutate=None, handler=None):
        data = copy.deepcopy(payloads)
        if mutate:
            mutate(data)
        requests = []

        def respond(request):
            requests.append(request)
            if handler:
                return handler(request)
            path = request.url.path
            if path.endswith("/data"):
                key = "catalog"
            elif "/players/" in path:
                key = "player"
            elif "/competitions/" in path:
                key = "evolution"
            else:
                key = path.split("/")[-1]
            return httpx.Response(200, json={"status": 200, "data": data[key]})

        config = settings or Settings()
        transport = ReadOnlyTransport(
            config, http_transport=httpx.MockTransport(respond), sleep=no_sleep
        )
        client = BiwengerClient(config, transport)
        clients.append(client)
        return client, requests, data

    return factory


async def no_sleep(seconds):
    return None
