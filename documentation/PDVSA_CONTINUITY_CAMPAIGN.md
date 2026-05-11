# PDVSA Continuity Campaign — Período 2026-2027

**Status:** Testing (email sent 2026-05-11, WA tracking pending)
**Created:** 2026-05-11
**Module:** `ueipab_attendance_report` v17.0.1.6.0
**Script:** `scripts/send_pdvsa_communication.py`

---

## Overview

Mass communication to parents tagged **"Representante PDVSA"** informing them of the end of the 35% discretionary discount (effective September 1, 2026) and asking whether they intend to continue in the institution for 2026-2027.

Each parent receives a personalized email with two one-click decision links. Responses are tracked in Odoo and CC'd to `votacion@ueipab.edu.ve`.

---

## Campaign Parameters

| Parameter | Value |
|---|---|
| `notice_key` | `pdvsa_continuacion_2026_2027` |
| Partner tag | `Representante PDVSA` (id=26 testing, check prod) |
| Decision deadline | **Monday, June 8, 2026 — 12:30 p.m.** |
| Default if no response | Auto-accepted (new conditions apply) |
| Sender | `Colegio Andrés Bello <votacion@ueipab.edu.ve>` |
| Reply-to | `votacion@ueipab.edu.ve` |
| CC (outbound + ACK) | `votacion@ueipab.edu.ve` |
| Testing ack_id | 2 (Gustavo Perdomo) |

---

## Partner Coverage (Testing DB Snapshot — 2026-05-11)

| Metric | Count |
|---|---|
| Total PDVSA partners (active) | 74 |
| With email | 68 |
| With mobile phone | 65 |
| With phone (landline) | 23 |

---

## Architecture

### Model: `partner.communication.ack`

Lives in `ueipab_attendance_report`. One record per partner per `notice_key`.

| Field | Type | Notes |
|---|---|---|
| `notice_key` | Char | `pdvsa_continuacion_2026_2027` |
| `notice_label` | Char | Human-readable title |
| `partner_id` | Many2one `res.partner` | Cascades on delete |
| `partner_name` | Char | Snapshot at send time |
| `partner_email` | Char | Snapshot at send time |
| `token` | Char | UUID, auto-generated, public ACK links |
| `state` | Selection | `pending` / `continuing` / `leaving` |
| `sent_date` | Datetime | When email was sent |
| `ack_date` | Datetime | When parent clicked |
| `ack_ip` | Char | IP at click time |

### Public Routes

| Route | Action |
|---|---|
| `GET /partner-ack/<token>/si` | Records `state=continuing`, shows success page |
| `GET /partner-ack/<token>/no` | Records `state=leaving`, shows success page |
| `GET /partner-ack/<token>` | Landing page with both buttons (fallback) |

All routes fire `_send_ack_confirmation()` → email to partner + CC `votacion@`.

### Nginx

Added to `dev.ueipab.edu.ve` proxy pattern (line 183):
```
^/(... |partner-ack)(/|$)
```
**Production:** same change needed on `10.124.0.3` nginx config.

### HR Tracking

**Payroll → Reports → Comunicados a Representantes**
— list view with state badges, days pending, filters by decision, group by campaign key.

---

## Send Script

```bash
# Dry run (default) — shows who would be sent to, no records created
docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http \
  < /opt/odoo-dev/scripts/send_pdvsa_communication.py

# Live — all PDVSA partners with email
{ echo "import os; os.environ['LIVE']='true'"; \
  cat /opt/odoo-dev/scripts/send_pdvsa_communication.py; } \
  | docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http

# Live — single partner (for test)
{ echo "import os; os.environ['LIVE']='true'; os.environ['PARTNER_ID']='3676'"; \
  cat /opt/odoo-dev/scripts/send_pdvsa_communication.py; } \
  | docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http
```

Script is idempotent — re-running skips partners who already have a record for this `notice_key`.

---

## Production Deployment Checklist

| Step | Action |
|---|---|
| 1 | Copy `ueipab_attendance_report` v17.0.1.6.0 to `/home/vision/ueipab17/addons` |
| 2 | `docker exec 0ef7d03db702_ueipab17 /usr/bin/odoo -d DB_UEIPAB -u ueipab_attendance_report --stop-after-init --http-port=18069` |
| 3 | Add `partner-ack` to prod nginx Odoo location regex + `nginx -s reload` |
| 4 | Verify `https://odoo.ueipab.edu.ve/partner-ack/test-token` returns 404-style page (not 502) |
| 5 | Run send script with `PARTNER_ID=<gustavo_prod_id> LIVE=true` for one-off test |
| 6 | Run full blast Friday morning VET |

---

## Pending: Glenda WA Tracking (Capabilities 2 & 3)

### Capability 2 — WA Reminder Blast (Script)

**Status:** Pending implementation
**Target run date:** June 3–5, 2026 (3–5 days before deadline)

A standalone host script that sends a WhatsApp nudge to every PDVSA partner with `state=pending` whose initial email was sent more than 7 days ago.

#### Script: `scripts/send_pdvsa_wa_reminders.py`

