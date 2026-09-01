# Biwenger MCP

MCP local y no oficial para consultar una liga de **LaLiga en modo Clásica** desde Claude Desktop o Codex. Lee plantilla, alineación, presupuesto, mercado, ofertas, jugadores y próxima jornada. No contiene herramientas para pujar, comprar, vender, aceptar ofertas ni cambiar la alineación.

> Estado: beta privada. Los endpoints de Biwenger no forman parte de una API pública estable y pueden cambiar. Revisa las condiciones de uso antes de distribuir el proyecto.

## Instalación sencilla en Claude Desktop

La extensión `biwenger-mcp-0.2.0.mcpb` usa el runtime `uv` administrado por Claude Desktop. En macOS no hace falta instalar Python ni abrir una terminal.

1. Descarga el `.mcpb` y su archivo `.sha256`.
2. Abre **Claude Desktop → Settings → Extensions → Advanced settings → Install Extension**.
3. Instala el archivo y pide a Claude que ejecute `connect_biwenger`.
4. Introduce en la página local tu correo y la **contraseña propia de Biwenger**.
5. Elige una liga compatible y reinicia la extensión.
6. Ejecuta `get_context` y comprueba que liga y puntuación sean correctas.

Las cuentas creadas con Google pueden establecer una contraseña propia mediante la [recuperación oficial de Biwenger](https://www.biwenger.com/faq/cuentas-contrasenas-combinar-cuentas/). Nunca introduzcas la contraseña de Google en esta extensión.

Consulta la [guía detallada](docs/INSTALL_CLAUDE.md), la [política de privacidad](docs/PRIVACY.md) y el [modelo de amenazas](docs/THREAT_MODEL.md).

## Qué sistemas admite

La liga debe pertenecer a LaLiga, usar modo Clásica y una puntuación estándar:

| `scoreID` | Sistema |
|---:|---|
| 1 | Diario AS |
| 2 | SofaScore |
| 3 | Estadísticas |
| 5 | Media AS y SofaScore |
| 6 | Biwenger Social |
| 7 | Feeberse Score |
| 8 | Media AS y Feeberse |

Se rechazan las puntuaciones personalizadas, otros modos y otras competiciones. Cada respuesta identifica el `scoreID`, el nombre del sistema y cuándo se obtuvieron sus fuentes.

## Herramientas

| Herramienta | Función |
|---|---|
| `connect_biwenger` | Abre el asistente local para conectar o renovar la sesión. |
| `disconnect_biwenger` | Abre una confirmación local para eliminar la sesión. |
| `get_context` | Liga, competición, temporada, puntuación y conexión. |
| `get_my_team` | Plantilla enriquecida y alineación visible. |
| `get_budget` | Saldo y puja máxima. |
| `get_market` | Jugadores disponibles, precios y vendedores visibles. |
| `get_received_offers` | Ofertas recibidas, sin aceptarlas. |
| `search_players` | Búsqueda paginada por nombre, posición y precio. |
| `get_player` | Ficha, partidos recientes, noticias e histórico de precios. |
| `get_next_round` | Próximo inicio de jornada que Biwenger proporcione. |
| `get_market_evolution` | Evolución global del mercado de LaLiga. |

Al arrancar se ejecuta un diagnóstico acotado. Solo se registran las consultas deportivas cuyo contrato se haya verificado; conexión y desconexión siempre están disponibles. Tras conectar por primera vez hay que reiniciar la extensión para repetir ese diagnóstico con la sesión nueva.

## Seguridad y datos

- El asistente escucha solo en `127.0.0.1`, usa nonce, caduca en diez minutos, limita los cuerpos y no registra credenciales.
- La contraseña se usa exclusivamente para `POST /api/v2/auth/login` y se descarta después.
- El token se guarda en el llavero de macOS. El archivo de preferencias no contiene secretos.
- El transporte deportivo permite únicamente `GET` contra hosts y rutas cerradas.
- No se siguen redirecciones ni proxies del entorno y se limitan tiempos, reintentos y tamaños de respuesta.
- Los campos ausentes se devuelven como desconocidos; no se convierten en cero.
- Nombres, noticias y textos de terceros se tratan como datos no fiables.

El [diagrama del flujo de datos](docs/ARCHITECTURE.md) explica los límites entre Claude, el proceso local, el llavero y Biwenger.

## Desarrollo

Requiere `uv` para trabajar desde el repositorio:

```bash
uv sync --all-groups
uv run pytest
uv run ruff check src tests scripts mcpb_server.py
```

Consultas desde terminal:

```bash
uv run biwenger connect
uv run biwenger diagnose
uv run biwenger query get_context
uv run biwenger query search_players --arguments '{"query":"Álvaro","limit":5}'
```

Para una instalación nueva, `connect` usa el llavero y guarda preferencias en:

```text
~/Library/Application Support/Biwenger MCP/settings.json
```

### Compatibilidad con la sesión antigua de Codex

Un archivo `.local/session.json` ya existente no se migra ni se borra. Solo se carga cuando se pasa explícitamente:

```bash
uv run biwenger --config .local/session.json diagnose
uv run biwenger --config .local/session.json serve
```

Ese modo conserva el comportamiento anterior y su token en archivo con permisos `600`. No publiques `.local/`.

## Construir el MCPB

Instala la herramienta oficial y ejecuta el constructor cerrado:

```bash
npm install -g @anthropic-ai/mcpb
uv run python scripts/build_mcpb.py
```

El script:

1. copia a una carpeta temporal solo el manifiesto, código, lockfile, icono, licencia y documentación pública permitidos;
2. valida y empaqueta con MCPB;
3. compara todos los miembros del ZIP con la lista esperada;
4. firma el artefacto con un certificado autocreado de pruebas;
5. verifica la firma y genera el SHA-256.

La salida queda en `dist/`, que no se versiona. Para una release pública debe usarse una firma de distribución y adjuntar también [las notas de versión](docs/RELEASE_NOTES_0.2.0.md).

## Validación real

Antes de considerar estable una versión:

- compara liga, puntuación y temporada con Biwenger;
- compara plantilla y alineación;
- compara saldo y puja máxima;
- compara jugadores y precios del mercado;
- prueba sesión caducada, reconexión y desconexión;
- instala el `.mcpb` en un perfil limpio de Claude Desktop;
- revisa seguridad, privacidad y condiciones vigentes del servicio.

Las pruebas automatizadas usan respuestas sintéticas anonimizadas. No sustituyen esta comparación manual.

## Próxima entrega

El análisis de rivales añadirá `get_league_standings`, `list_league_members` y `get_league_team(member_id)`. Validará que el participante pertenezca a la liga y no devolverá correo, saldo, dispositivos ni otros datos de cuenta. La alineación rival seguirá siendo desconocida cuando Biwenger no la proporcione.

## Licencia y atribución

[MIT](LICENSE). Proyecto no afiliado, patrocinado ni respaldado por Biwenger o Diario AS. “Biwenger” y las marcas relacionadas pertenecen a sus titulares.
