# Instalar en Claude Desktop para macOS

Esta versión requiere Claude Desktop `1.40609.0` o posterior. El usuario no necesita instalar Python, `uv` ni usar la terminal.

1. Descarga `biwenger-mcp-0.2.1.mcpb` y comprueba el SHA-256 publicado junto al archivo.
2. En Claude Desktop abre **Settings → Extensions → Advanced settings → Install Extension** y elige el `.mcpb`. También puedes abrir el archivo con Claude Desktop.
3. Inicia un chat nuevo y pide a Claude que use `connect_biwenger`.
4. En la página local que se abre, escribe el correo y la contraseña propia de Biwenger. Si la cuenta se creó con Google y no tiene contraseña propia, establécela mediante la recuperación oficial de Biwenger. No introduzcas la contraseña de Google.
5. Elige una liga compatible. Se admiten LaLiga, modo Clásica y los sistemas estándar Diario AS, SofaScore, Estadísticas, Feeberse, las dos medias y Biwenger Social.
6. Vuelve a Claude Desktop y reinicia la extensión desde sus ajustes. Después llama a `get_context` y comprueba la liga y la puntuación.

Para renovar una sesión caducada, repite `connect_biwenger`. Para eliminarla, usa `disconnect_biwenger`, confirma en la página local y reinicia la extensión.

La primera comprobación debe comparar con la web de Biwenger la plantilla, alineación, saldo, puja máxima y mercado. Esta extensión no puede pujar, comprar, vender, aceptar ofertas ni modificar la alineación.

El proyecto no está afiliado, patrocinado ni respaldado por Biwenger o Diario AS.
