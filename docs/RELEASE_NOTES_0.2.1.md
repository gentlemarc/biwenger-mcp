# Biwenger MCP 0.2.1 — beta privada

Corrección del asistente de conexión para aceptar el formato actual de `/api/v2/auth/login`, que devuelve `token` en la raíz de la respuesta. Se mantiene compatibilidad con el formato histórico `data.token`.

El token continúa guardándose únicamente en el llavero de macOS. La contraseña se descarta tras el intento de acceso y no se registra.
