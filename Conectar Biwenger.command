#!/bin/zsh
set -eu

BIWENGER_PROJECT_DIR="${0:A:h}"
cd -- "$BIWENGER_PROJECT_DIR"

if [[ ! -x .venv/bin/biwenger ]]; then
  if command -v uv >/dev/null 2>&1; then
    uv sync --frozen
  elif [[ -x /opt/homebrew/bin/uv ]]; then
    /opt/homebrew/bin/uv sync --frozen
  else
    print 'No se encuentra uv. Consulta README.md para instalar las dependencias.'
    read '?Pulsa Intro para cerrar.'
    exit 1
  fi
fi

if .venv/bin/biwenger configure; then
  if .venv/bin/biwenger diagnose --report docs/VALIDATION.md; then
    print 'Diagnóstico terminado. Revisa los estados y compara con la aplicación de Biwenger.'
    print 'Reinicia la conexión MCP de Codex para cargar las herramientas verificadas.'
  else
    print 'Hay consultas pendientes o fallidas. Consulta docs/VALIDATION.md; no se ha cambiado tu equipo.'
  fi
else
  print 'La configuración no se ha completado.'
fi
read '?Pulsa Intro para cerrar.'
