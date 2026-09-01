import asyncio
import json

import pytest

from biwenger_mcp.client import price_history
from biwenger_mcp.diagnostics import diagnose, enabled_tools
from biwenger_mcp.errors import BiwengerError


async def test_public_context_validates_sofascore_and_season(client_factory):
    client, requests, _ = client_factory()
    result = await client.get_context()
    assert result["data"]["score_id"] == 2
    assert result["data"]["season"]["slug"] == "2026-2027"
    assert result["data"]["connection"] == "public_only"
    assert all("authorization" not in request.headers for request in requests)


async def test_search_accents_filters_and_unknown_price(client_factory):
    client, _, _ = client_factory()
    result = await client.search_players("alvaro", position=2, max_price=1100000)
    assert result["data"]["total"] == 1
    player = result["data"]["players"][0]
    assert player["team"]["name"] == "Club Sintético"
    assert player["fitness"] == [7, "injured", None]
    unknown = await client.search_players("beta")
    assert unknown["data"]["players"][0]["price"] is None
    assert (await client.search_players(max_price=1000000))["data"]["total"] == 1


async def test_detail_chooses_score_2_and_orders_dates(client_factory):
    client, _, _ = client_factory()
    result = await client.get_player(101)
    assert result["data"]["recent_reports"][0]["sofascore_points"] == 7
    assert result["data"]["recent_reports"][0]["points"] == 7
    assert [row["date"] for row in result["data"]["price_history"]] == ["2026-08-29", "2026-08-30"]


async def test_scalar_points_without_score_confirmation_remain_unknown(client_factory):
    client, _, _ = client_factory(mutate=lambda d: d["player"]["reports"][0].update(points=9))
    assert (await client.get_player(101))["data"]["recent_reports"][0]["sofascore_points"] is None


async def test_private_reads_have_correct_context_and_no_writes(client_factory, settings):
    client, requests, _ = client_factory(settings)
    team, budget, market, offers = await asyncio.gather(
        client.get_my_team(), client.get_budget(), client.get_market(), client.get_received_offers()
    )
    assert team["data"]["players"][1] == {
        "id": 999,
        "name": None,
        "catalog_status": "not_found",
        "purchase_price": None,
        "acquired_at": None,
    }
    assert team["data"]["lineup"]["player_ids"] == [101, None, 0]
    assert budget["data"]["balance"] == 5000000
    assert budget["data"]["maximum_bid"] == 7500000
    assert market["data"]["total"] == 1
    assert offers["data"]["offers"][0]["players"][1]["id"] == 102
    assert offers["data"]["offers"][1]["players"] == []
    assert all(request.method == "GET" for request in requests)
    private = [request for request in requests if request.url.host == "biwenger.as.com"]
    assert all(
        request.headers["x-league"] == "9001" and request.headers["x-user"] == "8001"
        for request in private
    )
    assert len([request for request in requests if request.url.path == "/api/v2/market"]) == 1


async def test_market_sale_without_seller_remains_unknown(client_factory, settings):
    def remove_seller(data):
        data["market"]["sales"][0]["user"] = None

    client, _, _ = client_factory(settings, mutate=remove_seller)
    market = await client.get_market()
    assert market["data"]["total"] == 1
    assert market["data"]["sales"][0]["seller"] is None


@pytest.mark.parametrize("field,value", [("id", 9002), ("scoreID", 5), ("mode", "fantasy")])
async def test_reject_other_league_score_or_mode(client_factory, settings, field, value):
    client, requests, _ = client_factory(
        settings, mutate=lambda d: d["home"]["league"].update({field: value})
    )
    with pytest.raises(BiwengerError) as error:
        await client.get_budget()
    assert error.value.code == "context_mismatch"
    assert not any(request.url.path == "/api/v2/market" for request in requests)


async def test_reject_user_context_and_wrong_team(client_factory, settings):
    client, _, _ = client_factory(settings, mutate=lambda d: d["home"]["user"].update(id=8002))
    with pytest.raises(BiwengerError) as error:
        await client.get_my_team()
    assert error.value.code == "context_mismatch"
    client, _, _ = client_factory(settings, mutate=lambda d: d["user"].update(id=8002))
    with pytest.raises(BiwengerError) as error:
        await client.get_my_team()
    assert error.value.code == "context_mismatch"


async def test_missing_league_settings_require_explicit_local_confirmation(
    client_factory, settings
):
    def remove(d):
        d["home"]["league"].pop("scoreID")
        d["home"]["league"].pop("mode")

    client, _, _ = client_factory(settings, mutate=remove)
    with pytest.raises(BiwengerError) as error:
        await client.get_budget()
    assert error.value.code == "settings_confirmation_required"
    confirmed = settings.model_copy(update={"league_settings_confirmed": True})
    client, _, _ = client_factory(confirmed, mutate=remove)
    context = (await client.get_context())["data"]["private_context"]
    assert context["verification"]["score"] == "operator_confirmed"
    assert context["verification"]["identity"] == "api"


