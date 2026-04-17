# Self-Service Kiosk Platform — Implementation Plan

**Status:** Planned | **Approach:** Standalone PWA (Option B)
**Created:** 2026-03-07 | **Last Updated:** 2026-03-07

---

## Overview

A modular self-service platform that allows UEIPAB customers and employees to access documents (fiscal invoices, payslip certificates, study letters, etc.) through a touch-optimized Progressive Web App (PWA). The platform integrates with Banco Plaza's Open Banking API for payment processing and uses the existing MassivaMovil WhatsApp infrastructure for notifications.

### Key Use Cases

| # | Service | Target User | Trigger |
|---|---------|-------------|---------|
| 1 | Fiscal Invoice Pickup | Customers (Representantes) | Invoice payment confirmed |
| 2 | Certified Payslip | Employees | On-demand request |
| 3 | Study Appointment Letter | Customers (Representantes) | On-demand request |
| 4 | Employment Certificate | Employees | On-demand request |
| 5 | Vuelto Digital (Change Back) | Customers | Overpayment detected |

### Delivery Channels

- **Physical Kiosk**: Touch-screen tablet at UEIPAB premises, prints documents
- **Virtual Kiosk**: Same PWA accessible from customer's phone/browser via WhatsApp link

---

## Architecture

### Why Standalone PWA (Option B)

| Criteria | Odoo Portal (Option A) | Standalone PWA (Option B) |
|----------|----------------------|--------------------------|
| Touch UX | Limited, desktop-first | Full control, touch-first design |
| Offline | No | Yes, PWA caches app shell |
| Kiosk mode | Poor fit | Native Android kiosk mode support |
| Reusability | Tied to Odoo session | Same app for physical + virtual |
| Auth | Odoo login (complex for kiosk) | Simple cedula/QR code |
| Development | Odoo QWeb templates | Modern frontend (Vue.js/React) |
| API pattern | N/A | Same as existing AI agent scripts |

### System Diagram

```
+---------------------+       +-------------------+       +------------------+
|   PWA Frontend      |       |   Odoo 17 CE      |       |  External APIs   |
|   (Vue.js + TW)     |<----->|   JSON-RPC API    |<----->|                  |
|                     |       |                   |       |  Banco Plaza     |
|  - Kiosk tablet     |       |  ueipab_self_     |       |  (P2P/P2C)       |
|  - Customer phone   |       |  service          |       |                  |
|  - Desktop browser  |       |                   |       |  MassivaMovil    |
|                     |       |  ueipab_banco_    |       |  (WhatsApp)      |
+---------------------+       |  plaza            |       |                  |
                              |                   |       |  SENIAT          |
+---------------------+       |  ueipab_self_     |       |  (Fiscal valid.) |
|   Hardware          |       |  service_*        |       +------------------+
|                     |       |  (service plugins)|
|  - Tablet (Android) |       +-------------------+
|  - Printer (USB/Net)|
|  - Enclosure        |
+---------------------+
```

---

## Odoo Modules

### Module 1: `ueipab_banco_plaza` — Banking Integration

**Purpose:** Banco Plaza Open Banking API client for P2P/P2C payments.

**PENDING:** Request payment *reception* API from Banco Plaza. The current API (v3.4.3, "Envio Vuelto Digital") only supports **outbound** P2P/P2C transfers. We need the **inbound** payment verification/notification API to detect when customers pay invoices.

#### API Reference (Current — Outbound Only)

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/v1/pagos/p2p` | POST | HMAC-SHA384 | Send P2P/P2C payment |
| `/v1/pagos/p2p/{id}` | POST | HMAC-SHA384 | Send payment on behalf of third party |
| `/v1/pagos/p2p/bancos` | GET | None | List affiliated banks |

**Environments:**

| Environment | Domain | Port |
|-------------|--------|------|
| QA/Testing | `apiqa.bancoplaza.com` | 8585 |
| Production | `api.bancoplaza.com` | 8282 |

#### Authentication

Every authenticated request requires 3 headers:
- `Api-key`: 32-char client identifier (from Tu Plaza Linea Empresa portal)
- `Nonce`: Incrementing integer (unix timestamp in milliseconds)
- `Api-signature`: HMAC-SHA384 of `/{path}{nonce}{JSON.body}` signed with `api-key-secret`

```python
# Python signing example
import hmac, hashlib, json, time

