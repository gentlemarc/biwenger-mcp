# Biwenger MCP

**Un asistente para consultar tu equipo de Biwenger desde Codex, sin modificarlo.**

Cliente Python y servidor MCP local para **LaLiga Clásica con puntuación exclusivamente SofaScore**.
Codex puede consultar estos datos y ayudarte a decidir. Este proyecto no contiene pujas, ventas,
aceptación de ofertas, cambios de alineación, publicación de mensajes ni un agente autónomo.

## Estado actual

Las consultas públicas al catálogo, fichas de jugadores y evolución del mercado están comprobadas
contra Biwenger. La integración MCP se prueba tanto en memoria como mediante un proceso `stdio` real.
El último diagnóstico disponible, del **30 de agosto de 2026**, también valida las consultas privadas
de contexto, plantilla y próxima jornada. **Saldo, mercado y ofertas necesitan adaptar el formato de
respuesta de Biwenger** y permanecen deshabilitados cuando fallan esa validación.

| Capacidad | Estado del último diagnóstico |
|---|---|
| Catálogo, búsqueda y ficha de jugadores | Verificada en vivo |
| Evolución del mercado global | Verificada en vivo |
| Contexto de liga, plantilla y próxima jornada | Verificada en vivo con una sesión configurada |
| Saldo, mercado de la liga y ofertas recibidas | Pendiente: `schema_changed` |
| Pujas, ventas y cambios de alineación | No implementados; fuera de alcance |

El proyecto incluye **73 pruebas automáticas**. Los tests privados usan datos sintéticos;
cada instalación requiere configurar su propia sesión y contrastar los datos con la app.

Consulta [la matriz de validación](docs/VALIDATION.md) y [los contratos observados](docs/API.md).
No se guardan códigos de invitación ni se realizan acciones para unirse a una liga.

## Inicio rápido

