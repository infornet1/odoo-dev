# WA Invoice Reminder — Representante / Representante PDVSA

**Created:** 2026-05-14  
**Status:** Script built + dry run verified — First live send planned 2026-05-15  
**Script (planned):** `scripts/wa_invoice_reminder.py`  
**Cron (planned):** `/etc/cron.d/wa_invoice_reminder` — daily 11:00 UTC (7:00 AM VET)

---

## Overview

Automated daily WhatsApp reminder for customers with outstanding invoice balances,
segmented by partner tag. Reads balances from Odoo via XML-RPC and phone numbers
from the Google Sheets Customers tab (column L). Sends via MassivaMóvil `type=text`.

**Send frequency: once per day per partner** (confirmed business practice).

---

## Target Segments

| Tag | Tag ID | Message Variant | Filter |
|-----|--------|-----------------|--------|
| Representante | 25 | Generic balance reminder | Unpaid `out_invoice`/`out_receipt`, posted |
| Representante PDVSA | 26 | Monthly invoice + 35% advance prompt | Same + `fiscal_check` exclusion (see below) |

---

## Message Templates

### Representante

```
Colegio Andrés Bello informa su saldo de cuotas pendiente por ref {deuda} pagaderos a la tasa BCV oficial https://bit.ly/tasabcv

Este es un gentil recordatorio automático enviado desde nuestro sistema de cobranzas
```

- `{deuda}` = sum of `amount_residual_signed` across all unpaid invoices, formatted as USD (e.g. `$394.76 USD`)

### Representante PDVSA

```
Colegio Andrés Bello informa que su factura del mes de {last_month_es} esta lista, le invitamos a protegerse de volatividad cambiaria en adelantar el 35% de su factura, su saldo de cuotas pendiente por ref {deuda} pagaderos a la tasa BCV oficial https://bit.ly/tasabcv

Este es un gentil recordatorio automático enviado desde nuestro sistema de cobranzas
```

- `{last_month_es}` = name of the previous calendar month in Spanish at the time of send
  (e.g. if cron runs in May 2026 → `"abril"`). Computed dynamically — never hardcoded.
- `{deuda}` = same balance format as above, subject to `fiscal_check` exclusion

---

## Representante PDVSA — fiscal_check Exclusion

`fiscal_check` is a boolean field on `account.move` that marks invoices printed by
exception / company credit base (PDVSA-subsidised invoices). These do not require
customer payment and must not trigger a reminder.

> **⚠️ OPEN QUESTION — Two options, awaiting decision:**

### Option A — Hard exclude (strict)
If a PDVSA partner has **any** outstanding invoice with `fiscal_check=True` →
skip the partner entirely for WA reminders.

- Pro: simpler logic, no ambiguity
- Con: excludes 3 mixed-flag partners (CARLOS NAVARRO, LILIANNA REYES, RUTHBELIS MARIN)
  who also have non-fiscal balances

### Option B — Balance-only filter
For PDVSA partners, sum **only** `fiscal_check=False` invoice balances.
Include partner if filtered balance ≥ threshold.

- Pro: mixed-flag partners still get reminded for their own balance
- Con: slightly more complex; partner may be confused why reminder doesn't match full balance

**Decision: Option A** — confirmed 2026-05-14.

---

## Phase 0 — WA Number Audit + Odoo Sync ✓ COMPLETE (2026-05-14)

### What was done

1. **Audit** (`scripts/compare_wa_numbers.py`) — read-only diff of Odoo `mobile` vs
   Google Sheets col L for all `res.partner` with VAT in the sheet (scope: all tagged
   partners, Representante tag 25 + PDVSA tag 26). Used column A (`Registration`) as join key.

2. **Sync** (`scripts/sync_wa_numbers_from_sheet.py`) — updated Odoo `mobile` field for
   39 partners across 4 fix types:

| Fix type | Count |
|----------|-------|
| SHEET_ONLY — added missing mobile | 19 |
| Normalise format (spaces → digits, same number) | 12 |
| MISMATCH — sheet replaced Odoo value | 7 |
| Email stored in mobile field (JOYCE MOGOLLON) | 1 |
| **Total** | **39** |

### Final audit state (post-sync)