def sign_request(api_secret, path, nonce, body=None):
    """Generate HMAC-SHA384 signature for Banco Plaza API."""
    message = f"/{path}{nonce}"
    if body:
        message += json.dumps(body, separators=(',', ':'))
    return hmac.new(
        api_secret.encode(),
        message.encode(),
        hashlib.sha384
    ).hexdigest()
```

#### Key Model

```python
class BancoPlazaTransaction(models.Model):
    _name = 'banco.plaza.transaction'
    _description = 'Banco Plaza Transaction'
    _order = 'create_date desc'

    name = fields.Char(compute='_compute_name', store=True)
    transaction_type = fields.Selection([
        ('p2p_out', 'P2P Outbound (Vuelto Digital)'),
        ('p2p_in', 'P2P Inbound (Payment Reception)'),  # Future
    ])
    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('confirmed', 'Confirmed'),
        ('failed', 'Failed'),
        ('timeout', 'Timeout'),
    ])

    # Banco Plaza fields
    banco_code = fields.Char(string='Bank Code')
    id_beneficiario = fields.Char(string='Beneficiary ID (Cedula/RIF)')
    telefono = fields.Char(string='Beneficiary Phone')
    monto = fields.Float(string='Amount')
    moneda = fields.Selection([('VES', 'VES'), ('USD', 'USD')])
    motivo = fields.Char(string='Description', size=35)
    canal = fields.Selection([
        ('20', 'POS'), ('21', 'MERCHANT'), ('22', 'VPOS'),
        ('23', 'BOTON DE PAGO'), ('24', 'BILLETERA DIGITAL'),
    ])
    numero_referencia = fields.Char(string='Bank Reference')
    id_externo = fields.Char(string='External ID (Idempotency)')

    # Odoo links
    partner_id = fields.Many2one('res.partner')
    invoice_id = fields.Many2one('account.move')
    payment_id = fields.Many2one('account.payment')

    # API response
    codigo_respuesta = fields.Char()
    descripcion_cliente = fields.Char()
    descripcion_sistema = fields.Char()
    response_datetime = fields.Datetime()
```

#### Configuration

Credentials stored in `ir.config_parameter` (same pattern as AI agent):
- `banco_plaza.api_key`
- `banco_plaza.api_key_secret` (never sent over the wire, signing only)
- `banco_plaza.environment` (`qa` or `production`)
- `banco_plaza.default_canal`
- `banco_plaza.telefono_afiliado` (UEIPAB's registered phone)

Config file: `/opt/odoo-dev/config/banco_plaza.json` (gitignored), loaded via `post_init_hook`.

#### Pending: Payment Reception API

**ACTION REQUIRED:** Contact Banco Plaza to request:

1. **Incoming payment notification API** — Webhook or polling endpoint to detect when a customer pays via Pago Movil / transfer to UEIPAB's account
2. **Payment verification API** — Confirm a specific transaction reference is valid
3. **Account balance/statement API** — For automated reconciliation

Without this, payment detection must be done via:
- Manual reconciliation (accountant confirms in Odoo)
- Bank statement import (OFX/CSV) + Odoo auto-matching
- SMS parsing of Pago Movil confirmation messages (fragile)

---

### Module 2: `ueipab_self_service` — Core Platform

**Purpose:** Document queue, customer authentication, notification engine, and service registry.

#### Key Models

```python
class SelfServiceDocument(models.Model):
    _name = 'self.service.document'
    _description = 'Self-Service Document'
    _order = 'create_date desc'

    partner_id = fields.Many2one('res.partner', required=True)
    service_type = fields.Selection([
        ('invoice', 'Factura Fiscal'),
        ('payslip_cert', 'Constancia de Nomina'),
        ('study_letter', 'Constancia de Estudio'),
        ('employment_cert', 'Constancia de Trabajo'),
        ('vuelto', 'Vuelto Digital'),
    ])
    state = fields.Selection([
        ('ready', 'Listo para Retiro'),
        ('notified', 'Notificado'),
        ('delivered', 'Entregado'),
        ('expired', 'Expirado'),
    ], default='ready')

    # Source document (polymorphic)
    source_model = fields.Char()  # 'account.move', 'hr.payslip', etc.
    source_id = fields.Integer()
    source_ref = fields.Char(string='Document Reference')  # INV-2026-001, etc.

    # Document content
    document_pdf = fields.Binary(attachment=True)
    document_filename = fields.Char()

    # Delivery
    delivery_method = fields.Selection([
        ('kiosk', 'Kiosko Fisico'),
        ('virtual', 'Virtual / Descarga'),
    ])
    pickup_code = fields.Char(string='Pickup Code')  # 6-digit or QR token
    pickup_url = fields.Char(compute='_compute_pickup_url')
    delivered_date = fields.Datetime()

    # Notifications
    notified_whatsapp = fields.Boolean()
    notified_email = fields.Boolean()
    notification_date = fields.Datetime()
    expiry_date = fields.Datetime()  # Auto-expire after X days


