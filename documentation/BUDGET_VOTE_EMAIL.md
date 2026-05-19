# Budget Vote Email — Consulta Presupuestaria 2026-2027

**Status:** Production (pending live send) | **Script:** `scripts/send_budget_vote_email.py` | **Updated:** 2026-05-19

---

## Overview

Electronic vote email for the 2026-2027 school budget proposal. Parents select between **Opción A** ($218.88/mo, +10.89%) and **Opción B** ($236.58/mo, +19.86%). Vote tracking uses the existing `partner.communication.ack` infrastructure.

---

## Script

**File:** `scripts/send_budget_vote_email.py`  
Runs via **Odoo shell** piped into the production container. Must be uploaded to `/tmp/` on the production server first.

### Upload + Usage

```bash
# Upload script to production server
scp /opt/odoo-dev/scripts/send_budget_vote_email.py root@10.124.0.3:/tmp/

# Dry run — list all 226 recipients, no DB changes
docker exec -i ueipab17 /usr/bin/odoo shell -d DB_UEIPAB --no-http \
  < /tmp/send_budget_vote_email.py

# Test — CEO only (gustavo.perdomo@ueipab.edu.ve)
docker exec -e TEST=true -e LIVE=true -i ueipab17 /usr/bin/odoo shell -d DB_UEIPAB --no-http \
  < /tmp/send_budget_vote_email.py

# Live — send to all 226 active Representante families
docker exec -e LIVE=true -i ueipab17 /usr/bin/odoo shell -d DB_UEIPAB --no-http \
  < /tmp/send_budget_vote_email.py
```

### Environment Variables

| Variable | Default | Effect |
|----------|---------|--------|
| `LIVE` | unset | Must be `true` to enable real sends |
| `TEST` | unset | If `true`, restricts to CEO partner (id=7) only |
| `SEND_DELAY` | `0.2` | Seconds between sends |

---

## Recipients

**Domain:** `res.partner` where:
- `active = True`
- `email` is set (not empty)
- `category_id` includes tag **25** (Representante)
- `category_id` excludes tag **29** (Inactivo)

**Count as of 2026-05-19:** 226 partners.

---

## Vote Mechanism

Uses `partner.communication.ack` model (same as PDVSA continuity campaign):

| Action | URL | Odoo state |
|--------|-----|-----------|
| Vote Opción A | `/partner-ack/<token>/si` | `continuing` |
| Vote Opción B | `/partner-ack/<token>/no` | `leaving` |

- `notice_key = 'budget_consulta_2026_2027'`
- `notice_label = 'Consulta Presupuestaria 2026-2027'`
- From/CC: `votacion@ueipab.edu.ve`
- Reply-To: `votacion@ueipab.edu.ve`

### Notice-Key-Aware Confirmation Pages

`ueipab_attendance_report/controllers/partner_ack.py` (v6.5) detects `notice_key == 'budget_consulta_2026_2027'` and shows budget-specific confirmation pages:

| Decision | Confirmation shown |
|----------|-------------------|
| `continuing` (Opc. A) | "Votó por Opción A — $218,88/mes ✅" (navy) |
| `leaving` (Opc. B) | "Votó por Opción B — $236,58/mes ✅" (purple) |
| Already voted | Shows which option was selected + date |

CC confirmation email to `votacion@` also uses budget labels.

---

## Email Sections

| # | Section | Notes |
|---|---------|-------|
| 1 | Header | Logo, school name, "🗳️ CONSULTA PRESUPUESTARIA 2026-2027" chip |
| 2 | Greeting | Legal basis: Resoluciones 0009 y 024-2020 del MPPE |
| 3 | Context box | Inflation 611.86% / Bs. 487.12 / Growth 8.5% |
| 4 | Ballot cards | Option A (navy) + Option B (purple), each with: mensualidad, % change, pronto pago, annual cost, vote button |
| 5 | Brother discounts | 5% / 8% / 11% table |
| 6 | Annual extras | $101.58/alumno breakdown (seguro $30.58 + inglés $25 + olimpiadas $10 + enciclopedia $36) |
| 7 | 🛡️ Seguro Escolar | Seguros Caracas callout — claim WA + email, policy PDF link |
| 8 | Enrollment offer | $187.51 inscripción + $197.38 sep (until Jul 31) |
| 9 | Timeline | 4-step process with status chips (✅ done / 🗳️ active / 📊 pending) |
| 10 | ⚖️ Mora policy | 4-step process summary + link to `/mora-policy/` |
| 11 | Final vote buttons | Duplicate of ballot card buttons — prominent CTA |
| 12 | Footer | votacion@ / Glenda WA / Glenda Telegram |

---

## Key Pricing

| Item | Opción A | Opción B |
|------|---------|---------|
| Mensualidad | $218.88 | $236.58 |
| Pronto pago (1–10 c/mes) | $207.93 (save $10.95) | $224.75 (save $11.82) |
| % increase vs prior year | +10.89% | +19.86% |
| Annual per student | $2,845.45 | $3,075.55 |
| Annual extras (same) | $101.58 | $101.58 |

**Inscripción anticipada** (until 31 Jul): $187.51 + sep $197.38 (requires 2025-2026 fully paid).

---

## Key Contacts & Links

| Resource | Detail |
|----------|--------|
| Voting email | votacion@ueipab.edu.ve |
| Insurance claims WA | [0414-903.3738](https://wa.me/584149033738) |
| Insurance claims email | amis@grupov.com.ve |
| Insurance advisor | Johanna Hernández |
| Insurance policy PDF | [Google Drive](https://drive.google.com/file/d/1KLJ5i9IgE5f0BhN1sGJvmVUCZMX7-mtU/view?usp=drive_link) |
| Mora policy webpage | https://odoo.ueipab.edu.ve/mora-policy/ |
| Google Slides presentation | `16EmMb-8mMtnsvdLLnc4Cx8srhzDrzjrsOvNIcXvTkEA` |

---

## Vote Results

Results to be published **26 May 2026**. Query:

```sql
SELECT state, COUNT(*) FROM partner_communication_ack
WHERE notice_key = 'budget_consulta_2026_2027'
GROUP BY state;
```

---

## Resend / Reset

Script skips partners already in `continuing` or `leaving` state.

To reset a single partner for testing:
```sql
UPDATE partner_communication_ack
SET state='pending', ack_date=NULL, ack_ip=NULL
WHERE notice_key='budget_consulta_2026_2027' AND partner_id=<id>;
```
