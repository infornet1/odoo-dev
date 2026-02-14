# Email Bounce Processor

**Status:** Testing (Phase 1) | **Type:** Standalone Script + Odoo Module

## Overview

Automated system to detect bounced emails from Freescout, clean up Odoo contacts, notify support team, and maintain a queryable bounce history. Freescout is treated as a read-only source for bounce detection; optional post-processing writes subject prefixes, internal notes, and closes conversations. WhatsApp AI agent integration (via MassivaMóvil API) is planned for automated customer outreach.

## Goals

1. **Detect & Clean**: Read bounced emails from Freescout MySQL (read-only) and surgically remove only the bounced email from Representante-tagged Odoo contacts (`res.partner` and `mailing.contact`)
2. **Flag for Review**: Non-Representante bounces are flagged for manual review (not auto-cleaned)
3. **Mailing List Cleanup**: Also remove bounced email from `mailing.contact` records linked to Representante partners
4. **Audit Trail**: Maintain CSV log and chatter notes on all affected contacts

## 3-Tier Processing Logic (Reason + Tag Based)

| Tier | Condition | Action |
|------|-----------|--------|
| **CLEAN** | Representante partner + **permanent** failure (`invalid_address`, `domain_not_found`) | Remove email from `res.partner` + `mailing.contact`, post chatter note |
| **FLAG** | **Temporary** failure (`mailbox_full`, `rejected`, `other`) regardless of tags, OR non-Representante partner (any reason) | Log for manual review (no auto-modification) |
| **NOT FOUND** | Bounced email not found in Odoo at all | CSV log only |

**Key design decision:** Temporary failures like `mailbox_full` are NEVER auto-cleaned because the customer may fix the issue (clear inbox, respond to WhatsApp outreach). Only permanent failures where the email will never work again are auto-cleaned.

**Scope filters:**
- Only processes bounces from last **180 days** (6-month rolling window)
- Representante tags: `Representante` (ID 25), `Representante PDVSA` (ID 26)

## Architecture

```
Freescout MySQL ──(READ-ONLY)──> daily_bounce_processor.py
                                        │
                                        ├── TIER 1: CLEAN (Representante)
                                        │   ├──(XML-RPC WRITE)──> res.partner (remove bounced email)
                                        │   ├──(XML-RPC WRITE)──> mailing.contact (remove bounced email)
                                        │   └──(XML-RPC WRITE)──> chatter note (audit trail)
                                        │
                                        ├── TIER 2: FLAG (non-Representante)
                                        │   └──(LOCAL)──> CSV log + report section
                                        │
                                        ├── TIER 3: NOT FOUND
                                        │   └──(LOCAL)──> CSV log only
                                        │
                                        └──(LOCAL)──> bounce_log.csv (queryable history)
                                                      bounce_state.json (last processed ID)
```

**Note:** As of v1.1.0, the script optionally writes to Freescout for post-processing (subject prefix, internal note, status change). Controlled by `FREESCOUT_POSTPROCESS` flag.

## Phase 1: Standalone Script (Current)

### Location

```
/opt/odoo-dev/scripts/
├── daily_bounce_processor.py    ← main script
├── bounce_state.json            ← auto-created, tracks last processed Freescout ID
└── bounce_logs/
    └── bounce_log.csv           ← append-only history for support team queries
```

### Script Flow

1. **Read Freescout MySQL** (read-only connection)
   - Query Type 1: Standalone DSN bounce conversations (subject LIKE `%Undelivered%` or `%Delivery Status%`)
   - Query Type 2: Inline bounce threads (from `postmaster@` or `mailer-daemon@`)
   - Date filter: only bounces from last 180 days (`BOUNCE_WINDOW_DAYS`)
   - Extract bounced email addresses from HTML body (supports Google, Outlook, MailChannels formats)
   - Deduplicate: only process first occurrence of each email
   - Skip already-processed conversations (via `bounce_state.json`)

2. **Connect to Odoo via XML-RPC** (production or testing)
   - For each bounced email, search `res.partner` by email (ilike)
   - Check partner tags to determine tier:
     - **Representante/Representante PDVSA** → TIER 1: CLEAN (remove email, clean mailing.contact, post chatter)
     - **Other tags or no tags** → TIER 2: FLAG (log for review, no modification)
   - If no partner found, search `mailing.contact`:
     - Found → FLAG for review
     - Not found → TIER 3: NOT FOUND (CSV log only)

3. **Update Local State**
   - Append to `bounce_log.csv` (with action column: cleaned/flagged/not_found)
   - Save last processed ID to `bounce_state.json`
   - Print detailed report with separate sections per tier

### Multi-Email Handling