class SelfServiceKiosk(models.Model):
    _name = 'self.service.kiosk'
    _description = 'Kiosk Device'

    name = fields.Char(required=True)  # "Kiosko Recepcion", "Kiosko RRHH"
    location = fields.Char()
    device_id = fields.Char()  # Unique device identifier
    is_active = fields.Boolean(default=True)
    last_heartbeat = fields.Datetime()
    allowed_services = fields.Selection()  # Which services this kiosk offers
    printer_config = fields.Text()  # JSON: printer type, IP, etc.
```

#### Customer Authentication (Kiosk)

No Odoo login required. Simple identification methods:

1. **Cedula Input**: Customer types their cedula number on touchscreen numpad
2. **QR Code**: WhatsApp notification includes a QR with an encrypted token → customer shows to tablet camera
3. **Pickup Code**: 6-digit code sent via WhatsApp (e.g., "Su codigo de retiro: 847291")

**CRITICAL — Closed System Validation:**

The kiosk is a **delivery channel for known customers only**, not a public registration point. Authentication requires the customer to exist in Odoo with a valid Representante tag:

1. Customer inputs cedula (e.g., `V12345678`)
2. Odoo searches `res.partner` where `vat = 'V12345678'`
3. Partner **must** have `category_id` IN `(25, 26)` — tag `Representante` (ID 25) or `Representante PDVSA` (ID 26)
4. **If no match or missing tag** → screen shows "No se encontro su registro" → no actions available, no documents shown
5. **If valid match** → proceed to show pending `self.service.document` records

This means only the **318 known Representante contacts** (244 Rep + 74 PDVSA, both environments synced) can use the kiosk. A person not in the system gets nothing — they cannot browse, request, or print any document.

```python
# Authentication logic (server-side)
VALID_TAG_IDS = [25, 26]  # Representante, Representante PDVSA

def _authenticate_customer(self, cedula):
    """Validate cedula against known Representante contacts."""
    partner = self.env['res.partner'].search([
        ('vat', '=', cedula),
        ('category_id', 'in', VALID_TAG_IDS),
    ], limit=1)
    if not partner:
        return {'success': False, 'error': 'NOT_FOUND'}
    return {
        'success': True,
        'partner_id': partner.id,
        'name': partner.name,
        'documents': self._get_pending_documents(partner),
    }
