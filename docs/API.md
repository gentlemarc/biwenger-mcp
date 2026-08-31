# Contratos de Biwenger observados

Referencia: repositorio `pablopb3/biwenger-api`, commit `1b5172c622ba868a832576822ce6d2071f9c1349` (2020-01-25).
Comprobaciones realizadas el 2026-08-31. El diagnóstico con sesión real valida `home`, `user` y `market`.
En la respuesta observada, `sales[].user` puede ser `null`; el vendedor permanece desconocido y las
ventas propias se excluyen cruzando los IDs con la plantilla.
No se ha accedido a una cuenta mediante un código de invitación.

Todas las llamadas implementadas son **GET**. El estado HTTP y el campo `status` del JSON deben ser 200.
La capa HTTP exige `data` como objeto y la capa de dominio valida los campos usados; no devuelve un éxito falso.

| Clave | Dominio y ruta | Parámetros fijos | Acceso | Campos utilizados |
|---|---|---|---|---|
| catalog | `cf.biwenger.com/api/v2/competitions/la-liga/data` | `lang=es`, `score=2` | Público, verificado | `players`, `teams`, `season`, `scores`, `scoreID`, `currency`, `update` |
| player | `cf.biwenger.com/api/v2/players/la-liga/{slug}` | `lang=es`, `score=2`, `fields=*,team,fitness,reports,prices,competition,seasons,news` | Público, verificado | Ficha, `reports`, `prices`, `news`, `competition` |
| evolution | `cf.biwenger.com/api/v2/competitions/la-liga/market` | `interval=day`, `includeValues=true` | Público, verificado | `competition`, `values`, `ups`, `downs` |
| home | `biwenger.as.com/api/v2/home` | Ninguno | Privado, verificado en diagnóstico | `league`, `user`, `competition`, `events` |
| user | `biwenger.as.com/api/v2/user` | `fields=*,lineup(type,playersID),players(*,fitness,team,owner),market(*,-userID),offers,-trophies` | Privado, verificado en diagnóstico | `id`, `players`, `lineup` |
| market | `biwenger.as.com/api/v2/market` | Ninguno | Privado, verificado en diagnóstico | `sales`, `offers`, `status.balance`, `status.maximumBid`; `sales[].user` puede ser `null` |

Solo las rutas privadas reciben `Authorization: Bearer …`, `x-league`, `x-user` y el `x-version` configurado.
Los IDs deben provenir de una petición de tu propia sesión a tu liga actual. El servidor no descubre ligas
ajenas ni se une a una liga. No se envía el token al dominio público `cf.biwenger.com`.

## Diferencias detectadas respecto al repositorio antiguo

- El catálogo confirma `scoreID=2` y la entrada de `scores` con `id=2` como SofaScore; AS/SofaScore utiliza otro ID.
- `fitness` puede contener puntos enteros, `null` o estados como `injured`, `doubt`, `discarded` y `sanctioned`.
- La consulta anidada antigua de la ficha produjo HTTP 400. La selección actual y más sencilla está verificada.
- Los informes de partido actuales devuelven `points` como objeto por sistema: se selecciona la clave `2`.
  Si en el futuro llegan puntos escalares sin confirmar el sistema, no se atribuirán automáticamente a SofaScore.
- La ficha puede omitir `scoreID` y puntos totales. Los totales proceden del catálogo validado;
  los puntos de partido proceden de la clave explícita `2` del informe.
- Los precios históricos utilizan pares `[YYMMDD, importe]`, no timestamps Unix. Se ordenan por fecha.
- Las subidas y bajadas del endpoint global no confirman sistema de puntuación; se omiten sus puntos.
- No se presupone que una oferta tenga exactamente un jugador ni que exista una próxima jornada anunciada.
- La caché y la unión por IDs sustituyen el servidor Go y la base MongoDB de alias del proyecto original.

## Comprobaciones manuales pendientes

1. Comprobar manualmente los ajustes omitidos por la API y las cantidades, alineación y mercado en la app.
2. Confirmar en la interfaz de Codex las llamadas privadas. Las pruebas sintéticas y `stdio` no reemplazan este paso.