**Logic:**
1. Connect to Odoo via XML-RPC (prod env file)
2. Query `partner.communication.ack` → `state=pending` + `sent_date < now - 7 days` + `notice_key = pdvsa_continuacion_2026_2027`
3. For each record: look up `res.partner.mobile` (fallback `phone`), normalize to `+58` format
4. Build WA message with direct YES/NO deep-links
5. POST to MassivaMóvil `/api/send/whatsapp`
6. Respect 120 s anti-spam delay between sends
7. Log result per partner

**WA message template:**
```
Hola {first_name} 👋

Le recordamos que tiene pendiente confirmar su continuidad en el
*Colegio Andrés Bello* para el período 2026-2027.

📅 *Fecha límite: lunes 08 de junio a las 12:30 p.m.*

Por favor confirme su decisión:
✅ Continuaré → {si_url}
❌ No continuaré → {no_url}

¿Preguntas? Escríbanos a votacion@ueipab.edu.ve
```

**Coverage (from current data):** 65 of 74 PDVSA partners have mobile; remainder may have landline only — those are skipped with a warning log.

**Key implementation details:**
- Source creds from `/root/.odoo_agent_env_prod` (or `--env testing`)
- WA config from `/opt/odoo-dev/config/whatsapp_massiva.json`
- DRY_RUN=true default
- `--partner-id N` for single-partner test
- Skip partners who already responded (`state != pending`)
- Normalize Venezuelan numbers: `04XX-XXXXXXX` → `+58 4XX XXXXXXX`
- Do NOT record a new `mail.mail` — this is WA-only

**Run command:**
```bash
# Dry run
python3 /opt/odoo-dev/scripts/send_pdvsa_wa_reminders.py

# Live (all pending)
LIVE=true python3 /opt/odoo-dev/scripts/send_pdvsa_wa_reminders.py --env production

# Test with one partner
LIVE=true python3 /opt/odoo-dev/scripts/send_pdvsa_wa_reminders.py \
  --env production --partner-id <id>
```

---

### Capability 3 — Glenda HR Query Interface

**Status:** Pending implementation
**Module:** `ueipab_ai_agent` — `general_inquiry` skill
**File:** `addons/ueipab_ai_agent/skills/general_inquiry.py`

Glenda answers HR staff questions like *"¿Cuántos PDVSA respondieron la encuesta?"* using live counts from `partner.communication.ack`.

#### Implementation

Add `_build_pdvsa_survey_context()` to `general_inquiry.py`:

```python
def _build_pdvsa_survey_context(self):
    """Return a text block with live PDVSA survey stats for the system prompt."""
    try:
        Ack = self.env['partner.communication.ack']
        notice_key = 'pdvsa_continuacion_2026_2027'
        total      = Ack.search_count([('notice_key', '=', notice_key)])
        pending    = Ack.search_count([('notice_key', '=', notice_key), ('state', '=', 'pending')])
        si_count   = Ack.search_count([('notice_key', '=', notice_key), ('state', '=', 'continuing')])
        no_count   = Ack.search_count([('notice_key', '=', notice_key), ('state', '=', 'leaving')])
        return (
            f"ENCUESTA PDVSA 2026-2027 (cierre 08-Jun): "
            f"{si_count} continuarán, {no_count} no continuarán, "
            f"{pending} sin respuesta de {total} enviados."
        )
    except Exception:
        return ""
```

Inject into `get_context()` inside the `_INSTITUTIONAL_KNOWLEDGE` block, after the BCV rate block:

```python
pdvsa_block = self._build_pdvsa_survey_context()
if pdvsa_block:
    knowledge_lines.append(pdvsa_block)
```

**Sample HR ↔ Glenda exchange:**
> **HR:** ¿Cuántos representantes PDVSA han respondido la encuesta?
> **Glenda:** Hasta ahora: 12 confirmaron que continuarán, 3 indicaron que no continuarán, y 53 aún no han respondido. El cierre es el lunes 08 de junio.

**Notes:**
- Stats reflect the state at conversation start, not real-time mid-conversation
- Only available in `general_inquiry` skill (24/7, HR-facing)
- Depends on `partner.communication.ack` model — if `ueipab_attendance_report` not installed, returns empty string (graceful fallback)
- No new Odoo module changes needed — `general_inquiry.py` edits only

---

## Status Summary

| Component | Status | Notes |
|---|---|---|
| `partner.communication.ack` model | ✅ Done | v17.0.1.6.0 |
| Public ACK routes `/partner-ack/` | ✅ Done | nginx updated (dev) |
| HR tracking view | ✅ Done | Payroll → Reports menu |
| Send script (email) | ✅ Done | `send_pdvsa_communication.py` |
| Confirmation CC email on ACK | ✅ Done | `votacion@` auto-CC |
| School logo in email | ✅ Done | `dev.ueipab.edu.ve/flyers/ueipab_logo.png` |
| Production deployment | ⏳ Pending | See checklist above |
| Capability 2 — WA reminders | ⏳ Pending | Run Jun 3–5 |
| Capability 3 — Glenda stats | ⏳ Pending | `general_inquiry.py` edit |