async def test_next_round_unknown_and_unsorted_events(client_factory, settings):
    client, _, _ = client_factory(settings)
    assert (await client.get_next_round())["data"]["next_round"] is None
    events = [
        {"type": "roundStart", "date": 2000001000},
        {"type": "roundStart", "date": 100},
        {"type": "roundStart", "date": 2000000000},
    ]
    client, _, _ = client_factory(settings, mutate=lambda d: d["home"].update(events=events))
    assert (await client.get_next_round())["data"]["next_round"]["starts_at"].startswith(
        "2033-05-18T03:33:20"
    )


async def test_evolution_does_not_mix_unconfirmed_points(client_factory):
    client, _, _ = client_factory()
    result = await client.get_market_evolution(days=1)
    assert result["data"]["values"][0]["date"] == "2026-08-30"
    assert "points" not in result["data"]["rising"][0]


@pytest.mark.parametrize(
    "change",
    [
        lambda d: d["catalog"].update(scoreID=5),
        lambda d: d["catalog"].update(slug="premier-league"),
        lambda d: d["catalog"]["scores"][0].update(name="AS"),
    ],
)
async def test_catalog_must_match_expected_competition_and_score(client_factory, change):
    client, _, _ = client_factory(mutate=change)
    with pytest.raises(BiwengerError) as error:
        await client.search_players()
    assert error.value.code == "context_mismatch"


@pytest.mark.parametrize(
    "score_id,score_name",
    [
        (1, "Diario AS"),
        (2, "SofaScore"),
        (3, "Estadísticas"),
        (5, "Media AS y SofaScore"),
        (6, "Biwenger Social"),
        (7, "Feeberse Score"),
        (8, "Media AS y Feeberse"),
    ],
)
async def test_catalog_and_reports_follow_active_standard_score(
    client_factory, settings, score_id, score_name
):
    def change(data):
        data["catalog"]["scoreID"] = score_id
        data["catalog"]["scores"] = [{"id": score_id, "name": score_name}]
        data["home"]["league"]["scoreID"] = score_id
        data["player"]["scoreID"] = score_id
        data["player"]["reports"][0]["points"] = {str(score_id): 11, "99": 99}

    configured = settings.model_copy(update={"score_id": score_id})
    client, requests, _ = client_factory(configured, mutate=change)
    result = await client.get_player(101)
    assert result["meta"]["score_id"] == score_id
    assert result["meta"]["score_name"] == score_name
    assert result["data"]["recent_reports"][0]["points"] == 11
    assert any(request.url.params.get("score") == str(score_id) for request in requests)


async def test_missing_balance_is_not_zero(client_factory, settings):
    client, _, _ = client_factory(settings, mutate=lambda d: d["market"]["status"].pop("balance"))
    with pytest.raises(BiwengerError) as error:
        await client.get_budget()
    assert error.value.code == "schema_changed"


async def test_schema_errors_and_unknown_player_do_not_return_success(client_factory):
    client, _, _ = client_factory(mutate=lambda d: d["catalog"].pop("players"))
    with pytest.raises(BiwengerError) as error:
        await client.search_players()
    assert error.value.code == "schema_changed"
    client, _, _ = client_factory()
    with pytest.raises(BiwengerError) as error:
        await client.get_player(99999)
    assert error.value.code == "player_not_found"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"limit": 101},
        {"limit": 0},
        {"offset": -1},
        {"max_price": -1},
        {"query": "x" * 101},
        {"position": 9},
    ],
)
async def test_invalid_arguments_are_rejected_before_network(client_factory, kwargs):
    client, requests, _ = client_factory()
    with pytest.raises(BiwengerError):
        await client.search_players(**kwargs)
    assert requests == []


async def test_diagnostics_public_flag_never_uses_credentials(client_factory, settings):
    client, requests, _ = client_factory(settings)
    report = await diagnose(client, public_only=True)
    assert all(request.url.host == "cf.biwenger.com" for request in requests)
    assert enabled_tools(report) == {
        "get_context",
        "get_player",
        "search_players",
        "get_market_evolution",
    }
    assert "synthetic-secret" not in json.dumps(report)


async def test_failed_capability_is_not_enabled(client_factory):
    client, _, _ = client_factory(mutate=lambda d: d["player"].update(id=888))
    report = await diagnose(client)
    assert "get_player" not in enabled_tools(report)
    assert "search_players" in enabled_tools(report)


def test_price_history_rejects_ambiguous_layout():
    with pytest.raises(BiwengerError):
        price_history([[260830]], 1)
    with pytest.raises(BiwengerError):
        price_history([[1234567890, 10]], 1)