Contacts may have multiple emails separated by `;`. The script **surgically removes only the bounced email** and preserves the rest.

```python
# Example: contact has "juan@gmail.com;maria@hotmail.com;pedro@yahoo.com"
# maria@hotmail.com bounced

BEFORE:  "juan@gmail.com;maria@hotmail.com;pedro@yahoo.com"
AFTER:   "juan@gmail.com;pedro@yahoo.com"
```

Edge cases handled:
- Single email → field cleared
- Multiple emails, one bounced → only bounced removed
- Case-insensitive matching
- Extra spaces trimmed
- All emails bounced → field cleared

### Chatter Audit Trail

Before modifying any contact, the script posts an internal note:

```
Email rebotado removido: maria@hotmail.com
Razon: Buzon lleno (550 5.2.1 mailbox full)
Antes: juan@gmail.com;maria@hotmail.com;pedro@yahoo.com
Despues: juan@gmail.com;pedro@yahoo.com
Fuente: Freescout Conversation #8901
Fecha: 03/02/2026 07:00
```

### CSV Log Format

```csv
date,bounced_email,partner_id,partner_name,mailing_contact_id,bounce_reason,freescout_conversation_id,action,tags,notes
2026-02-05,maria@hotmail.com,1234,Maria Lopez,,mailbox_full,8901,cleaned,Representante,res.partner cleaned
2026-02-05,staff@ueipab.edu.ve,2711,MONICA MOSQUEDA,,mailbox_full,33301,flagged,,Flagged for review (res.partner)
2026-02-05,unknown@example.com,,,,,34071,not_found,,Not found in Odoo
```

Support team can query via terminal or open in Excel/Google Sheets.

### Execution

```bash
# Manual
python3 /opt/odoo-dev/scripts/daily_bounce_processor.py

# Cron (daily at 7 AM)
0 7 * * * python3 /opt/odoo-dev/scripts/daily_bounce_processor.py >> /var/log/bounce_processor.log 2>&1
```

### Testing Notes (2026-02-03)

Phase 1 script verified in testing environment (`localhost:8019`, db=`testing`):

- **TEST_MODE**: Uses 4 simulated bounces (no Freescout connection needed)
- **DRY_RUN=True**: Prints what WOULD change, creates CSV with `[DRY_RUN]` prefix
- **DRY_RUN=False**: Verified live modifications:
  - Single-email partner: email field cleared correctly
  - Multi-email partner: only bounced email removed, others preserved (`keep.this@example.com;also.keep@example.com`)
  - Mailing contact: email field cleared correctly
  - Non-existent email: correctly reported as "Not found"
  - Chatter notes posted with proper HTML formatting (audit trail)
  - `bounce_state.json` created with last processed conversation ID
  - `bounce_log.csv` created with all entries

**Auth note**: XML-RPC authentication requires an API key (not password) due to `login_user_detail` module incompatibility with XML-RPC context. A patch was applied to that module to handle the `request.httprequest` RuntimeError gracefully.

### Production Dry Run Results (2026-02-05)

Script executed with `DRY_RUN=True` against production (`DB_UEIPAB`) using reason-based 3-tier logic:

- **429 total bounces** detected from Freescout (6-month window)
- **49 unique emails** after deduplication

| Tier | Count | Description |
|------|-------|-------------|
| CLEAN | 11 partners, 12 mailing contacts | Representante + permanent failure (invalid_address/domain_not_found) |
| FLAG (temporary) | 13 records | Representante + temporary failure (mailbox_full/other) |
| FLAG (non-rep) | 14 records | Non-Representante or mailing.contact only |
| NOT FOUND | 13 emails | Not in Odoo at all |

**Key findings:**
- Only **permanent** failures auto-cleaned: 6 invalid_address + 5 domain_not_found (all PDVSA)
- 13 Representante partners with **mailbox_full** flagged for review (customer may fix/respond)
- All PDVSA domain bounces (`pdvsa.com`, `petropiar.pdvsa.com`) are permanent (DNS dead) → safe to clean
- Flagged non-Representante includes staff (`@ueipab.edu.ve`), "Inactivo" tagged, and orphan mailing.contacts

Full CSV export: `/home/ftpuser/odoo-dev/bounce_dry_run_2026-02-05.csv`

---

## Phase 2: Odoo Module (Installed in Testing)

**Module:** `ueipab_bounce_log` | **Version:** 17.0.1.4.0 | **Depends:** `contacts`, `mail`, `mass_mailing`

The module extends the existing Contacts app (not a standalone app). WhatsApp AI agent integration is planned for a future phase.

### Testing Notes (2026-02-03)

