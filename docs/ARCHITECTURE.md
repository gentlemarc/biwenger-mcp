# Arquitectura y flujo de datos

```mermaid
flowchart LR
    U[Usuario] -->|correo y contraseña Biwenger| B[Navegador 127.0.0.1]
    B -->|formulario con nonce| W[Asistente local MCP]
    W -->|POST login; contraseña efímera| A[biwenger.as.com]
    A -->|token de sesión| W
    W -->|token| K[Llavero de macOS]
    W -->|liga y puntuación sin secretos| C[Application Support]
    CL[Claude Desktop o Codex] -->|herramientas MCP stdio| M[Servidor Biwenger MCP]
    K -->|token al iniciar| M
    C -->|contexto de liga| M
    M -->|GET privados permitidos| A
    M -->|GET catálogo y mercado global| P[cf.biwenger.com]
    A -->|datos de liga| M
    P -->|datos públicos| M
    M -->|JSON identificado y fechado| CL
```

Claude Desktop administra `uv`, crea el entorno Python de la extensión y ejecuta `mcpb_server.py` por `stdio`. No hay un servidor remoto del proyecto. El pequeño servidor HTTP solo existe durante la conexión o desconexión, escucha en loopback y se cierra al completar la operación o caducar.

Las consultas deportivas pasan por una lista cerrada de rutas y métodos. El catálogo público se solicita con el `scoreID` de la liga activa. Cada resultado incluye competición, ID y nombre de puntuación, momento de obtención y advertencias aplicables.
