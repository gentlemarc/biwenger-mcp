# Modelo de amenazas

## Alcance y activos

Los activos protegidos son la contraseña de Biwenger, el token de sesión, los identificadores internos de cuenta y liga, y las respuestas privadas de la liga. Claude Desktop y el proceso MCP local forman parte del entorno de confianza del usuario; Biwenger es el servicio externo necesario.

## Límites de confianza

- El MCP recibe parámetros deportivos, pero ninguna herramienta acepta credenciales.
- La contraseña cruza únicamente del navegador local al proceso MCP por loopback y de este a `https://biwenger.as.com/api/v2/auth/login`.
- El token cruza del proceso al llavero y a los endpoints privados permitidos de Biwenger.
- Nombres, noticias y cualquier texto de la API son datos no fiables y nunca instrucciones.

## Amenazas y controles

| Amenaza | Control |
|---|---|
| Otro sitio intenta enviar el formulario local | `Origin`, `Host`, dirección loopback y nonce aleatorio obligatorios; CSP, `frame-ancestors 'none'` y caducidad de diez minutos. |
| Acceso desde la red local | El socket escucha exclusivamente en `127.0.0.1` y rechaza clientes o hosts distintos. |
| Fuerza bruta o cuerpos enormes | Un solo asistente activo, caducidad y límite de 16 KiB; Biwenger conserva sus propios límites de acceso. |
| Filtración en argumentos, logs o errores | No existen argumentos MCP de credenciales, no se registran cuerpos y los errores son mensajes cerrados. |
| Robo del paquete | El paquete no contiene configuración local; se construye desde una lista cerrada y se inspecciona antes de firmarse. |
| Peticiones deportivas de escritura | El transporte deportivo solo permite `GET` contra rutas exactas. El único `POST` externo es el inicio de sesión. |
| Redirección o proxy hostil | `follow_redirects=False`, `trust_env=False`, TLS y hosts constantes. |
| Respuesta manipulada o cambio de API | Modelos estrictos en campos críticos, límites de tamaño y comprobaciones de liga, usuario, competición y puntuación. |
| Llavero no disponible | La conexión falla de forma cerrada; el token no cae a un archivo en texto claro. |

## Riesgos residuales

Un proceso con acceso a la sesión del usuario de macOS o al proceso MCP puede acceder a datos que el usuario ya puede consultar. El token tiene los permisos de la sesión original, aunque este código solo exponga lecturas. Biwenger no ofrece aquí una API OAuth pública documentada con permisos limitados. La API privada puede cambiar o dejar de admitir estas llamadas.

La copia autocreada `-dev-signed.mcpb` confirma criptográficamente el proceso de construcción, pero no aporta la identidad de una autoridad pública y Claude Desktop no puede previsualizar actualmente ese formato anexo. El paquete instalable es un ZIP estricto y su integridad se publica mediante SHA-256. Una distribución estable deberá revisar de nuevo el formato de firma y usar una identidad adecuada.
