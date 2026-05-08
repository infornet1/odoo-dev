# Cashea Campaign — Instituto Privado Andrés Bello

**Created:** 2026-05-08  
**Status:** Sent 2026-05-08 — 279 emails delivered (v2, no price)

## Overview

Promotional campaign to inform UEIPAB parents/representatives that the school is now a **Cashea merchant**, allowing them to pay the monthly tuition (mensualidad) in interest-free biweekly installments.

Cashea is Venezuela's leading BNPL (Buy Now, Pay Later) platform — 5M+ users, 5,000+ allied merchants, 0% interest model.

---

## Campaign Assets

### Email Templates (Odoo)

| Template | ID | Description |
|---|---|---|
| Cashea — Campaña de Lanzamiento | 81 | **v1** — includes specific price $197,38 |
| Cashea — Campaña v2 (sin precio) | 82 | **v2** — generic, price-free, reusable each month |

Both templates feature:
- School logo (served from `https://dev.ueipab.edu.ve/flyers/school_logo.png`)
- Cashea brand colors: yellow `#FFD600`, black `#111111`, white
- Cashea Club de Niveles 6-tier breakdown table
- Google Play + App Store + cashea.app download buttons
- `email_from`: `"Instituto Privado Andrés Bello" <pagos@ueipab.edu.ve>`

**Note:** v2 template has no personalized greeting — opens directly with intro paragraph.

### Instagram Images

| File | Dimensions | Version |
|---|---|---|
| `cashea_instagram_post_v1.png` | 1080×1080 | v1 — shows $197,38 |
| `cashea_instagram_story_v1.png` | 1080×1920 | v1 — shows $197,38 |
| `cashea_instagram_post_v2.png` | 1080×1080 | v2 — shows % levels, no price |
| `cashea_instagram_story_v2.png` | 1080×1920 | v2 — shows % levels, no price |

All images saved to `/home/ftpuser/odoo-dev/`.  
Generated with Pillow (PIL) using DejaVu fonts.

---

## Cashea Club de Niveles

| Level | Emoji | Requirement | Initial % | Day-14 |
|---|---|---|---|---|
| Semilla | 🌱 | New user | 60% | rest on day 14 |
| Raíz | 🌿 | 5 payments or $120 | 50% | 50% on day 14 |
| Hoja | 🍃 | 10 payments or $400 | 40% | more installments |
| Tronco | 🌳 | 20 payments or $800 | 25% | more installments |
| Árbol | 🌲 | 40 payments or $2,000 | 20% | more installments |
| Araguaney | 🌻 | 80 payments or $4,000 | 0%* | maximum flex |

*0% initial for select partners (Nivel Araguaney).  
All levels: **0% interest, 0 surcharges**.

---

## Scripts

| Script | Purpose |
|---|---|
| `scripts/create_cashea_campaign_template.py` | Creates/updates Odoo email template id=81 (v1, with price) |
| `scripts/create_cashea_campaign_template_v1.py` | Backup of v1 template script |
| `scripts/create_cashea_campaign_template_v2.py` | Creates/updates Odoo email template id=82 (v2, no price) |
| `scripts/create_cashea_instagram.py` | Generates v1 Instagram Post + Story (with $197,38) |
| `scripts/create_cashea_instagram_v2.py` | Generates v2 Instagram Post + Story (no price, % levels) |
| `scripts/send_cashea_campaign.py` | Mass send via Odoo partner list (customer_rank > 0) |
| `scripts/send_cashea_campaign_from_sheet.py` | Mass send via Google Sheet Customers tab (Active + Pipeline, col J emails) |

---

## Send Campaign

All scripts run via Odoo shell (XML-RPC is non-functional in this installation).

### Option A — From Google Sheet (recommended, used for 2026-05-08 send)

Source: Spreadsheet `1Oi3Zw1OLFPVuHMe9rJ7cXKSD7_itHRF0bL4oBkKBPzA`, tab `Customers`.  
Filter: column C = `ACTIVE` or `PIPELINE`. Emails: column J (semicolon-separated, all sent).

```bash
# Step 1 — Build clean recipient list (validates emails, deduplicates)
python3 /opt/odoo-dev/scripts/send_cashea_campaign_from_sheet.py --dry-run

# Step 2 — Real send
python3 /opt/odoo-dev/scripts/send_cashea_campaign_from_sheet.py --send
```

**2026-05-08 send results:**
- 184 customers (178 ACTIVE + 6 PIPELINE) → 282 raw emails
- Skipped 1 invalid (`sheni0702gmail.com` — missing `@`)
- Skipped 2 exact duplicates (`jbisleibymata@gmail.com`, `joachim@brusseel.be`)
- **279 emails sent — 0 errors** · template id=82 · from `pagos@ueipab.edu.ve`

### Option B — From Odoo Partner List

```bash
# DRY RUN
docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http \
  < /opt/odoo-dev/scripts/send_cashea_campaign.py

# Real send (v2 template)
CASHEA_TEMPLATE_ID=82 DRY_RUN=false \
  docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http \
  < /opt/odoo-dev/scripts/send_cashea_campaign.py
```

Targets Odoo partners with `active=True`, `email` set, `customer_rank > 0`, excluding `@ueipab.edu.ve`.

### Environment Variables (Option B)

| Variable | Default | Description |
|---|---|---|
| `DRY_RUN` | `true` | Set to `false` for real send |
| `CASHEA_TEMPLATE_ID` | `81` | Template ID to use |
| `CASHEA_LIMIT` | `0` (all) | Cap recipients for partial test |
| `CASHEA_DELAY` | `0.5` | Seconds between sends |

---

## Regenerate Instagram Images

```bash
# v1 (with price)
python3 /opt/odoo-dev/scripts/create_cashea_instagram.py

# v2 (no price — reusable)
python3 /opt/odoo-dev/scripts/create_cashea_instagram_v2.py
```

Requires: `Pillow`, DejaVu fonts at `/usr/share/fonts/truetype/dejavu/`,  
school logo at `/home/ftpuser/odoo-dev/Instituto*Bello*.png`.

---

## Production Migration

1. Copy scripts to production server (or run against `DB_UEIPAB` directly)
2. Run `create_cashea_campaign_template_v2.py` on production Odoo shell
3. Verify template renders correctly with a test send
4. Update `CASHEA_TEMPLATE_ID` in `send_cashea_campaign.py` to the production template ID
5. Run with `DRY_RUN=false` targeting production database

**Note:** School logo must be accessible at `https://dev.ueipab.edu.ve/flyers/school_logo.png` (already deployed).

---

## Technical Notes

- **Gmail/data URI**: Gmail blocks `data:` URI images — logo served via HTTPS nginx static.
- **Logo path**: `/var/www/dev/flyers/school_logo.png` → `https://dev.ueipab.edu.ve/flyers/`
- **Odoo 17 template rendering**: use `_generate_template([id], render_fields=[...])` — `generate_email()` was removed in Odoo 17.
- **email_to field**: must be set on template as `{{ object.email }}` — otherwise `mail.mail` has no recipient.
