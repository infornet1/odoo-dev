# PDVSA Continuity Campaign — Período 2026-2027

**Status:** Testing complete ✅ — Production deploy pending Friday 2026-05-15
**Created:** 2026-05-11
**Module:** `ueipab_attendance_report` v17.0.1.6.0
**Script:** `scripts/send_pdvsa_communication.py`
**Deploy runbook:** [PDVSA_DEPLOY_FRIDAY_20260515.md](PDVSA_DEPLOY_FRIDAY_20260515.md)

---

## Overview

Mass communication to parents tagged **"Representante PDVSA"** informing them of the end
of the 35% discretionary discount (effective September 1, 2026) and asking whether they
intend to continue in the institution for 2026-2027.

Each parent receives a personalized email with three stacked full-width buttons
(read letter → yes → no). Responses are tracked in Odoo and CC'd to `votacion@ueipab.edu.ve`.

---

## Campaign Parameters

| Parameter | Value |
|---|---|
| `notice_key` | `pdvsa_continuacion_2026_2027` |
| Partner tag | `Representante PDVSA` (id=**26** — confirmed same in testing and production) |
| Decision deadline | **Monday, June 8, 2026 — 12:30 p.m.** |
| Default if no response | Auto-accepted (new conditions apply for 2026-2027) |
| Sender | `Colegio Andrés Bello <votacion@ueipab.edu.ve>` |
| Reply-to | `votacion@ueipab.edu.ve` |
| CC on every outbound email | `votacion@ueipab.edu.ve` |
| CC on every ACK confirmation | `votacion@ueipab.edu.ve` |
| Full letter link | [Google Doc](https://docs.google.com/document/d/1z9_Dr3qvWdytEcrDUCp7NcVoJQHq4MKiveNoV_kC2jE/edit?tab=t.0) |

---

## Partner Coverage

| Metric | Testing | Production (confirmed 2026-05-11) |
|---|---|---|
| Total PDVSA partners (active) | 74 | — |
| With email | 68 | **71** |
| With mobile phone | 65 | — |
| PDVSA tag id | 26 | **26** |
| Test partner | id=3676 Gustavo Perdomo | id=7 Gustavo Perdomo |

---

## Email Design (current — v3)

Decision-first layout. Buttons are visible **above the fold** on mobile without scrolling.

```
[LOGO — navy header]
¿Continuará en el Colegio para el período 2026-2027?
Estimado(a) {name}, le comunicamos un cambio importante...

┌─────────────────────────────────────────┐
│  📄  Ver comunicado completo            │  ← navy ghost (opens Google Doc)
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│  ✓  Sí, continuaré en 2026-2027        │  ← navy solid → /partner-ack/<token>/si
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│  No continuaré                          │  ← gray solid → /partner-ack/<token>/no
└─────────────────────────────────────────┘

📅 Fecha límite: lunes 08 de junio de 2026 — 12:30 p.m.
   (amber callout — "si no responde, se asume aceptación")

• Bullet 1: descuento 35% finaliza 1° sep 2026
• Bullet 2: ajuste matrícula estimado 20–34% para 2026-2027
• Bullet 3: Casos Especiales evaluados individualmente → votacion@

La Administración — Colegio "Andrés Bello" | 08 mayo 2026
[FOOTER — navy]
```

**Key UX decisions:**
- Ghost button first = "read the letter before deciding" flow
- All buttons full-width stacked = no mobile cramping, no misclick between YES/NO
- Full letter text removed from email body — linked via Google Doc instead

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
| `token` | Char | UUID, auto-generated |
| `state` | Selection | `pending` / `continuing` / `leaving` |
| `sent_date` | Datetime | When email was sent |
| `ack_date` | Datetime | When parent clicked |
| `ack_ip` | Char | IP at click time |

### Public Routes

| Route | Action |
|---|---|
| `GET /partner-ack/<token>/si` | Records `state=continuing`, shows success, fires ACK confirmation email |
| `GET /partner-ack/<token>/no` | Records `state=leaving`, shows success, fires ACK confirmation email |
| `GET /partner-ack/<token>` | Landing page with all 3 buttons (fallback if no direct link click) |

ACK confirmation email → partner + CC `votacion@ueipab.edu.ve`.

### Nginx

Added to `dev.ueipab.edu.ve` proxy pattern (and `glenda-calibracion` was also fixed):
```
^/(web|...|notice-ack|glenda-calibracion|employee-info|partner-ack)(/|$)
```
**Production:** same pattern needed on `10.124.0.3` — covered in deploy runbook.

### HR Tracking View

**Payroll → Reports → Comunicados a Representantes**
— list with state badges (`pending`/`continuing`/`leaving`), days pending, filters, group by campaign key.

---

## Send Script

`scripts/send_pdvsa_communication.py` — Odoo shell script (stdin pipe pattern).

```bash
# Dry run (default) — lists recipients, no records created
docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http \
  < /opt/odoo-dev/scripts/send_pdvsa_communication.py

# Live — all PDVSA partners with email
{ echo "import os; os.environ['LIVE']='true'"; \
  cat /opt/odoo-dev/scripts/send_pdvsa_communication.py; } \
  | docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http

# Live — single partner (for test, replace PARTNER_ID)
{ echo "import os; os.environ['LIVE']='true'; os.environ['PARTNER_ID']='3676'"; \
  cat /opt/odoo-dev/scripts/send_pdvsa_communication.py; } \
  | docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http
```

**Idempotent** — re-running skips partners who already have a record for this `notice_key`.

---

## Testing History

| Date | Action | Result |
|---|---|---|
| 2026-05-11 | v1 sent (full letter body) | mail_id=1042, ack_id=1 ✅ |
| 2026-05-11 | v2: votacion@ sender + CC + logo + subject | mail_id=1043, ack_id=2 ✅ |
| 2026-05-11 | v3: redesign — decision-first, 3 bullets | mail_id=1044, ack_id=3 ✅ |
| 2026-05-11 | v4: ghost button first, stacked full-width | mail_id=1045, ack_id=4 ✅ sent to perdomo.gustavo@gmail.com |

---

## Production Deployment

**Target: Friday 2026-05-15, ~9:00 AM VET**

See full step-by-step runbook: **[PDVSA_DEPLOY_FRIDAY_20260515.md](PDVSA_DEPLOY_FRIDAY_20260515.md)**

Summary:
1. Backup DB_UEIPAB
2. Copy + upgrade `ueipab_attendance_report` v17.0.1.5.2 → v17.0.1.6.0
3. Add `partner-ack` to prod nginx location regex
4. Test send to partner id=7 (Gustavo, `gustavo.perdomo@ueipab.edu.ve`)
5. Full blast — **71 partners**

---

## Pending: Glenda WA Tracking (Capabilities 2 & 3)

### Capability 2 — WA Reminder Blast (Script)

**Status:** Pending implementation
**Target run date:** June 3–5, 2026 (3–5 days before deadline)

Script: `scripts/send_pdvsa_wa_reminders.py` (to be created)

**Logic:**
1. Connect to Odoo via XML-RPC (prod env file)
2. Query `partner.communication.ack` → `state=pending` + `sent_date < now - 7 days` + `notice_key = pdvsa_continuacion_2026_2027`
3. For each: look up `res.partner.mobile` (fallback `phone`), normalize to `+58` format
4. Send WA via MassivaMóvil with direct YES/NO deep-links
5. Respect 120 s anti-spam delay between sends

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

**Coverage:** 65 of 74 testing partners have mobile. Production TBD.

**Run command:**
```bash
LIVE=true python3 /opt/odoo-dev/scripts/send_pdvsa_wa_reminders.py --env production
```

---

### Capability 3 — Glenda HR Query Interface

**Status:** Pending implementation
**File to edit:** `addons/ueipab_ai_agent/skills/general_inquiry.py`

Add `_build_pdvsa_survey_context()` method — queries `partner.communication.ack` counts
and injects live stats into Glenda's system prompt `_INSTITUTIONAL_KNOWLEDGE` block.

```python
def _build_pdvsa_survey_context(self):
    try:
        Ack = self.env['partner.communication.ack']
        key = 'pdvsa_continuacion_2026_2027'
        total   = Ack.search_count([('notice_key', '=', key)])
        pending = Ack.search_count([('notice_key', '=', key), ('state', '=', 'pending')])
        si      = Ack.search_count([('notice_key', '=', key), ('state', '=', 'continuing')])
        no      = Ack.search_count([('notice_key', '=', key), ('state', '=', 'leaving')])
        return (
            f"ENCUESTA PDVSA 2026-2027 (cierre 08-Jun): "
            f"{si} continuarán, {no} no continuarán, "
            f"{pending} sin respuesta de {total} enviados."
        )
    except Exception:
        return ""
```

**Sample HR ↔ Glenda exchange:**
> **HR:** ¿Cuántos representantes PDVSA han respondido la encuesta?
> **Glenda:** Hasta ahora: 12 confirmaron continuidad, 3 no continuarán, 56 aún no han respondido. Cierre el 08 de junio.

---

## Status Summary

| Component | Status |
|---|---|
| `partner.communication.ack` model | ✅ Testing |
| Public ACK routes `/partner-ack/` | ✅ Testing (nginx updated) |
| HR tracking view | ✅ Testing |
| Send script (email, 3-button design) | ✅ Testing — 4 iterations, final v4 sent |
| CC `votacion@` on outbound + ACK | ✅ Verified |
| School logo in email header | ✅ `dev.ueipab.edu.ve/flyers/ueipab_logo.png` |
| Production deploy | ⏳ **Friday 2026-05-15** |
| Capability 2 — WA reminders | ⏳ Implement before Jun 3 |
| Capability 3 — Glenda stats | ⏳ Pending |