```

For **employee services** (payslip certs, employment letters), a separate authentication rule applies — validated against `hr.employee` records instead of partner tags. This is Phase 6 scope.

The PWA calls Odoo JSON-RPC to validate and fetch pending documents:

```
POST /jsonrpc
{
    "method": "call",
    "params": {
        "model": "self.service.document",
        "method": "authenticate_and_fetch",
        "args": [{"cedula": "V12345678"}]  // or {"pickup_code": "847291"}
    }
}
```

#### Notification Engine

Reuses existing MassivaMovil WhatsApp integration from `ueipab_ai_agent`:

```python
def _notify_document_ready(self):
    """Send WhatsApp notification when document is ready for pickup."""
    wa_service = self.env['ai.agent.whatsapp.service']
    for doc in self.filtered(lambda d: d.state == 'ready'):
        phone = doc.partner_id.mobile or doc.partner_id.phone
        if not phone:
            continue
        message = (
            f"Estimado/a {doc.partner_id.name},\n\n"
            f"Su documento *{doc.get_service_label()}* "
            f"ref. {doc.source_ref} esta listo.\n\n"
            f"Codigo de retiro: *{doc.pickup_code}*\n"
            f"Tambien puede descargarlo aqui: {doc.pickup_url}\n\n"
            f"Valido hasta: {doc.expiry_date.strftime('%d/%m/%Y')}"
        )
        wa_service.send_message(phone, message)
        doc.write({
            'state': 'notified',
            'notified_whatsapp': True,
            'notification_date': fields.Datetime.now(),
        })
```

---

### Module 3: `ueipab_self_service_invoicing` — Invoice Service Plugin

**Purpose:** Automate fiscal invoice generation and delivery when payment is confirmed.

#### Flow

```
Customer pays invoice (bank transfer / Pago Movil)
    |
    v
Payment registered in Odoo (manual or auto-reconciliation)
    |
    v
account.move state changes to 'posted' + payment_state = 'paid'
    |
    v  (automated action / override write())
Generate fiscal PDF with SENIAT seal/control number
    |
    v
Create self.service.document (state=ready, pickup_code generated)
    |
    v
WhatsApp notification sent to customer
    |
    v
Customer retrieves document:
    - Physical: Kiosk tablet -> cedula/QR -> print
    - Virtual: WhatsApp link -> browser -> download PDF
    |
    v
Document marked as 'delivered'
```

#### Automated Action

```python
class AccountMove(models.Model):
    _inherit = 'account.move'

    self_service_document_ids = fields.One2many(
        'self.service.document', 'source_id',
        domain=[('source_model', '=', 'account.move')],
    )

    def _create_self_service_document(self):
        """Called when invoice is fully paid. Creates pickup-ready document."""
        SelfServiceDoc = self.env['self.service.document']
        for invoice in self:
            if invoice.move_type != 'out_invoice':
                continue
            if SelfServiceDoc.search_count([
                ('source_model', '=', 'account.move'),
                ('source_id', '=', invoice.id),
            ]):
                continue  # Already created

            # Generate fiscal PDF
            pdf_content = self.env['ir.actions.report']._render_qweb_pdf(
                'account.account_invoices', invoice.ids
            )

            SelfServiceDoc.create({
                'partner_id': invoice.partner_id.id,
                'service_type': 'invoice',
                'source_model': 'account.move',
                'source_id': invoice.id,
                'source_ref': invoice.name,
                'document_pdf': base64.b64encode(pdf_content[0]),
                'document_filename': f'{invoice.name}.pdf',
                'pickup_code': SelfServiceDoc._generate_pickup_code(),
                'expiry_date': fields.Datetime.now() + timedelta(days=30),
            })