| Status | Count |
|--------|-------|
| MATCH | 171 |
| NOT_IN_SHEET (expected — tagged but not in Customers sheet) | 141 |
| SKIP_NOT_ELIGIBLE (C/Q/R filter) | 10 |
| MISMATCH / SHEET_ONLY / BOTH_EMPTY | **0** |

**Odoo `mobile` is now fully in sync with Google Sheets col L** for all matched partners.
The reminder script can use either source interchangeably.

### Scripts (one-off, kept for future re-audits)

- `scripts/compare_wa_numbers.py` — read-only audit; run anytime to check drift
- `scripts/sync_wa_numbers_from_sheet.py` — apply sheet → Odoo mobile sync (`--live` flag)

---

## Data Pipeline (reminder script)

### Step 1 — Odoo (XML-RPC)

```
res.partner
  category_id in [25, 26]
  → id, name, vat, category_ids

account.move
  partner_id in <partner_ids>
  move_type in ['out_invoice', 'out_receipt']
  state = 'posted'
  payment_state != 'paid'
  → partner_id, amount_residual_signed, fiscal_check
```

- Sum `amount_residual_signed` per partner (signed field — correctly nets credit notes)
- Skip partners with net balance below minimum threshold (default **$1.00 USD**)

### Step 2 — Google Sheets (gspread)

- Spreadsheet: `1Oi3Zw1OLFPVuHMe9rJ7cXKSD7_itHRF0bL4oBkKBPzA`
- Tab: `Customers`
- Column A (`Registration`) = cedula/VAT — join key against `res.partner.vat`
- Column L = WA phone number (authoritative source, already includes `58` country code prefix)

**Sheet-side eligibility filters (all three must pass):**

| Column | Header | Required value | Distribution (verified 2026-05-14) |
|--------|--------|----------------|-------------------------------------|
| C | Status | `ACTIVE` or `PENDING` | ACTIVE=178, PENDING=4, INACTIVE=11, PIPELINE=6 |
| Q | Notify_SMS | `YES` | YES=196, NO=3 |
| R | Notify_Email | `YES` | YES=196, NO=3 |

- Rows that fail any of the three filters → `SKIP_NOT_ELIGIBLE`, not sent
- **179 rows** currently pass all three filters; all 179 have a phone in column L
- Case-insensitive comparison (uppercase normalisation)
- Partners with no phone in column L → logged as `SKIP_NO_PHONE`, not sent (0 currently)

### Step 3 — Message construction

```python
# Representante
msg = TEMPLATE_REP.format(deuda=fmt_usd(balance))

# PDVSA
last_month = compute_last_month_es()   # e.g. "abril"
msg = TEMPLATE_PDVSA.format(last_month_es=last_month, deuda=fmt_usd(balance))
```

`fmt_usd(balance)` formats as `"$394.76 USD"` — confirmed 2026-05-14.

### Step 4 — Send

MassivaMóvil `POST /api/send/whatsapp`:

```
secret    = <from config>
account   = primary_account_id
recipient = phone (column L)
type      = text
message   = <constructed message>
```

Config from `/opt/odoo-dev/config/whatsapp_massiva.json` (same as AI agent).

**Send method: plain text** — Python substitutes the balance value before sending `type=text`. No pre-approved template required. Confirmed 2026-05-14.

---

## Deduplication & Send Frequency

**Confirmed:** once per day per partner (if balance ≥ threshold).

State file: `scripts/wa_invoice_reminder_state.json`

```json
{
  "partners": {
    "1234": {"last_sent": "2026-05-14", "last_balance": 394.76},
    ...
  },
  "last_run": "2026-05-14T11:00:00"
}
```

- Skip partner if `last_sent == today` (idempotent re-runs)
- Re-send next day if balance still exists
- Reset entry when partner balance drops to zero / below threshold

Anti-spam delay: **120 seconds** between sends (MassivaMóvil per-account limit).
With ~50–100 partners after filtering, total run time ≈ 1.5–3.5 hours starting 7:00 AM VET.

---

## Scale Estimate

