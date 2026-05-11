# Representante Continuity Campaign — Período 2026-2027

**Status:** ⏳ PENDING — letter content not yet ready
**Created:** 2026-05-11
**Module:** `ueipab_attendance_report` v17.0.1.6.0 (same as PDVSA campaign)
**Script:** `scripts/send_representante_communication.py`
**Related:** [PDVSA campaign](PDVSA_CONTINUITY_CAMPAIGN.md) — already deployed

---

## Overview

Companion survey to the PDVSA campaign, targeting parents tagged **"Representante"**
(non-PDVSA families). Shares all infrastructure — only the letter content differs.

**Blocked on:** letter from La Administración. Once received, fill 5 constants in the
script and run.

---

## Campaign Parameters

| Parameter | Value |
|---|---|
| `notice_key` | `representante_continuacion_2026_2027` |
| Partner tag | `Representante` (id=**25** — confirmed same in testing and production) |
| Decision deadline | **Monday, June 8, 2026 — 12:30 p.m.** *(confirm when letter arrives)* |
| Default if no response | Auto-accepted (new conditions apply for 2026-2027) |
| Sender (SMTP From) | `Colegio Andrés Bello <soporte@ueipab.edu.ve>` |
| Reply-to | `votacion@ueipab.edu.ve` |
| CC (outbound + ACK) | `votacion@ueipab.edu.ve` |

---

## Partner Coverage

| Metric | Testing | Production |
|---|---|---|
| Representante with email | 224 | **225** |
| Tag id | 25 | **25** |

---

## What needs to be done when letter is ready

Open `scripts/send_representante_communication.py` and fill these 5 constants at the top:

```python
# URL to the full letter document
LETTER_URL = 'https://docs.google.com/document/d/...'

# Three bullet-point summaries (HTML allowed)
BULLET_1 = 'El <strong>descuento X</strong> finaliza el...'
BULLET_2 = 'La matrícula 2026-2027 tendrá un ajuste de...'
BULLET_3 = 'Casos especiales con méritos serán evaluados...'

# Headline shown in the email hero (under the logo)
EMAIL_HEADLINE = '¿Continuará en el Colegio para 2026-2027?'
```

Also verify `DEADLINE_DISPLAY` and `DEADLINE_SHORT` match the letter if different from June 8.

---

## Shared infrastructure (no changes needed)

| Component | Status |
|---|---|
| `partner.communication.ack` model | ✅ Already in production (from PDVSA deploy) |
| `/partner-ack/<token>/si\|no` routes | ✅ Already live (dev + prod nginx) |
| ACK confirmation email → partner + CC votacion@ | ✅ Controller handles all `notice_key`s |
| HR tracking view (Comunicados a Representantes) | ✅ Filters by `notice_key` — shows both campaigns |

---

## Send workflow (once letter is ready)

```bash
# 1. Dry run — confirm 225 partners found, no records created
docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http \
  < /opt/odoo-dev/scripts/send_representante_communication.py

# 2. Test send — single partner (replace N with partner id)
{ echo "import os; os.environ['LIVE']='true'; os.environ['PARTNER_ID']='N'"; \
  cat /opt/odoo-dev/scripts/send_representante_communication.py; } \
  | docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http

# 3. Production full blast (pipe via SSH to prod container)
{ echo "import os; os.environ['LIVE']='true'"; \
  cat /opt/odoo-dev/scripts/send_representante_communication.py; } \
  | ssh root@10.124.0.3 \
  "docker exec -i 0ef7d03db702_ueipab17 /usr/bin/odoo shell -d DB_UEIPAB --no-http"
```

Script is **idempotent** — re-running skips partners who already have a record for this `notice_key`.

---

## Status

| Component | Status |
|---|---|
| Script skeleton | ✅ Created 2026-05-11 |
| Guard (blocks send until TODOs filled) | ✅ Tested — shows clear error message |
| Letter content (5 TODO constants) | ⏳ Waiting for La Administración |
| Production deploy of module | ⏳ Friday 2026-05-15 (covered by PDVSA deploy) |
| Test send | ⏳ After letter arrives |
| Full blast | ⏳ After test passes |