Module installed and verified in testing environment (`localhost:8019`, db=`testing`):

- **Menu:** `Contacts > Bounce Log` confirmed visible (parent: Contactos, sequence 5)
- **Security:** Admin (full CRUD), Internal User (read-only) -- verified via `ir.model.access`
- **State transitions:** pending → notified → contacted → resolved -- all work correctly
- **Restaurar Email Original:** Re-appends bounced email using `;` separator, posts chatter note on partner
- **Aplicar Nuevo Email:** Appends new email using `;` separator, requires `new_email` field (UserError if empty)
- **Error handling:** Correctly prevents resolving already-resolved records, prevents applying without new email
- **Chatter audit trail:** Internal notes posted on `res.partner` with bounce details and resolution info
- **SQL constraint:** UNIQUE(freescout_conversation_id, bounced_email) prevents duplicate imports
- **Views:** Tree (with badge decorations), Form (with statusbar + resolution buttons), Search (with filters and group-by)

### Menu Location

```
Contacts (existing app)
├── Contacts          (existing)
├── Bounce Log        ← new direct submenu
└── Configuration     (existing)
```

### Model: `mail.bounce.log`

```python
class MailBounceLog(models.Model):
    _name = 'mail.bounce.log'
    _description = 'Email Bounce Log'
    _order = 'bounce_date desc'

    # Core bounce info
    bounce_date            = fields.Datetime('Fecha de Rebote', default=fields.Datetime.now)
    bounced_email          = fields.Char('Email Rebotado', required=True)
    bounce_reason          = fields.Selection([
        ('mailbox_full', 'Buzon Lleno'),
        ('invalid_address', 'Direccion Invalida'),
        ('domain_not_found', 'Dominio No Encontrado'),
        ('rejected', 'Rechazado por Servidor'),
        ('other', 'Otro'),
    ], string='Razon')
    bounce_detail          = fields.Text('Detalle Tecnico')

    # Links to Odoo records
    partner_id             = fields.Many2one('res.partner', 'Contacto')
    mailing_contact_id     = fields.Many2one('mailing.contact', 'Contacto Mailing')

    # Resolution workflow
    state = fields.Selection([
        ('pending', 'Pendiente'),
        ('notified', 'Soporte Notificado'),
        ('contacted', 'Cliente Contactado'),
        ('resolved', 'Resuelto'),
    ], default='pending', string='Estado')

    # Resolution fields
    new_email              = fields.Char('Email Nuevo')
    resolved_date          = fields.Datetime('Fecha Resolucion')
    resolved_by            = fields.Many2one('res.users', 'Resuelto Por')

    # Source tracking
    freescout_conversation_id = fields.Integer('Freescout Conversation ID')
    freescout_url          = fields.Char(compute='_compute_freescout_url')  # v1.1.0
    action_tier            = fields.Selection([                              # v1.1.0
        ('clean', 'Limpiado'), ('flag', 'Revision'), ('not_found', 'No Encontrado'),
    ], string='Accion del Script')

    # Akdemia family context (v1.4.0)
    akdemia_family_emails  = fields.Text('Contexto Familiar Akdemia')  # JSON

    # Future: WhatsApp agent fields
    whatsapp_contacted     = fields.Boolean('Contactado por WhatsApp')
    whatsapp_contact_date  = fields.Datetime('Fecha Contacto WhatsApp')
```

### Resolution Workflow

Support team resolves each bounce via two possible actions:

| Action | Button | When to Use | What It Does |
|--------|--------|-------------|--------------|
| Restore original | "Restaurar Email Original" | Temporary issue fixed (mailbox cleared) | Re-adds `bounced_email` back to contact's email field |
| Apply new email | "Aplicar Nuevo Email" | Permanent failure, customer gave new email | Adds `new_email` to contact's email field |

