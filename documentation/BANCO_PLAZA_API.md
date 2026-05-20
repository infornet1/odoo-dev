# Banco Plaza Open API — Reference Documentation

**Source docs:** `/home/ftpuser/odoo-dev/bcoplaza-api-docs/`
**API version:** 4.0.0 (TRF/P2C/Movimientos) | 3.0.0 (Balances)
**Last updated:** 2026-05-16

---

## Onboarding Status

**Status:** QA/Evaluation phase — awaiting credentials from Banco Plaza via Telegram.

| Resource | Link |
|---|---|
| Developer portal (QA) | https://portalapiqa.bancoplaza.com/devportal/apis |
| OpenAPIs portal | https://plazaopenapis.bancoplaza.com/ |
| Telegram support group | https://t.me/+6t84xWNWfhEzOTM5 |

**Credentials delivery:** Banco Plaza will post `client_id` + `client_secret` (QA) and test account numbers in the Telegram group. Production credentials follow after QA validation.

**Next step:** Once credentials arrive via Telegram → save to `/opt/odoo-dev/config/bancoplaza_api.json` → begin QA testing against `openapiqa.bancoplaza.com`.

---

## Environments

| Purpose | QA | Production |
|---|---|---|
| API base | `https://openapiqa.bancoplaza.com` | `https://openapi.bancoplaza.com` |
| Token URL | `https://portalapiqa.bancoplaza.com/oauth2/token` | `https://portalapi.bancoplaza.com/oauth2/token` |

---

## Authentication — OAuth 2.0 (client_credentials)

All endpoints require a Bearer token. Token expires after a defined period — always refresh if 401 is returned.

**Step 1 — Obtain token:**
```http
POST https://portalapi.bancoplaza.com/oauth2/token
Authorization: Basic base64(CLIENT_ID:CLIENT_SECRET)
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials
```

**Step 2 — Use token on every API call:**
```http
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Python pattern:**
```python
import requests, base64

def get_plaza_token(client_id, client_secret, qa=False):
    url = "https://portalapiqa.bancoplaza.com/oauth2/token" if qa else "https://portalapi.bancoplaza.com/oauth2/token"
    creds = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    resp = requests.post(url, headers={
        "Authorization": f"Basic {creds}",
        "Content-Type": "application/x-www-form-urlencoded"
    }, data={"grant_type": "client_credentials"})
    resp.raise_for_status()
    return resp.json()["access_token"]
