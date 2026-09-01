import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_manifest_is_uv_macos_and_declares_no_credentials():
    manifest = json.loads((ROOT / "mcpb" / "manifest.json").read_text())
    assert manifest["manifest_version"] == "0.4"
    assert manifest["server"]["type"] == "uv"
    assert manifest["server"]["entry_point"] == "mcpb_server.py"
    assert manifest["server"]["mcp_config"]["command"] == "uv"
    assert manifest["compatibility"]["platforms"] == ["darwin"]
    assert manifest["license"] == "MIT"
    assert "user_config" not in manifest
    serialized = json.dumps(manifest).lower()
    assert "password" not in serialized and "authorization" not in serialized


def test_manifest_has_only_read_sports_tools_and_local_session_management():
    manifest = json.loads((ROOT / "mcpb" / "manifest.json").read_text())
    names = {tool["name"] for tool in manifest["tools"]}
    assert {"connect_biwenger", "disconnect_biwenger"} <= names
    assert {
        "get_context",
        "get_my_team",
        "get_budget",
        "get_market",
        "get_received_offers",
        "search_players",
        "get_player",
        "get_next_round",
        "get_market_evolution",
    } <= names
    forbidden = {"place_offer", "sell_player", "accept_offer", "set_lineup"}
    assert not names & forbidden


def test_builder_uses_closed_file_list_and_excludes_private_paths():
    source = (ROOT / "scripts" / "build_mcpb.py").read_text()
    assert "EXACT_FILES" in source
    for forbidden in (".local/session.json", "tests/", ".venv/", ".env"):
        assert forbidden not in source
