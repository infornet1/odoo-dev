# PDVSA Continuity Campaign — Período 2026-2027

**Status:** Production live ✅ — 84 families emailed 2026-05-19 (enhanced send)
**See also:** [Representante campaign](REPRESENTANTE_CONTINUITY_CAMPAIGN.md) — same infrastructure, letter pending
**Created:** 2026-05-11 | **Updated:** 2026-05-19
**Module:** `ueipab_attendance_report` v17.0.1.6.5
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
| Sender (SMTP From) | `Colegio Andrés Bello <soporte@ueipab.edu.ve>` — Gmail SMTP requires authenticated account as From |
| Reply-to | `votacion@ueipab.edu.ve` — replies land at votacion@ mailbox |
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
| 2026-05-11 | v4: ghost button first, stacked full-width | mail_id=1045, ack_id=4 — not received (From=votacion@ rejected by Gmail SMTP) |
| 2026-05-11 | v5: fix From=soporte@ (authenticated), Reply-To=votacion@ | mail_id=1049, ack_id=5 ✅ delivered to perdomo.gustavo@gmail.com |

---

## Production Deployment

**Deployed:** 2026-05-15 (initial, 71 partners) + 2026-05-19 (enhanced re-send, 84 partners)

See full step-by-step runbook: **[PDVSA_DEPLOY_FRIDAY_20260515.md](PDVSA_DEPLOY_FRIDAY_20260515.md)**

### 2026-05-19 Enhanced Re-Send

Email enhanced with **📊 Nueva Propuesta Económica 2026-2027** section:
- Option A ($218.88) / Option B ($236.58) mini-cards
- Google Slides CTA → `16EmMb-8mMtnsvdLLnc4Cx8srhzDrzjrsOvNIcXvTkEA`
- WhatsApp + Telegram + pagos@ query channels
- **CC:** `pagos@ueipab.edu.ve` | **Reply-To:** `pagos@ueipab.edu.ve`
- Source: Customers spreadsheet col O=Yes + col C=ACTIVE → **84 families**
- Delivery: 71 sent / 13 outgoing at check → all 84 delivered by mail queue
- 1 mailto fallback — RAFAEL DUERTO (no Odoo partner)

---

## Pending: Glenda WA Tracking (Capabilities 2 & 3)

### Capability 2 — WA Reminder Blast (Script)

**Status:** Messages approved — script pending implementation
**Target run date:** June 3–5, 2026 (3–5 days before deadline)

Script: `scripts/send_pdvsa_wa_reminders.py` (to be created)

**Logic:**
1. Connect to Odoo via XML-RPC (prod env file)
2. Query `partner.communication.ack` → `state=pending` + `notice_key = pdvsa_continuacion_2026_2027`
3. For each: look up `res.partner.mobile` (fallback `phone`), normalize to `+58` format
4. Send WA via MassivaMóvil — Message 1 on first send; Message 2 as final reminder
5. Respect 120 s anti-spam delay between sends

---

#### Mensaje 1 — Anuncio principal (send after / alongside email)

```
Hola 👋 Estimado(a) representante,

Le escribimos para informarle que acaba de recibir un correo importante de nuestra parte con el asunto:

📧 "¿Continuará en el Colegio 2026-2027? + Propuesta Económica"

En él encontrará información sobre los cambios en la política de descuento para colaboradores PDVSA/Petropiar a partir del 1° de septiembre de 2026, así como la propuesta económica del nuevo período escolar.

Le pedimos que lo revise con calma y confirme su decisión antes del *lunes 08 de junio de 2026 a las 12:30 p.m.*

📌 No lo encuentra? Revise su carpeta de *spam* o escríbanos aquí.

ℹ️ *Nota:* Se evaluarán *Casos Especiales* para familias con estudiantes de méritos destacados (académico, deportivo, artístico). Si es su caso, indíquelo a votacion@ueipab.edu.ve

Instituto Privado "Andrés Bello" 🏫
```

---

#### Mensaje 2 — Recordatorio final (send June 5–6, days before deadline)

```
⏰ Recordatorio — *08 de junio, fecha límite*

Estimado(a) representante, le recordamos que aún está a tiempo de responder la encuesta sobre su continuidad en el Colegio Andrés Bello para el período *2026-2027*.

Busque en su correo el mensaje de *votacion@ueipab.edu.ve* y haga clic en el enlace de respuesta.

¿No lo recibió o necesita ayuda? Escríbame aquí y le reenvío su enlace personal 🙏

_Fecha límite: lunes 08/06/2026 · 12:30 pm_
```

---

**Coverage:** Production: 84 families emailed; mobile coverage TBD (query `res.partner.mobile` on tag 26).

**Run command (once script is built):**
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
| `partner.communication.ack` model | ✅ Production |
| Public ACK routes `/partner-ack/` | ✅ Production (nginx updated) |
| HR tracking view | ✅ Production |
| Send script (email, 3-button + budget section) | ✅ Production — 84 families sent 2026-05-19 |
| CC `votacion@` on outbound + ACK | ✅ Verified |
| School logo in email header | ✅ Production |
| notice_key-aware confirmation pages (v6.5) | ✅ Production 2026-05-19 |
| Capability 2 — WA messages | ✅ Messages approved — script pending (run Jun 3–5) |
| Capability 3 — Glenda stats | ⏳ Pending |
