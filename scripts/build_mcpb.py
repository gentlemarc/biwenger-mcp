"""Construye el MCPB desde una lista cerrada y comprueba su contenido."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import struct
import subprocess
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.2.0"
EXACT_FILES = {
    "mcpb/manifest.json": "manifest.json",
    "mcpb_server.py": "mcpb_server.py",
    "pyproject.toml": "pyproject.toml",
    "uv.lock": "uv.lock",
    ".mcpbignore": ".mcpbignore",
    "README.md": "README.md",
    "LICENSE": "LICENSE",
    "assets/icon.png": "assets/icon.png",
    "docs/PRIVACY.md": "docs/PRIVACY.md",
    "docs/THREAT_MODEL.md": "docs/THREAT_MODEL.md",
    "docs/INSTALL_CLAUDE.md": "docs/INSTALL_CLAUDE.md",
    "docs/ARCHITECTURE.md": "docs/ARCHITECTURE.md",
}


def run(command: list[str], *, cwd: Path) -> None:
    subprocess.run(command, cwd=cwd, check=True)


def verify_detached_signature(package: Path, temporary: Path) -> None:
    content = package.read_bytes()
    header = b"MCPB_SIG_V1"
    footer = b"MCPB_SIG_END"
    header_at = content.rfind(header)
    if header_at < 0 or not content.endswith(footer):
        raise SystemExit("MCPB no contiene la firma esperada.")
    length_at = header_at + len(header)
    signature_length = struct.unpack("<I", content[length_at : length_at + 4])[0]
    signature_at = length_at + 4
    signature = content[signature_at : signature_at + signature_length]
    if signature_at + signature_length != len(content) - len(footer):
        raise SystemExit("Bloque de firma MCPB inválido.")
    original = temporary / "unsigned.mcpb"
    detached = temporary / "signature.der"
    original.write_bytes(content[:header_at])
    detached.write_bytes(signature)
    run(
        [
            "/usr/bin/openssl",
            "smime",
            "-verify",
            "-inform",
            "DER",
            "-in",
            str(detached),
            "-content",
            str(original),
            "-noverify",
            "-out",
            "/dev/null",
        ],
        cwd=temporary,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mcpb-bin", default=shutil.which("mcpb") or "mcpb")
    parser.add_argument("--unsigned", action="store_true")
    args = parser.parse_args()
    output = ROOT / "dist" / f"biwenger-mcp-{VERSION}.mcpb"
    signed_output = ROOT / "dist" / f"biwenger-mcp-{VERSION}-dev-signed.mcpb"
    output.parent.mkdir(exist_ok=True)
    output.unlink(missing_ok=True)
    signed_output.unlink(missing_ok=True)
    output.with_suffix(output.suffix + ".sha256").unlink(missing_ok=True)
    signed_output.with_suffix(signed_output.suffix + ".sha256").unlink(missing_ok=True)

    with tempfile.TemporaryDirectory(prefix="biwenger-mcpb-") as temporary:
        staging = Path(temporary) / "bundle"
        for source_name, target_name in EXACT_FILES.items():
            source = ROOT / source_name
            if not source.is_file():
                raise SystemExit(f"Falta el archivo permitido: {source_name}")
            target = staging / target_name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        for source in sorted((ROOT / "src" / "biwenger_mcp").glob("*.py")):
            target = staging / source.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)

        run([args.mcpb_bin, "validate", str(staging / "manifest.json")], cwd=staging)
        run([args.mcpb_bin, "pack", str(staging), str(output)], cwd=staging)
        expected = {
            target for target in EXACT_FILES.values() if target != ".mcpbignore"
        } | {
            str(path.relative_to(ROOT))
            for path in (ROOT / "src" / "biwenger_mcp").glob("*.py")
        }
        with zipfile.ZipFile(output) as archive:
            actual = {name.rstrip("/") for name in archive.namelist() if not name.endswith("/")}
        if actual != expected:
            raise SystemExit(f"Contenido inesperado en MCPB: {sorted(actual ^ expected)}")
        if not args.unsigned:
            # Claude Desktop currently previews MCPB as a strict ZIP and rejects the
            # appended PKCS#7 block. Keep the installable artifact as a plain MCPB and
            # create a separately named signed copy for cryptographic verification.
            shutil.copy2(output, signed_output)
            run(
                [args.mcpb_bin, "sign", str(signed_output), "--self-signed"],
                cwd=Path(temporary),
            )
            verify_detached_signature(signed_output, Path(temporary))

    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    checksum = output.with_suffix(output.suffix + ".sha256")
    checksum.write_text(f"{digest}  {output.name}\n")
    print(output)
    print(checksum)
    if signed_output.exists():
        signed_digest = hashlib.sha256(signed_output.read_bytes()).hexdigest()
        signed_checksum = signed_output.with_suffix(signed_output.suffix + ".sha256")
        signed_checksum.write_text(f"{signed_digest}  {signed_output.name}\n")
        print(signed_output)
        print(signed_checksum)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