```

#### Venezuelan Fiscal Invoice Requirements

For invoices to be legally valid in Venezuela:

- **SENIAT Control Number**: Sequential fiscal control number (Numero de Control)
- **RIF**: UEIPAB's tax ID on the invoice
- **Customer Cedula/RIF**: Required on the invoice
- **Tax breakdown**: IVA (16%) clearly separated
- **Fiscal printer** (optional): SENIAT-certified printers auto-generate control numbers
- **Pre-printed format** (alternative): If not using fiscal printer, use SENIAT-authorized pre-printed invoice books with control numbers already assigned

**Note:** The exact fiscal compliance approach depends on UEIPAB's current SENIAT setup. This module generates the PDF; the fiscal numbering/seal is handled by existing Odoo invoice configuration or a dedicated fiscal module.

---

## PWA Frontend

### Tech Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Framework | Vue.js 3 + Composition API | Lightweight, touch-friendly |
| Styling | Tailwind CSS | Rapid UI, responsive, utility-first |
| State | Pinia | Simple state management |
| HTTP | Axios | JSON-RPC calls to Odoo |
| QR Scanner | html5-qrcode | Camera-based QR reading on kiosk |
| PWA | Vite PWA plugin | Service worker, offline caching |
| Printing | window.print() / CUPS API | Direct USB or network printer |

### Screen Flow

```
[Splash / Welcome Screen]
    "Bienvenido al Autoservicio UEIPAB"
    [Soy Representante]  [Soy Empleado]
            |                    |
            v                    v
    [Identification Screen]
    - Numpad for cedula input (e.g., V12345678)
    - OR "Escanear QR" button (camera)
    - OR "Tengo un codigo" (6-digit input)
            |
            v
    [Validation] ── cedula NOT found in res.partner ──> [Error Screen]
    - res.partner.vat match?                            "No se encontro su registro.
    - Has tag Representante (25)                         Contacte a administracion."
      or Representante PDVSA (26)?                       Auto-return to welcome 10s
            |
         VALID
            v
    [My Documents Screen]
    - "Bienvenido, [Partner Name]"
    - List of ready documents (cards)
    - Each card: type icon, reference, date, status
    - Tap card -> document preview
    - No documents? -> "No tiene documentos pendientes"
            |
            v
    [Document Detail Screen]
    - PDF preview (embedded viewer)
    - [Imprimir] button (kiosk only)
    - [Descargar PDF] button
    - [Volver] button
            |
            v
    [Confirmation Screen]
    - "Documento impreso/descargado exitosamente"
    - Auto-return to welcome after 10s
```

### Touch UX Guidelines

- **Minimum touch target**: 48x48px (Google Material guidelines)
- **Large numpad**: Full-width for cedula input, 72px buttons minimum
- **High contrast**: Dark text on light background, large fonts (18px+ body)
- **No scrolling if possible**: Paginate document lists, max 4-5 items per page
- **Auto-timeout**: Return to welcome screen after 60s of inactivity
- **Language**: Spanish only (Venezuelan locale)

### Odoo JSON-RPC Integration

The PWA communicates with Odoo exclusively via JSON-RPC. A dedicated API controller in `ueipab_self_service` exposes kiosk-specific endpoints:

```python
class SelfServiceController(http.Controller):

    @http.route('/self-service/api/authenticate', type='json', auth='none',
                methods=['POST'], csrf=False)
    def authenticate(self, **kwargs):
        """Validate cedula/pickup_code and return pending documents."""
        # Validates against res.partner VAT field or pickup_code
        # Returns list of ready documents (no Odoo session required)

    @http.route('/self-service/api/document/<int:doc_id>/pdf', type='http',
                auth='none', methods=['GET'], csrf=False)
    def download_pdf(self, doc_id, token, **kwargs):
        """Download document PDF. Requires valid pickup token."""
        # Token-based auth (no Odoo login)
        # Marks document as delivered

    @http.route('/self-service/api/document/<int:doc_id>/print', type='json',
                auth='none', methods=['POST'], csrf=False)
    def mark_printed(self, doc_id, **kwargs):
        """Mark document as printed/delivered from kiosk."""

    @http.route('/self-service/api/heartbeat', type='json', auth='none',
                methods=['POST'], csrf=False)
    def kiosk_heartbeat(self, **kwargs):
        """Kiosk device heartbeat for monitoring."""
