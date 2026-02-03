# Email Bounce Processor

**Status:** Planned | **Type:** Standalone Script + Future Odoo Module

## Overview

Automated system to detect bounced emails from Freescout, clean up Odoo contacts, notify support team, and maintain a queryable bounce history. Freescout is treated as a **READ-ONLY** source -- the script never writes to the Freescout database.

## Goals

1. **Detect & Remove**: Read bounced emails from Freescout MySQL (read-only) and surgically remove only the bounced email from Odoo contacts (`res.partner` and `mailing.contact`)
2. **Flag to Support**: Send HTML report email to `soporte@ueipab.edu.ve` with affected contact details and Odoo links
3. **Mailing List Cleanup**: Also remove bounced email from `mailing.contact` records to prevent future campaign failures

## Architecture

```
Freescout MySQL ──(READ-ONLY)──> daily_bounce_processor.py
                                        │
                                        ├──(XML-RPC WRITE)──> Production Odoo
                                        │   ├── res.partner (remove bounced email)
                                        │   ├── mailing.contact (remove bounced email)
                                        │   └── chatter note (audit trail)
                                        │
                                        ├──(SMTP)──> soporte@ueipab.edu.ve (report)
                                        │
                                        └──(LOCAL)──> bounce_log.csv (queryable history)
                                                      bounce_state.json (last processed ID)
```

**Critical Rule:** The script NEVER writes, updates, or deletes anything in the Freescout database.

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
   - Query Type 1: Standalone DSN bounce conversations
   - Query Type 2: Inline bounce threads (postmaster@/mailer-daemon@)
   - Extract bounced email addresses from HTML body
   - Skip already-processed conversations (via `bounce_state.json`)

2. **Connect to Production Odoo via XML-RPC**
   - Search `res.partner` by bounced email
   - Search `mailing.contact` by bounced email
   - For each match: surgically remove only the bounced email, preserve others
   - Log old email in contact's chatter (internal note) for audit trail

3. **Send Report to soporte@ueipab.edu.ve**
   - HTML formatted email with:
     - Contact name + removed email + bounce reason
     - Direct Odoo link: `/web#id=XXX&model=res.partner&view_type=form`
     - Summary statistics

4. **Update Local State**
   - Append to `bounce_log.csv`
   - Save last processed ID to `bounce_state.json`

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
date,bounced_email,partner_id,partner_name,mailing_contact_id,bounce_reason,freescout_conversation_id
2026-02-03,maria@hotmail.com,1234,Maria Lopez,567,mailbox_full,8901
```

Support team can query via terminal or open in Excel/Google Sheets.

### Execution

```bash
# Manual
python3 /opt/odoo-dev/scripts/daily_bounce_processor.py

# Cron (daily at 7 AM)
0 7 * * * python3 /opt/odoo-dev/scripts/daily_bounce_processor.py >> /var/log/bounce_processor.log 2>&1
```

---

## Phase 2: Odoo Module (Future)

**Module:** `ueipab_bounce_log` | **Depends:** `contacts`, `mail`

To be implemented alongside the WhatsApp AI agent integration. The module extends the existing Contacts app (not a standalone app).

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

### WhatsApp AI Agent Integration (Future)

When implemented, the WhatsApp agent will:
1. Query `mail.bounce.log` for records in `pending` state
2. Look up contact's phone/mobile from `res.partner`
3. Send WhatsApp message asking for new/alternative email
4. On customer reply: update `new_email`, trigger "Aplicar Nuevo Email" action
5. Set state to `Resuelto`

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

### What We NEVER Do

- Insert, update, or delete any Freescout records
- Mark conversations as processed in Freescout
- Close or modify Freescout conversations
- Create Freescout tags, notes, or any other data

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
