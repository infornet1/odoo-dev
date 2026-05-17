# CEO Command Center (wa_monitor)

Real-time monitoring alerts to CEO via two channels:
- **Odoo Discuss** (OdooBot DM) — primary, instant, no throttle; via `wa_monitor.ceo_email`
- **WA +584248944898** — secondary, subject to 120s anti-spam throttle; via `wa_monitor.ceo_phone`

---

## Config Params (ir.config_parameter)

| Key | Value |
|-----|-------|
| `wa_monitor.ceo_email` | `gustavo.perdomo@ueipab.edu.ve` |
| `wa_monitor.ceo_phone` | `+584248944898` |
| `wa_monitor.tertiary_notified_ids` | JSON list of already-notified tertiary WA message IDs (dedup, rolling 500) |

---

## Events That Trigger CEO Alert

Defined in `ai_agent_conversation.py`:

| Event | Method | Trigger point |
|---|---|---|
| Customer with balance contacts Glenda | `_notify_ceo` | `_get_or_create_general_inquiry_conversation` after creation |
| Glenda escalation | `_notify_ceo` | `_handle_escalation` |
| Handoff to Pagos/Soporte | `_notify_ceo` | `action_process_reply` resolve block |
| Message received on tertiary (+58 414-832-1963) | `_notify_ceo_tertiary` | `_cron_poll_messages` non-primary guard |

### Script-level Alerts (standalone scripts)

| Script | Event | Channel |
|---|---|---|
| `wa_invoice_reminder.py` | WA blast start + end summary | WA (`wa_monitor.ceo_phone`) |
| `pagos_receipt_processor.py` | Payment confirmed | WA (MassivaMóvil direct) |
| `dmarc_report_processor.py` | Unknown IP **passing** DMARC | OdooBot DM (instant) + Email digest |

---

## Implementation Details

**OdooBot Discuss method (in-module):** `_notify_ceo_discuss(message, ceo_email)` in `ai_agent_conversation.py` — SQL lookup of CEO's OdooBot DM channel, creates if missing, posts as `base.partner_root`.

**OdooBot Discuss from standalone scripts:** use `discuss.channel` (Odoo 17 rename from `mail.channel`) and `discuss.channel.member`. Pattern: find CEO partner → find OdooBot partner (`base.partner_root` via `ir.model.data`) → intersect channel search results → create if no shared channel → `message_post`. See `notify_ceo_discuss()` in `scripts/dmarc_report_processor.py` for the canonical XML-RPC implementation.

**Tertiary dedup:** `_notify_ceo_tertiary` checks `wa_monitor.tertiary_notified_ids` before notifying; saves wa_id after notifying to prevent repeated alerts on same message across poll cycles.

---

## DMARC Daily Monitor

**Script:** `scripts/dmarc_report_processor.py`
**Cron:** `/etc/cron.d/dmarc_processor` — daily 06:30 VET (10:30 UTC)

Processes DMARC aggregate-report emails that land in FreeScout finanzas@ (mailbox_id=5):

| Scenario | Action |
|---|---|
| All legit + blocked | Parse XML → add HTML note → close conversation → email digest only |
| Akdemia/known third-party (blocked) | Same + 🔍 note in digest |
| Unknown IP passing DMARC | Same + ⚠️ OdooBot DM alert (immediate) |

**Alert threshold:** `suspicious_passing` — any IP not in known-good ranges (`209.85/16`, `74.125/16`, Google IPv6, `64.23.157.121`) with `disposition=none` (i.e., not blocked by DMARC).

**Known providers reporting:** Google (`noreply-dmarc-support@google.com`), Microsoft (`dmarcreport@microsoft.com`), Yahoo (`dmarchelp@yahooinc.com`).

**Akdemia note:** `50.31.44.87` (SendGrid) appears in reports sending with `From: ueipab.edu.ve` but `MAIL FROM: em.akdemia.com` → DMARC misalignment → blocked. Not a security issue but Akdemia should be asked to use a subdomain or proper DKIM alignment.