```

**Security:** All endpoints use token-based authentication (pickup_code or device API key), NOT Odoo session auth. This allows the kiosk tablet to operate without an Odoo user login.

---

## Hardware Setup (Physical Kiosk)

### Recommended Components

| Component | Model | Estimated Cost |
|-----------|-------|---------------|
| Tablet | Samsung Galaxy Tab A9+ (11") or Lenovo Tab M10 | $150-200 |
| Tablet Enclosure | Wall-mount anti-theft case with USB passthrough | $50-80 |
| Printer | Brother HL-L2350DW (laser, WiFi) or HP LaserJet M110w | $120-180 |
| USB Hub | Powered USB 3.0 hub (if needed for printer) | $20-30 |
| Power | Tablet + printer power strip, wall-mounted | $15 |

**Total estimated per kiosk station: $355-505 USD**

### Tablet Kiosk Mode

Android tablets support "kiosk mode" (also called "lock task mode"):
- Lock device to Chrome browser only
- Open PWA URL on boot
- Disable navigation bar, status bar, notifications
- Options: Samsung Knox (built-in), or third-party MDM (Hexnode, Scalefusion)

### Printer Integration

Two approaches for printing from the PWA:

1. **Browser Print Dialog**: `window.print()` — simplest, uses Android print service. Works with any WiFi/USB printer connected to the tablet. Limited control over layout.

2. **Network Print Server**: PWA sends print job to a lightweight print server (CUPS on a Raspberry Pi or the Odoo server) that sends the PDF directly to the printer. More control, allows silent printing without dialog.

**Recommendation:** Start with option 1 (browser print). Upgrade to option 2 if print quality/UX needs improvement.

---

## Integration with Existing Systems

### WhatsApp (MassivaMovil)

Reuses `ai.agent.whatsapp.service` from `ueipab_ai_agent` module:
- Same API credentials, same anti-spam (120s between sends)
- Notification templates for each service type
- Pickup code + download URL included in message

### Glenda AI Agent

Future integration: Glenda could handle self-service queries via WhatsApp:
- "Quiero mi factura del mes de febrero" -> triggers document generation
- "Necesito constancia de estudio para mi hijo" -> creates study letter request

This would add a new skill to the AI agent:
```python
# Skill: self_service_request
# Trigger: Customer asks for a document via WhatsApp
# Flow: Identify document type -> validate eligibility -> generate -> send pickup code
```

### Existing Invoice Workflow

The self-service document creation hooks into the existing `account.move` workflow:
- No changes to current invoicing process
- Document generation triggered AFTER payment confirmation
- Accountants continue working normally; kiosk is a delivery channel, not a billing tool

---

## Security Considerations

| Concern | Mitigation |
|---------|------------|
| Kiosk tablet theft | Wall-mount enclosure, Android device lock, MDM remote wipe |
| Unauthorized document access | Cedula must match `res.partner` with tag Representante/PDVSA (IDs 25/26). No tag = no access. Pickup codes are 6-digit, time-limited. |
| API abuse | Rate limiting on self-service endpoints, device API keys |
| Banco Plaza credentials | Stored in ir.config_parameter, API-KEY-SECRET never transmitted |
| HMAC replay attacks | Incrementing nonce (timestamp-based) per Banco Plaza spec |
| Session hijack on kiosk | No Odoo sessions on kiosk; token-based auth, auto-timeout |
| Printer queue abuse | Max 1 print per document, cooldown between prints |

---

## Development Phases

### Phase 1: Banco Plaza Integration (`ueipab_banco_plaza`)

- [ ] Request inbound payment API documentation from Banco Plaza
- [ ] Implement HMAC-SHA384 signing service in Python
- [ ] Create transaction model and API client
- [ ] Test against QA environment (`apiqa.bancoplaza.com:8585`)
- [ ] Implement outbound P2P (vuelto digital) flow
- [ ] Config: credentials in `ir.config_parameter`, JSON config file

### Phase 2: Core Self-Service Module (`ueipab_self_service`)

- [ ] Create `self.service.document` model
- [ ] Create `self.service.kiosk` model
- [ ] Implement pickup code generation (6-digit + QR token)
- [ ] Build JSON-RPC API controller (authenticate, fetch, download)
- [ ] Token-based security (no Odoo session)
- [ ] WhatsApp notification integration (reuse MassivaMovil)
- [ ] Cron: auto-expire documents after configured days
- [ ] Admin views: document queue, kiosk monitoring

### Phase 3: PWA Kiosk Frontend

- [ ] Vue.js 3 project scaffolding + Tailwind CSS
- [ ] Welcome screen with user type selection
- [ ] Cedula numpad + QR scanner + pickup code input
- [ ] Document list (card-based, touch-friendly)
- [ ] PDF viewer + print/download actions
- [ ] PWA manifest + service worker (offline shell)
- [ ] Auto-timeout and session cleanup
- [ ] Deploy on Nginx (same server as Odoo)

### Phase 4: Invoice Service Plugin (`ueipab_self_service_invoicing`)

- [ ] Hook into `account.move` payment state change
- [ ] Auto-generate fiscal PDF on payment confirmation
- [ ] Create `self.service.document` with pickup code
- [ ] Trigger WhatsApp notification
- [ ] Test end-to-end: pay invoice -> notification -> kiosk pickup

### Phase 5: Physical Kiosk Deployment

- [ ] Procure tablet + enclosure + printer
- [ ] Configure Android kiosk mode
- [ ] Network setup (WiFi, printer connectivity)
- [ ] Test printing from PWA
- [ ] Deploy at UEIPAB premises

### Phase 6: HR Services Extension (Future)

- [ ] Certified payslip generation (from `hr.payslip`)
- [ ] Study appointment letter generation
- [ ] Employment certificate generation
- [ ] Employee self-service via kiosk (different auth flow)

---

## Banco Plaza API — Quick Reference

### Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `POST /v1/pagos/p2p` | POST | Yes | Send P2P/P2C payment |
| `POST /v1/pagos/p2p/{id}` | POST | Yes | Send payment on behalf of {id} |
| `GET /v1/pagos/p2p/bancos` | GET | No | List affiliated banks |

### Required Fields (P2P Payment)

| Field | Type | Example | Description |
|-------|------|---------|-------------|
| `banco` | String(4) | `"0138"` | Beneficiary bank code |
| `idBeneficiario` | String(12) | `"V13759368"` | Cedula/RIF with type prefix |
| `telefono` | String(10) | `"4245378879"` | Beneficiary phone (no leading 0) |
| `monto` | Double | `150000.00` | Amount |
| `motivo` | String(35) | `"Vuelto digital"` | Transaction description |
| `canal` | String | `"23"` | Channel code (23=BOTON DE PAGO) |
| `id-externo` | String | `"INV-2026-001"` | Idempotency key |

### Optional Fields

| Field | Description |
|-------|-------------|
| `cuenta` | Source account (default: Open Bank account) |
| `telefonoAfiliado` | Sender's registered phone |
| `moneda` | Currency ISO 4217 (VES, USD, EUR) |
| `sucursal` | Branch code |
| `cajero` | Cashier code |
| `caja` | Register code |
| `ipCliente` | Client IP (header) |
| `longitud` / `latitud` / `precision` | Geolocation (headers) |

### Response Codes (Key)

| Code | Description | HTTP |
|------|-------------|------|
| `0000` | TRANSACCION EXITOSA | 201 |
| `0002` | PARAMETRO OBLIGATORIO | 400 |
| `0051` | SALDO INSUFICIENTE | 400 |
| `E001` | CLIENTE NO REGISTRADO | 500 |
| `E023` | IDENTIF. DEL BENEFICIARIO NO COINCIDE | 400 |
| `A001` | FIRMA DIGITAL INVALIDA | 400 |
| `A004` | API-KEY INVALIDA O REVOCADA | 500 |

### Signing Algorithm

```
signature_input = "/{path}{nonce}{JSON.stringify(body)}"  // body only for POST
signature = HMAC-SHA384(signature_input, api_key_secret).hex()

Headers: Api-key, Nonce, Api-signature
```

---

## Open Questions

1. **Banco Plaza inbound API**: Must request documentation for payment reception/verification. Current API is outbound-only (P2P/P2C disbursements).

2. **Fiscal compliance**: Confirm UEIPAB's current SENIAT setup — fiscal printer or pre-printed invoice books? This determines how control numbers are assigned.

3. **Priority**: Start with virtual-only (WhatsApp + PDF download) before physical kiosk hardware? Lower cost to validate the concept.

4. **Vuelto digital scope**: Is the primary Banco Plaza use case sending change back to customers, or also collecting payments programmatically?

5. **Employee auth on kiosk**: Should employees use cedula (same as customers) or a different method (employee badge, PIN)?
