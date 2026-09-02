"""Pruebas en vivo seguras; ninguna respuesta privada completa se persiste."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from .client import BiwengerClient
from .errors import BiwengerError

OPERATIONS = {
    "get_context": ("catalog + home", "optional"),
    "search_players": ("catalog", "public"),
    "get_player": ("catalog + player", "public"),
    "get_market_evolution": ("evolution", "public"),
    "get_my_team": ("catalog + home + user", "private"),
    "get_budget": ("catalog + home + market", "private"),
    "get_market": ("catalog + home + market", "private"),
    "get_received_offers": ("catalog + home + market", "private"),
    "get_next_round": ("catalog + home", "private"),
}


async def diagnose(client: BiwengerClient, *, public_only: bool = False) -> dict:
    report = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "read_only": True,
        "configuration": {
            "competition": "la-liga",
            "score_id": client.settings.score_id,
            "score_name": client.settings.score_name,
            "league_mode": "league",
            "league_type": "normal",
            "market_mode": "classic",
            "session_configured": client.settings.authenticated,
        },
        "comparison_with_app": "pending_operator_check",
        "capabilities": {},
    }

    async def check(name, call):
        endpoint, auth = OPERATIONS[name]
        row = {"endpoint": endpoint, "authentication": auth, "status": "verified"}
        try:
            async with asyncio.timeout(35):
                result = await call()
            row["returned_fields"] = list(result["data"])
            row["warnings"] = result["meta"]["warnings"]
            if name == "get_context":
                data = result["data"]
                row["connection"] = data["connection"]
                row["season"] = data["season"]
                row["catalog_count"] = data["players_in_catalog"]
                if "private_error" in data:
                    row["private_error"] = data["private_error"]
            if name == "get_received_offers":
                row["empty_result"] = result["data"]["total"] == 0
        except BiwengerError as error:
            row.update(
                status="not_configured" if error.code == "not_configured" else "failed",
                error=error.public(),
            )
        except TimeoutError:
            row.update(
                status="failed",
                error={
                    "code": "diagnostic_timeout",
                    "message": "Diagnóstico agotó su tiempo máximo.",
                    "retryable": True,
                },
            )
        except Exception:
            row.update(
                status="failed",
                error={
                    "code": "unexpected_schema",
                    "message": "Respuesta no reconocida; requiere revisar el adaptador.",
                    "retryable": False,
                },
            )
        report["capabilities"][name] = row

    await check("get_context", lambda: client.get_context(include_private=not public_only))
    await check("search_players", lambda: client.search_players(limit=1))

    async def probe_player():
        catalog, _ = await client.catalog()
        candidates = sorted(player.id for player in catalog.players.values() if player.slug)
        if not candidates:
            raise BiwengerError(
                "no_probe_player", "No hay una ficha disponible para validar esta capacidad."
            )
        return await client.get_player(candidates[0])

    await check("get_player", probe_player)
    await check("get_market_evolution", lambda: client.get_market_evolution(days=1))
    for name, (_, auth) in OPERATIONS.items():
        if auth != "private":
            continue
        if public_only or not client.settings.authenticated:
            report["capabilities"][name] = {
                "endpoint": OPERATIONS[name][0],
                "authentication": auth,
                "status": "not_configured",
                "reason": "Prueba pública solicitada o sesión privada no configurada.",
            }
        elif report["capabilities"]["get_context"].get("private_error"):
            # Do not repeatedly send a token already rejected during this diagnostic.
            report["capabilities"][name] = {
                "endpoint": OPERATIONS[name][0],
                "authentication": auth,
                "status": "failed",
                "error": report["capabilities"]["get_context"]["private_error"],
            }
        else:
            await check(name, getattr(client, name))
    return report


def enabled_tools(report: dict) -> set[str]:
    return {"get_context"} | {
        name for name, row in report["capabilities"].items() if row["status"] == "verified"
    }


def markdown_report(report: dict) -> str:
    lines = [
        "# Validación de capacidades de Biwenger",
        "",
        f"Fecha de comprobación: {report['checked_at']}",
        "",
        "Solo se han ejecutado consultas GET. Los resultados privados no se guardan en este informe.",
        "",
        "| Herramienta | Endpoints | Acceso | Resultado |",
        "|---|---|---|---|",
    ]
    for name, row in report["capabilities"].items():
        status = row["status"]
        if row.get("error"):
            status += f" ({row['error']['code']})"
        endpoint = row["endpoint"]
        if name == "get_context" and row.get("connection") == "public_only":
            endpoint = "catalog (home pendiente)"
        lines.append(f"| `{name}` | {endpoint} | {row['authentication']} | {status} |")
    lines.extend(
        [
            "",
            "`verified` significa que una consulta real y la validación del contrato tuvieron éxito.",
            "`not_configured` no implica fallo de Biwenger: falta comprobar la sesión privada.",
            "La comparación de los datos de la liga con la aplicación requiere completar la lista de comprobación del README.",
            "",
        ]
    )
    return "\n".join(lines)