```

**Config:** Store `client_id` + `client_secret` in `/opt/odoo-dev/config/bancoplaza_api.json` (gitignored, same pattern as `freescout_api.json`).

---

## API Group 1: Verify Incoming Transfer (TRF)

**Used for:** Confirming a bank transfer or supplier payment has been credited to UEIPAB's Plaza account.

### Endpoint A — By UEIPAB account
```
POST https://openapi.bancoplaza.com/cuentas/operacion/v1/v0/cuentas/operacion
```

**Request body (JSON):**

| Field | Type | Required | Description |
|---|---|---|---|
| `cuenta` | String | Yes | UEIPAB's 20-digit Plaza account number |
| `moneda` | String | Yes | Currency code ISO 4217. Default: `VES` |
| `banco` | String | Yes | 4-digit bank code of sender. `0138`=Plaza, `0105`=Mercantil, `0102`=BDV, `0104`=Banesco |
| `tPago` | String | Yes | Transaction type. `TRF` = Transfer/supplier payment |
| `naturaleza` | String | Yes | `CR` = Credit (incoming) |
| `referencia` | String | Yes | Reference number (≤9 digits for Plaza-origin; ≤8 for other banks) |
| `fechaInicio` | Date | Yes | Start date filter `YYYY-MM-DD` |
| `fechaFin` | Date | Yes | End date filter `YYYY-MM-DD` |
| `monto` | Double | Yes | Transaction amount e.g. `3098.50` |
| `canal` | String | Yes | Channel code. `"23"` = BOTON DE PAGO/Open Bank |
| `id` | String | Yes | Sender cedula/RIF. Natural person: `V013759368`. Company: `J378944781` |
| `direccion_ip` | String | No | IPv4 of calling server (send in HTTP header) |

**Request example:**
```json
{
  "cuenta": "01380011130110248648",
  "moneda": "VES",
  "banco": "0138",
  "tPago": "TRF",
  "naturaleza": "CR",
  "referencia": "12346768",
  "fechaInicio": "2026-05-16",
  "fechaFin": "2026-05-16",
  "monto": 3098.50,
  "canal": "23",
  "id": "V013759368"
}
```

**Response body:**
```json
{
  "movimientos": [
    {
      "fecha": "2026-05-16",
      "hora": "14:08:32",
      "referencia": "12346768",
      "concepto": "TRF PLAZA V013759368 MARIA R",
      "tipo": "TO",
      "naturaleza": "CR",
      "monto": 3098.50
    }
  ]
}
```

**Response header fields (always present):** `codigoRespuesta`, `descripcionCliente`, `descripcionSistema`, `fechaHora`

**Concepto patterns observed:**
- `TRF PLAZA V013759368 MARIA R` — sender cedula + name
- `TRF BANESC J013759368 MARIA R` — inter-bank
- `TRF MERCAN V999999999 CANELONE`
- `PAG PLAZA V999999999 CANELONE` — supplier payment type CF

### Endpoint B — By customer RIF (alternative)
```
POST https://openapi.bancoplaza.com/cuentas/operaciones/v1/v0/cuentas/operaciones/{rif_cliente}
```
`rif_cliente` in URL path (12 chars e.g. `V13759368`). Body accepts same optional filters.

### Response Codes

| Code | Description | HTTP |
|---|---|---|
| `0000` | Transaction found | 200 |
| `0005` | No transactions for this search | 204 |
| `0004` | No parametria for search type | 204 |
| `C001` | Client not found | 404 |
| `C002` | Account not found or not belonging to client | 404 |
| `C006` | Parameter format invalid | 400 |
| `C007` | fechaInicio > fechaFin | 400 |
| `C009` | Invalid currency code | 400 |
| `0096` | System error | 500 |
| `A001-A004` | Digital signature invalid / expired | 400 |
| `A003` | Resource not authorized | 403 |
| `A004` | API-KEY invalid or revoked | 401 |

---

## API Group 2: Verify P2P / P2C Mobile Payment

**Used for:** Confirming a Pago Móvil (P2C = Person-to-Company) received by UEIPAB.

```
GET https://openapi.bancoplaza.com/pagos/p2p/v1/v1/pagos/p2p/{id}
```

`{id}` = UEIPAB's RIF in URL path (12 chars, e.g. `J00297055`). All filters are QueryString params.

**Query parameters:**

| Param | Type | Required | Description |
|---|---|---|---|
| `canal` | String | Yes | `"20"`=POS, `"21"`=MERCHANT, `"22"`=VPOS, `"23"`=BOTON DE PAGO, `"24"`=BILLETERA DIGITAL |
| `acc` | Integer | No | Direction: `0`=incoming (default), `1`=outgoing, `>1`=all |
| `fi` | String | No | Start date `YYYY-MM-DD`. Default: service limit (~2 months back) |
| `ff` | String | No | End date `YYYY-MM-DD`. Default: today |
| `tlf` | String | No | Filter by sender phone `00582XXXXXXXXX` format (no special chars) |
| `tlfa` | String | No | Filter by UEIPAB's affiliated phone (registered with Open Bank) |
| `horaIni` | String | No | Start time `HHMMSSMS` format e.g. `09000000` |
| `horaFin` | String | No | End time `HHMMSSMS` format |
| `id_Pago` | String | No | Filter by payer's cedula/RIF (12 chars) |

**Common query combos:**
- `?acc=0&fi=2026-05-16&ff=2026-05-16` — all incoming P2C today
- `?tlf=00584124688296&acc=0` — from a specific phone today
- `?id_Pago=V00025709325&acc=0` — from a specific cedula today
- `?horaIni=09000000&horaFin=18000000` — within business hours

**Response body:**
```json
{
  "cantidadPagos": 3,
  "pagos": [
    {
      "accion": "R",
      "banco": "0172",
      "concepto": "pago",
      "fecha": "20260412",
      "hora": "1832",
      "monto": "500.00",
      "referencia": "183255935841",
      "telefonoAfiliado": "4242956418",
      "telefonoCliente": "4124688296",
      "cedulaB": "V00025709325"
    }
  ]
}
```

**Key fields for matching:**
- `cedulaB` — payer's cedula (goldmine: direct Odoo `res.partner.vat` lookup)
- `telefonoCliente` — payer's phone (cross-reference with WA contact)
- `monto` — VES amount (convert to USD via BCV rate for invoice matching)
- `referencia` — unique dedup key
- `fecha` — format `YYYYMMDD` (no hyphens — parse with `datetime.strptime(x, '%Y%m%d')`)
- `hora` — format `HHMM`

### Response Codes

| Code | Description | HTTP |
|---|---|---|
| `0000` | Success | 200 |
| `E001` | Client not registered | 500 |
| `E002` | Phone not registered | 500 |
| `E003` | Record not found | 204 |
| `E024` | Client blocked | 500 |
| `0002` | Required parameter missing | 400 |

---

## API Group 3: Account Movements (Movimientos)

**Used for:** Real-time full transaction history — replaces manual CSV import in `reconciliation_engine.py`.

```
GET https://openapi.bancoplaza.com/cuentas/movimientos/v1/v0/cuentas/{cuenta}/movimientos
GET https://openapi.bancoplaza.com/cuentas/movimientos/v1/v0/cuentas/{id}/{cuenta}/movimientos
```

`{cuenta}` = 20-digit account number; `{id}` = RIF/cedula.

---

## API Group 4: Account Balances (Cuentas y Saldos)

**Used for:** Real-time Plaza account balance — inject into Glenda daily digest or finance dashboard.

| Endpoint | Description |
|---|---|
| `GET /cuentas/v1/v0/cuentas/default` | Default registered account |
| `GET /cuentas/v1/v0/cuentas/{id}` | All accounts by RIF |
| `GET /cuentas/v1/v0/cuentas/{cuenta}` | Specific 20-digit account |
| `GET /cuentas/v1/v0/cuentas/{id}/{cuenta}` | RIF + account |
| `GET /cuentas/v1/v0/cuentas/telefonos/{telefono}` | By registered phone |
| `GET /cuentas/v1/v0/cuentas/{id}/telefonos/{telefono}` | By RIF + phone |

---

## API Group 5: Collect — Débito Inmediato (token-based)

**Used for:** Initiating an instant debit from customer's account. Bank sends customer a token; UEIPAB uses it to pull payment. **Requires customer cooperation** — not suitable for passive collection.

Reference doc: `Referencia de Uso API Banco Plaza -Cobro con débito inmediato con token.pdf`

---

## API Group 6: Collect — C2P (Customer Initiates)

**Used for:** Customer initiates payment from their bank app using UEIPAB's registered phone/key. UEIPAB receives instant credit.

Reference doc: `Referencia de Uso API Banco Plaza -Cobros con C2P.pdf`

---

## UEIPAB-Specific Constants

> Fill these in when credentials are obtained from Banco Plaza:

```python
PLAZA_CLIENT_ID     = ""    # from Banco Plaza Open Bank enrollment
PLAZA_CLIENT_SECRET = ""    # from Banco Plaza Open Bank enrollment
PLAZA_CUENTA        = ""    # UEIPAB's 20-digit Plaza account number
PLAZA_RIF           = "J00297055"   # J-00297055-3 (normalized, no hyphens, no check digit)
PLAZA_BANCO_CODE    = "0138"
```

Config file: `/opt/odoo-dev/config/bancoplaza_api.json` (gitignored)

---

## Key Gotchas

1. **Date format in P2C response** — `fecha` is `YYYYMMDD` (no hyphens). Parse with `datetime.strptime(x, '%Y%m%d')`.
2. **`cedulaB` leading zeros** — field is 12 chars with leading `V` or `J` prefix: `V00025709325`. Strip prefix and zeros for Odoo `vat` field lookup (`vat LIKE '%25709325'`).
3. **monto in P2C is a String** — `"500.00"`, not a number. Cast with `float(pago['monto'])`.
4. **TRF referencia max digits** — Plaza-origin ≤9, other-bank ≤8. Don't zero-pad when querying.
5. **OAuth token expiry** — always handle 401 by re-fetching token and retrying once.
6. **No webhooks** — all APIs are polling-only (no push notification from bank). Plan for cron + state file dedup.
7. **`canal` for our use case** — use `"23"` (BOTON DE PAGO/Open Bank) for all queries.
8. **`action_post()` None marshal quirk** — applies here too (same XML-RPC pattern as pagos_receipt_processor). Catch `Fault("cannot marshal None")` and re-read payment state.