| Segment | Sheet eligible (C=ACTIVE/PENDING, Q+R=YES) | With Odoo tag | With unpaid balance | After fiscal exclusion |
|---------|-------------------------------------------|---------------|---------------------|------------------------|
| Representante (tag 25) | 179 total across both tags | TBD | TBD | N/A |
| Representante PDVSA (tag 26) | ↑ (subset of above) | ~43 | ~43 | ~10 (fiscal_check=False only) |

> Note: the 179 eligible sheet rows are the **universe**. Odoo tag filter + unpaid balance filter
> will narrow the actual send list further each day.

---

## Dry Run Results (2026-05-14)

```
python3 scripts/wa_invoice_reminder.py   # dry run, production data
```

| Metric | Value |
|--------|-------|
| Partners to send | 40 |
| Total outstanding balance | $11,012.38 USD |
| Month context | abril |
| BELOW_THRESHOLD skipped | 240 |
| PDVSA_FISCAL_EXCLUDED skipped | 35 |
| NO_PHONE_IN_SHEET skipped | 8 |
| Estimated run time | 80–93 min |

**First live send: 2026-05-15** — run manually, verify delivery, then set up cron.

---

## Cron

**Status: pending** — install after first live send confirms delivery on 2026-05-15.

```cron
# WA Invoice Reminder — daily 7:00 AM VET (11:00 UTC)
0 11 * * * root /usr/bin/python3 \
  /opt/odoo-dev/scripts/wa_invoice_reminder.py --live \
  >> /var/log/wa_invoice_reminder.log 2>&1
```

---

## Risk Flags

| Risk | Mitigation |
|------|-----------|
| WA account flagged for spam | Daily send is confirmed practice; monitor MassivaMóvil subscription usage |
| Mixed fiscal_check partners get wrong balance | Use Option A (hard exclude) until clarified |
| Phone in Sheet col L differs from Odoo | Phase 0 audit surfaces mismatches before first run |
| Partner not in Customers sheet | `NOT_IN_SHEET` status logged; skip send |
| Near-zero rounding residuals ($0.01) | $1.00 minimum threshold |
| Script runs on wrong environment | `--env` flag + `TARGET_ENV` guard |
| Month name wrong if cron delayed past midnight | Always compute from `datetime.now()` at run time |
| Double-send on re-run same day | State file `last_sent == today` guard |

---

## Open Questions Checklist

- [x] **Q3** Send cooldown → **daily** (confirmed)
- [x] **Q5** Customers sheet matching → **column A (`Registration`)** = cedula/VAT; column L already has `58` prefix — **Phase 0 sync complete, 39 Odoo mobile fields updated**
- [x] **Q1** PDVSA exclusion → **Option A: hard exclude** any partner with any fiscal_check=True outstanding invoice
- [x] **Q2** Send method → **plain text** (`type=text`), Python substitutes balance before send
- [x] **Q4** Balance format → **`$394.76 USD`**

---

## Implementation Phases

| Phase | Task | Script | Status |
|-------|------|--------|--------|
| 0 | WA number audit + Odoo mobile sync | `scripts/compare_wa_numbers.py` + `sync_wa_numbers_from_sheet.py` | ✓ Done 2026-05-14 — 39 partners fixed, 171 MATCH |
| 1–4 | Script: data pipeline + phone resolution + messages + send + dedup | `scripts/wa_invoice_reminder.py` | ✓ Built + dry run verified 2026-05-14 |
| 5 | Cron setup | `/etc/cron.d/wa_invoice_reminder` | Pending — after first live send confirms OK |
| 6 | First live send | `python3 scripts/wa_invoice_reminder.py --live` | **Planned 2026-05-15** |

---

## Related

- [QUERY_REPRESENTANTE_PDVSA_TAG_CHECK.md](QUERY_REPRESENTANTE_PDVSA_TAG_CHECK.md) — fiscal_check segmentation data (2026-04-15)
- [AI_AGENT_MODULE.md](AI_AGENT_MODULE.md) — MassivaMóvil API config and send patterns
- [AKDEMIA_DATA_PIPELINE.md](AKDEMIA_DATA_PIPELINE.md) — gspread pattern reused here
- `scripts/pagos_receipt_processor.py` — reference script architecture
- `scripts/ai_agent_escalation_bridge.py` — reference MassivaMóvil send function