Both actions:
- Use multi-email `;` logic (append to existing, don't overwrite)
- Update both `res.partner` and `mailing.contact` if applicable
- Set state to `Resuelto`, auto-fill `resolved_date` and `resolved_by`
- Post change in contact's chatter

### State Flow

```
Pendiente → Soporte Notificado → Cliente Contactado → Resuelto
    │              │                      │
    │              │                      └── WhatsApp agent reached out
    │              └── Email sent to soporte@
    └── Email removed from contact
```

### UI Views

**List View** (filterable, searchable):
- Columns: Fecha, Email Rebotado, Contacto, Razon, Estado
- Filters: Pendiente, Resuelto, This Month, Last Month
- Group by: Razon, Estado

**Form View**:
- Contact link (clickable, opens partner form)
- Resolution section with both action buttons
- Technical detail (raw DSN error)

### WhatsApp AI Agent Integration (Planned)

Extends `ueipab_bounce_log` module to automate bounce resolution via WhatsApp conversations with customers.

**WhatsApp Provider:** MassivaMóvil API (`whatsapp.massivamovil.com`)
**AI Model:** Claude Haiku 4.5 via Anthropic API (~$0.005/conversation)
**Config files (gitignored):**
- `/opt/odoo-dev/config/whatsapp_massiva.json` - MassivaMóvil credentials + account
- `/opt/odoo-dev/config/anthropic_api.json` - Claude API key + model config

**Integration Flow:**
1. Query `mail.bounce.log` for records in `pending` state
2. Look up contact's phone/mobile from `res.partner`
3. Send WhatsApp message via `POST /api/send/whatsapp` asking for new/alternative email
4. Receive replies via webhook (`POST` to Odoo controller) or polling (`GET /api/get/wa.received`)
5. On customer reply: update `new_email`, trigger "Aplicar Nuevo Email" action
6. Set state to `Resuelto`

**API Endpoints Used:**

| Action | Method | Endpoint | Key Params |
|--------|--------|----------|------------|
| Send message | POST | `/send/whatsapp` | `secret`, `account` (unique_id), `recipient`, `message` |
| Validate number | GET | `/validate/whatsapp` | `secret`, `unique`, `phone` |
| Get received | GET | `/get/wa.received` | `secret`, `limit`, `page` |
| Get single msg | GET | `/get/wa.message` | `secret`, `id`, `type` |

**Webhook Payload (incoming WhatsApp):**
```
POST callback_url
  secret: "WEBHOOK_SECRET"
  type: "whatsapp"
  data[id]: 2
  data[wid]: "+584148321963"      // our account
  data[phone]: "+584121234567"    // sender phone
  data[message]: "Hello World!"
  data[attachment]: "url or null"
  data[timestamp]: 1645684231
```

**Approach:** Start with polling (simpler, no public URL needed for testing), add webhook for production real-time responses.

### Migration Path

Existing CSV log data from Phase 1 can be imported into the Odoo model as a one-time migration when the module is installed.

---

## Freescout Integration (READ-ONLY)

### What We Read

| Data | Source Table | Purpose |
|------|-------------|---------|
| Bounce conversations | `conversations` | Detect new bounces |
| Bounce thread content | `threads` | Extract bounced email + reason |
| Customer email | `customers` / `emails` | Cross-reference with Odoo |

### What We NEVER Do (Phase 1 - prior to v1.1.0)

- ~~Insert, update, or delete any Freescout records~~ (v1.1.0 adds optional post-processing)
- Mark conversations as processed in Freescout (state file used instead)

### Freescout Post-Processing (v1.1.0, optional)

When `FREESCOUT_POSTPROCESS = True`, after all bounces are processed:
- **Subject prefix:** `[LIMPIADO]`, `[REVISION]`, or `[NO ENCONTRADO]`
- **Customer email:** Set to the bounced email address
- **Status:** Closed (3) for all tiers (Odoo is the single resolution workspace)
- **Internal note:** HTML note with Odoo contact link, bounce log link, action details
- All writes are skipped in DRY_RUN mode

State tracking is handled entirely via the local `bounce_state.json` file.

### Bounce Detection Queries

**Type 1 - Standalone DSN conversations:**
```sql
SELECT id, subject, created_at
FROM conversations
WHERE subject LIKE '%Undelivered%' OR subject LIKE '%Delivery Status%'
  AND id > :last_processed_id
ORDER BY id ASC;
```

**Type 2 - Inline bounce threads:**
```sql
SELECT c.id, t.body, t.created_at
FROM threads t
JOIN conversations c ON t.conversation_id = c.id
WHERE (t.from LIKE '%postmaster@%' OR t.from LIKE '%mailer-daemon@%')
  AND t.id > :last_processed_thread_id
ORDER BY t.id ASC;
```

---

## Configuration

The script requires the following environment variables or config file:

```python
# Freescout MySQL (READ-ONLY)
FREESCOUT_DB_HOST = '...'
FREESCOUT_DB_USER = '...'       # read-only MySQL user
FREESCOUT_DB_PASSWORD = '...'
FREESCOUT_DB_NAME = 'freescout'

# Production Odoo (XML-RPC)
ODOO_URL = 'https://...'
ODOO_DB = 'DB_UEIPAB'
ODOO_USER = '...'
ODOO_PASSWORD = '...'

# SMTP for report email
SMTP_HOST = '...'
SMTP_PORT = 587
SMTP_USER = '...'
SMTP_PASSWORD = '...'
REPORT_EMAIL_TO = 'soporte@ueipab.edu.ve'
```
