# Biwenger MCP 0.2.0 — beta privada

Primera extensión MCPB para macOS, preparada para pruebas antes de hacer público el repositorio.

## Novedades

- Instalación en Claude Desktop mediante `.mcpb` con runtime `uv` administrado por el host.
- Conexión en navegador local mediante correo y contraseña propia de Biwenger.
- Descubrimiento y selección de ligas, verificación con `/home` y sesión en el llavero de macOS.
- Compatibilidad con siete sistemas estándar de LaLiga Clásica.
- Herramientas locales de conexión y desconexión; las nueve consultas deportivas existentes siguen disponibles cuando su diagnóstico es correcto.
- Política de privacidad, modelo de amenazas, arquitectura, paquete instalable y SHA-256.

## Límites de esta beta

- Solo macOS, LaLiga y modo Clásica.
- Proyecto no oficial basado en endpoints que Biwenger puede cambiar.
- La copia `-dev-signed.mcpb` usa una firma autocreada y no es instalable en la versión actual de Claude Desktop. El `.mcpb` principal es un ZIP estricto sin ese bloque anexo.
- La autenticación real por contraseña y una instalación limpia deben completarse manualmente antes de declarar estable esta versión.
- El análisis de rivales queda para la siguiente entrega.
