# Validación de capacidades de Biwenger

Fecha de comprobación: 2026-08-31T10:46:04.042490+00:00

Solo se han ejecutado consultas GET. Los resultados privados no se guardan en este informe.

| Herramienta | Endpoints | Acceso | Resultado |
|---|---|---|---|
| `get_context` | catalog + home | optional | verified |
| `search_players` | catalog | public | verified |
| `get_player` | catalog + player | public | verified |
| `get_market_evolution` | evolution | public | verified |
| `get_my_team` | catalog + home + user | private | verified |
| `get_budget` | catalog + home + market | private | verified |
| `get_market` | catalog + home + market | private | verified |
| `get_received_offers` | catalog + home + market | private | verified |
| `get_next_round` | catalog + home | private | verified |

`verified` significa que una consulta real y la validación del contrato tuvieron éxito.
`not_configured` no implica fallo de Biwenger: falta comprobar la sesión privada.
La comparación de los datos de la liga con la aplicación requiere completar la lista de comprobación del README.