Requisitos: **Python 3.12 o superior** y [uv](https://docs.astral.sh/uv/getting-started/installation/).
Clona el repositorio con una cuenta que tenga acceso y abre su carpeta en el terminal:

```sh
git clone https://github.com/gentlemarc/biwenger-mcp.git
cd biwenger-mcp
uv sync --frozen
uv run --frozen biwenger diagnose --public
uv run --frozen biwenger query search_players --arguments '{"query":"Catena","limit":5}'
```

También puedes ejecutar directamente `.venv/bin/biwenger` tras instalar las dependencias.
No necesitas Docker, MongoDB, servidor público ni una clave de OpenAI para este MCP: no realiza llamadas a modelos.
`uv.lock` fija las versiones transitivas. El SDK utilizado es el oficial `mcp==2.1.1`.

## Conectar tu cuenta sin compartir el token

En macOS también puedes abrir **Conectar Biwenger.command** con Terminal: guía la configuración y
ejecuta el diagnóstico. Si el sistema te pregunta con qué aplicación abrirlo, selecciona Terminal.

1. Abre la web de Biwenger e inicia sesión tú mismo.
2. Selecciona tu liga actual y comprueba que es **LaLiga, Clásica, solo SofaScore**, no la media AS/SofaScore.
3. Abre las herramientas de desarrollador del navegador y la pestaña **Red / Network**.
4. Visita Inicio, Equipo o Mercado. Selecciona una consulta a `api/v2/home`, `api/v2/user` o `api/v2/market`.
5. En **Request headers**, localiza `Authorization`, `x-league`, `x-user` y, si aparece, `x-version`.
6. Ejecuta en un terminal local:

```sh
uv run --frozen biwenger configure
```

Pega el token solo cuando el terminal lo solicite: **no se muestra al escribir**. Se admite el prefijo `Bearer`.
Introduce los IDs numéricos de `x-league` y `x-user`; el código de invitación de la liga no los sustituye.
Si no encuentras las cabeceras, selecciona la petición GET a `/api/v2/home` y abre **Preview / Vista previa**:
`data → league → id` es el ID de liga, y `data → user → id` es el ID de usuario dentro de esa liga.
Comprueba que `data → league → name` corresponde a la liga seleccionada. Si `x-version` no aparece, pulsa Enter.
No pegues un cURL completo, un HAR, el token o la contraseña en el chat. No exportes todas las cookies del navegador.

La sesión se guarda en `.local/session.json` con permisos `600`, dentro de una carpeta `700`, excluida de Git.
El token se guarda localmente en texto claro protegido por permisos, **no cifrado**: no compartas ni subas `.local/`.
No se guarda la contraseña. `--config RUTA` o `BIWENGER_CONFIG` permiten elegir otra ruta privada.

Si la API omite la puntuación o el modo de liga, se usa tu confirmación explícita de esos ajustes al configurar
la sesión, y el resultado lo identifica como `operator_confirmed`, nunca como una verificación de la API.
Una contradicción explícita de competición, puntuación, modo o identidad bloquea las consultas privadas.

Después:

```sh
uv run --frozen biwenger diagnose --report docs/VALIDATION.md
```

El diagnóstico ejecuta solo GET y guarda únicamente estado, campos y advertencias, sin respuestas privadas completas.
`--public` garantiza que no se consultan endpoints privados, incluso si hay una sesión configurada.

## Usarlo en Codex

La configuración se obtiene sin mostrar credenciales:

```sh
uv run --frozen biwenger codex-config
```

Añade el bloque resultante a la configuración MCP de Codex, conservando las demás entradas. Si esta entrega
ya está registrada como `biwenger`, no la añadas de nuevo. El proceso arranca con un comando local `stdio`,
sin escuchar en ningún puerto. Se configuran 60 segundos para arranque y llamadas.

Al iniciar, el servidor valida las operaciones y **solo registra las que funcionaron**; `get_context` siempre
está disponible como diagnóstico. Sin sesión privada aparecerán normalmente cuatro herramientas.
Después de configurar o renovar la sesión, reinicia la conexión MCP o vuelve a abrir Codex para repetir esa validación.
Si el servicio no responde al arrancar, puede quedar solo `get_context`; reinicia la conexión cuando se recupere.

Ejemplos de preguntas una vez conectada y verificada la sesión:

- «Consulta mi equipo y dime qué posiciones tengo peor cubiertas. Señala los datos que falten».
- «¿Cuál es mi saldo y mi puja máxima? No hagas ninguna operación».
- «Compara jugadores del mercado que entren en mi presupuesto, usando sus puntos SofaScore».
- «¿Cuándo comienza la próxima jornada según Biwenger?».

La decisión deportiva corresponde al asistente; el MCP aporta datos, no predicciones de titularidad garantizadas.
Los textos y noticias recibidos son datos de terceros y no deben interpretarse como instrucciones.

## Herramientas

| Nombre | Entradas | Resultado |
|---|---|---|
| `get_context` | Ninguna | Contexto, temporada, verificación, capacidades y conexión |
| `search_players` | `query`, `position`, `max_price`, `limit`, `offset` | Catálogo paginado con puntos SofaScore |
| `get_player` | `player_id` | Ficha, últimos 10 partidos, 30 registros de precio y 5 noticias |
| `get_my_team` | Ninguna | Plantilla y alineación actual |
| `get_budget` | Ninguna | Saldo y puja máxima, por separado |
| `get_market` | `max_price`, `limit`, `offset` | Ventas ajenas ordenadas por precio solicitado |
| `get_received_offers` | `limit`, `offset` | Ofertas recibidas; admite cero o varios jugadores |
| `get_next_round` | Ninguna | Próximo evento `roundStart` futuro, o desconocido |
| `get_market_evolution` | `days` entre 1 y 366 | Histórico global y cambios de precio, no de tu plantilla |

`limit` admite 1–100; `offset`, 0–10000. Las posiciones siguen la codificación del catálogo:
1 portero, 2 defensa, 3 centrocampista, 4 delantero, 5 entrenador. Los importes se mantienen como enteros
según la API y se acompañan de su moneda; hay que contrastar las cantidades privadas con la app.

Cada resultado incluye fuentes, instante de obtención UTC, TTL y advertencias. La caché es de 60 segundos
y solo vive en memoria; el token de la sesión se carga al arrancar. Los datos ausentes son `null`, no cero.
Las fechas de próximos eventos se devuelven en UTC; conviértelas a Europe/Madrid al interpretarlas.
Las fechas del histórico de precios llegan como `YYMMDD` y se devuelven como `YYYY-MM-DD`.

## Verificación de la liga en la aplicación

Antes de dar por conectada y validada tu cuenta, comprueba:

- [ ] `get_context` muestra tu liga y usuario correctos, LaLiga y SofaScore exclusivo.
- [ ] La temporada del catálogo corresponde a la temporada que estás jugando; es información pública,
      no una comprobación independiente de la temporada de la liga privada.
- [ ] `get_my_team` coincide con la plantilla y alineación visibles en Biwenger.
- [ ] Saldo y puja máxima coinciden exactamente, incluidas unidades y posibles cantidades negativas.
- [ ] Mercado: jugador, vendedor y **precio solicitado** coinciden; no confundirlo con valor de mercado.
- [ ] Las ofertas coinciden, o la app confirma que actualmente no tienes ninguna.
- [ ] El comienzo de jornada coincide, teniendo en cuenta la zona horaria; no se inventa si falta.
- [ ] Desde Codex se puede llamar a las herramientas privadas después de reiniciar la conexión.

## Pruebas y mantenimiento

```sh
uv run --frozen pytest -q
uv run --frozen ruff check src tests scripts
uv run --frozen python scripts/smoke_stdio.py
```

`pytest` no necesita red ni cuenta real. El último comando sí consulta Biwenger, siempre en modo público,
y comprueba descubrimiento MCP, las cuatro herramientas públicas y rechazo de una herramienta de pujas inexistente.

Protecciones: lista cerrada de endpoints, únicamente GET, validación de slugs, ausencia de redirecciones,
credenciales solo para `biwenger.as.com`, sin proxies implícitos, tamaño de respuesta máximo 8 MiB,
15 segundos por petición, hasta dos reintentos adicionales en fallos transitorios y respeto de `Retry-After`.
No se reintenta automáticamente un 401/403 ni se intenta superar CAPTCHA o bloqueos de acceso.
Los errores nunca devuelven el cuerpo HTTP, excepciones del proveedor o credenciales. No hay logs de cuerpos.

Ante `auth_required`, repite `configure`; ante `context_mismatch`, revisa liga, usuario y puntuación.
Ante `schema_changed`, no confíes en resultados de esa operación: hay que adaptar su contrato y repetir pruebas.
La API de la web puede cambiar sin aviso; el proyecto original no constituye un contrato oficial de estabilidad.

## Estructura

```text
src/biwenger_mcp/       Cliente HTTP, modelos, configuración, diagnóstico y servidor MCP
tests/                 Pruebas offline con datos sintéticos
scripts/               Prueba stdio y registro opcional en Codex
docs/                  Contratos observados, validación y comprobaciones
Conectar Biwenger.command  Configurador interactivo para macOS
pyproject.toml          Paquete Python y comandos
uv.lock                Versiones fijadas de las dependencias
```

## Próximos pasos

- Adaptar y verificar los contratos de saldo, mercado de liga y ofertas recibidas.
- Completar la comparación de datos privados con la aplicación.
- Probar el asesoramiento desde Codex con esas capacidades verificadas.
- Diseñar después un agente independiente; la autonomía y las operaciones de escritura requieren otra fase.

## Procedencia y alcance

Implementación nueva, usando como referencia el mapa de llamadas de
[pablopb3/biwenger-api](https://github.com/pablopb3/biwenger-api), revisión `1b5172c622ba868a832576822ce6d2071f9c1349`.
No se ejecuta su servidor Go, sus scripts, su función de Twitter ni sus ejemplos de escritura.
El SDK es [modelcontextprotocol/python-sdk](https://github.com/modelcontextprotocol/python-sdk).
La conexión local está descrita en la [documentación de MCP de OpenAI](https://developers.openai.com/codex/mcp/).

Uso personal sobre tu propia sesión y datos a los que ya tienes acceso. Respeta las condiciones y límites de Biwenger.
Quedan fuera de esta versión: multiliga, otros sistemas de puntuación, escritura, despliegue remoto,
memoria histórica persistente, automatizaciones y agente autónomo.
