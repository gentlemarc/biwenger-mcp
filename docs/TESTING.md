# Comprobaciones de la entrega

Comprobadas el 2026-08-30 en el Mac de desarrollo.

| Comprobación | Resultado |
|---|---|
| Instalación reproducible `uv sync --frozen` | Correcta; entorno Python 3.12 y dependencias de `uv.lock` |
| Tests offline `pytest -q` | 74 tests aprobados |
| Análisis estático `ruff check src tests scripts` | Sin errores |
| Diagnóstico público contra Biwenger | Catálogo, ficha y evolución verificados |
| MCP en memoria con cliente oficial | Inicialización, descubrimiento, resultados estructurados y errores comprobados |
| Proceso real `stdio` | Las nueve herramientas de lectura funcionan con sesión; una herramienta de pujas inexistente es rechazada |
| Registro local de Codex | `codex mcp get biwenger --json` confirma entrada habilitada, stdio y tiempos de 60 segundos |
| Sesión privada real | Contexto, plantilla, saldo, mercado, ofertas y próxima jornada verificados; las ofertas vacías se conservan como lista vacía |
| Comparación con la app de Biwenger | Pendiente |
| Llamadas privadas mediante cliente MCP `stdio` | Verificadas en un proceso real independiente |

Los tests usan exclusivamente datos sintéticos: no contienen la liga real, el código de invitación ni credenciales.
Se prueban errores 401/403/429/5xx, errores dentro de HTTP 200, JSON/HTML inválido, timeouts, caché,
IDs de liga/usuario incorrectos, otra puntuación, datos ausentes, ofertas vacías o con varios jugadores,
fechas del mercado y selección exclusiva de puntos SofaScore.

Las comprobaciones de seguridad incluyen el bloqueo de rutas no permitidas y redirecciones,
la ausencia de credenciales en peticiones públicas y errores, los permisos de la configuración,
la selección de herramientas según verificación y la conservación de otras opciones de Codex al registrar el MCP.

La prueba stdio usa un cliente MCP oficial independiente. El registro en Codex está confirmado,
pero la interfaz de esta tarea puede necesitar reiniciar la conexión para descubrir las herramientas nuevas.
No se ha afirmado que la sesión privada esté validada basándose en tests simulados.
