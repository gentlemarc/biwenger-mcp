"""Entrada local para configuración, diagnóstico, consultas y MCP."""

from __future__ import annotations

import argparse
import asyncio
import getpass
import json
import logging
import sys
import warnings
from pathlib import Path

from pydantic import SecretStr, ValidationError

from .client import BiwengerClient
from .config import Settings, default_config_path, load_settings, project_root, save_settings
from .diagnostics import OPERATIONS, diagnose, markdown_report
from .errors import BiwengerError


def configure(path: Path) -> None:
    if not sys.stdin.isatty():
        raise BiwengerError(
            "terminal_required",
            "Ejecuta configure en un terminal interactivo. No pegues credenciales en el chat.",
        )
    print("Configuración local de Biwenger. No se enviarán cambios a tu equipo.")
    print(
        "En la web de Biwenger: Herramientas de desarrollador > Red > una consulta home, user o market."
    )
    print(
        "Copia Authorization, x-league, x-user y, si aparece, x-version. No uses el código de invitación."
    )
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        token = getpass.getpass("Token Authorization (oculto; admite prefijo Bearer): ")
    try:
        league_id = int(input("x-league (ID numérico de tu liga actual): ").strip())
        user_id = int(input("x-user (ID numérico de tu usuario en esa liga): ").strip())
    except ValueError:
        raise BiwengerError(
            "invalid_config",
            "Los IDs deben ser numéricos; el código de invitación no sirve como ID.",
        ) from None
    version = input("x-version (opcional, Enter si no aparece): ").strip() or None
    confirmed = input(
        "¿Has comprobado en la app LaLiga, modo Clásica y SOLO SofaScore? [sí/no]: "
    ).strip().casefold() in {"sí", "si", "s", "yes"}
    settings = Settings(
        token=SecretStr(token),
        league_id=league_id,
        user_id=user_id,
        client_version=version,
        league_settings_confirmed=confirmed,
    )
    save_settings(settings, path)
    print("Sesión guardada con permisos 600. El token no se mostrará ni se guardará en Git.")
    print(
        "Ejecuta biwenger diagnose para verificar las consultas privadas y reinicia la conexión MCP."
    )


async def run_command(args, settings: Settings) -> int:
    client = BiwengerClient(settings)
    try:
        if args.command == "serve":
            from .server import serve

            await serve(client)
            return 0
        if args.command == "diagnose":
            report = await diagnose(client, public_only=args.public)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            if args.report:
                destination = Path(args.report)
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(markdown_report(report))
            return (
                1
                if any(row["status"] == "failed" for row in report["capabilities"].values())
                else 0
            )
        if args.command == "query":
            arguments = json.loads(args.arguments)
            if not isinstance(arguments, dict):
                raise BiwengerError("invalid_argument", "Los argumentos deben ser un objeto JSON.")
            try:
                result = await getattr(client, args.tool)(**arguments)
            except TypeError:
                raise BiwengerError(
                    "invalid_argument", "Argumentos no válidos para esta consulta."
                ) from None
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        return 0
    finally:
        await client.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Biwenger de solo lectura: cliente local y MCP stdio."
    )
    parser.add_argument(
        "--config", type=Path, default=default_config_path(), help="Archivo privado local de sesión"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("configure", help="Introduce la sesión en un terminal con token oculto")
    sub.add_parser("serve", help="Inicia el MCP stdio, habilitando solo consultas verificadas")
    diagnostic = sub.add_parser(
        "diagnose", help="Verifica endpoints sin guardar respuestas privadas"
    )
    diagnostic.add_argument("--public", action="store_true", help="No consulta endpoints privados")
    diagnostic.add_argument(
        "--report", help="Escribe una matriz Markdown sin credenciales ni datos de la cuenta"
    )
    query = sub.add_parser("query", help="Ejecuta una consulta de lectura")
    query.add_argument("tool", choices=list(OPERATIONS))
    query.add_argument("--arguments", default="{}", help="Argumentos JSON sin credenciales")
    sub.add_parser("codex-config", help="Muestra la configuración MCP sin incluir el token")
    args = parser.parse_args()
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    try:
        if args.command == "configure":
            configure(args.config)
            return 0
        if args.command == "codex-config":
            executable = project_root() / ".venv" / "bin" / "biwenger"
            print("[mcp_servers.biwenger]")
            print("command = " + json.dumps(str(executable)))
            print("args = " + json.dumps(["--config", str(args.config.resolve()), "serve"]))
            print("startup_timeout_sec = 60\ntool_timeout_sec = 60")
            return 0
        return asyncio.run(run_command(args, load_settings(args.config)))
    except BiwengerError as error:
        print(json.dumps({"error": error.public()}, ensure_ascii=False), file=sys.stderr)
        return 1
    except (ValidationError, ValueError, getpass.GetPassWarning):
        print(
            "Configuración o argumentos no válidos. No se muestran valores sensibles.",
            file=sys.stderr,
        )
        return 1
    except (KeyboardInterrupt, EOFError):
        print("Operación cancelada.", file=sys.stderr)
        return 130
    except Exception:
        print(
            "No se pudo completar la operación. Revisa la configuración y ejecuta el diagnóstico.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
