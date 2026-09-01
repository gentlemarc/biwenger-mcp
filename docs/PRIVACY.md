# Política de privacidad de Biwenger MCP

Última actualización: 31 de agosto de 2026.

Biwenger MCP es un proyecto local, de código abierto y no oficial. No opera un servidor propio, no incluye telemetría y no recibe datos de sus usuarios. La extensión se comunica directamente desde el ordenador con `biwenger.as.com` y `cf.biwenger.com` para realizar las consultas solicitadas.

El asistente de conexión recibe temporalmente el correo y la contraseña propia de Biwenger. La contraseña se usa una sola vez contra `/api/v2/auth/login`, no se escribe en disco y se descarta después de esa petición. Nunca debe introducirse una contraseña de Google, Apple o Facebook. El token de sesión resultante se guarda en el llavero de macOS bajo el servicio `com.gentlemarc.biwenger-mcp`.

El archivo `~/Library/Application Support/Biwenger MCP/settings.json` contiene únicamente el ID interno de la liga, el ID de usuario dentro de esa liga, la competición, la puntuación, la versión de cliente y preferencias técnicas. No contiene correo, contraseña ni token. La herramienta `disconnect_biwenger` elimina el elemento del llavero y ese archivo tras una confirmación local.

Las respuestas consultadas pueden contener plantilla, alineación, saldo, puja máxima, mercado, ofertas, información pública de jugadores y nombres visibles de otros participantes cuando Biwenger los incluya. Los datos se mantienen en memoria y en una caché breve. La extensión no guarda respuestas deportivas ni cuerpos HTTP en registros.

El archivo de sesión antiguo `.local/session.json` solo se utiliza cuando una ejecución lo indica de forma explícita con `--config`. No se migra, modifica ni elimina desde el asistente nuevo.

El uso de Biwenger y el tratamiento que hace ese servicio de la cuenta se rigen por sus propios términos y ajustes de privacidad. Antes de publicar o distribuir esta extensión debe revisarse que su uso sea compatible con las condiciones vigentes de Biwenger.
