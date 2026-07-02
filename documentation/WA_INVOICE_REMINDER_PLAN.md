# WA Invoice Reminder — Representante / Representante PDVSA

**Created:** 2026-05-14  
**Status:** LIVE in production. Latest run **2026-06-23: 61/61 sent, 0 errors** (all generic Standard message).  
**Script:** `scripts/wa_invoice_reminder.py`  
**Cron:** `/etc/cron.d/wa_invoice_reminder` (daily blast, currently disabled) + `/etc/cron.d/wa_invoice_reminder_poller` (UI-trigger poller, every 5 min)

---

## 2026-07-01 Update — wizard redesigned to two-step config → preview (payroll v1.75.0)

- **"Filters not working" root cause = client-side onchange staleness, NOT the backend.** The wizard populated its confirmation list via an `@api.onchange`, which left the list **stale/empty when the user switched filter mode**. Staff read the empty/mismatched list as "the filters don't work". Server-side `_compute_lines()` was always correct. **Removed the onchange population.**
- **New stateful flow:** opens in **`state='config'`** (filters only, no list) → footer **«Ver lista →»** (`action_load_list`, a **warm** in-form reload = Owl-crash-safe) → **`state='preview'`** (readonly filter recap + confirmation list + Email/WA send + **«← Cambiar filtros»**). Warm reloads avoid the Owl `this.fiber.bdom is null` crash that COLD-mounting a form with x2many rows re-triggers (same trap that reverted the v1.74.1 populate-on-open attempt).
- **WA-outage banner:** param-driven `wa_invoice_reminder.wa_notice` (set both envs) shows an alert noting Glenda's primary WA **+58 414-8321989 is down** (Massiva ticket; sends via backup). Clear the param to hide. Prod backups `*.bak-20260701`.
- **Deployed both + prod.** See CHANGELOG 2026-07-01 (pm-3).

---

## 2026-06-23 Update — wizard-driven WA + message-by-segment (payroll v1.74.5)

- **WA button sends the wizard's EXACT selected list** (ad-hoc), not the standalone tag-based blast. Wizard → `wa_invoice_reminder.adhoc_payload` param (partner + Odoo `mobile` `+58…` + tag) → poller runs `wa_invoice_reminder.py --live --adhoc` → sends that list verbatim. Force-dry while `ai_agent.dry_run=True` (global WA pause).
- **Message is chosen by the SELECTED SEGMENT, not the customer's tag:**
  - **"Todos con saldo pendiente" (`all`)** → **Standard** generic balance message for **everyone, incl. PDVSA** (no 35% pitch). Wording (TEMPLATE_REP): *"Colegio Andrés Bello le informa que su saldo pendiente es de {deuda}. Le invitamos a protegerse de la volatilidad cambiaria pagando a la tasa BCV oficial, la cual puede consultar en nuestro monitor https://bit.ly/tasabcv …"*
  - **"PDVSA Only" / "Representante + PDVSA"** → PDVSA rows get the **35%-advance** template (TEMPLATE_PDVSA, with invoice month). REP rows + `all` use the Standard template.
- **Live result 2026-06-23:** 61/61 sent, 0 errors, 0 skipped — all `[REP]` Standard (0 PDVSA pitch). One emergency-stop earlier the same day (2 PDVSA customers got the wrong 35% body before the `all`-generic fix; their dedup was cleared and they were re-sent correctly).
- WA **un-paused** (`ai_agent.dry_run=False`) and delivering via the **backup +584248944898** (dedicated primary +584148321989 still broken — Massiva ticket).

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

## Pending Enhancements (2026-06-01)

Analysis date: 2026-06-01. Ground truth: **SMS1** (Representante) and **SMS2** (PDVSA) tabs of Customers sheet `1Oi3Zw1OLFPVuHMe9rJ7cXKSD7_itHRF0bL4oBkKBPzA`. Current wizard produces 133 sends (72 REP + 61 PDVSA) vs sheet expectation ~147 (76 REP + 71 PDVSA).

### What already works correctly (no change needed)

- **June 10 future-due invoices** — wizard does NOT filter by due date; all unpaid posted invoices are included regardless of whether they mature June 10 or later. 101+ partners with `due:2026-06-10` already appear in the send list. ✅
- **May 31 carry-over balances** — partners with unpaid May 10, April 10, and older invoices are already summed into the balance. KARINA DE DELGADO ($789.52 = May+June), REINSON GUTIERREZ ($864.50 = Apr+May+Jun), etc. all appear. ✅
- **PDVSA "didn't fully pay May + new June invoice"** — partners with both months stacked (ALEXIS QUILARQUE $201.60, ALIRIO ROSAS $325.68, JEAN MUNOZ $394.76) are already included. ✅

### Fix 1 — `PDVSA_ADVANCE_PAID` exclusion — ✅ RESOLVED 2026-06-23 (v1.74.0, both envs)

**Resolution:** rather than deleting the rule, it is now **bypassable** via a new
`override_pdvsa_rule` boolean toggle on the wizard. When enabled, the wizard
skips BOTH PDVSA exclusions (`PDVSA_ADVANCE_PAID` 30% advance **and**
`PDVSA_FISCAL_EXCLUDED` fiscal_check) so every PDVSA partner with a balance is
reminded; left off, the conservative behaviour is unchanged. Also shipped the
same release: new `all` segment (surfaces untagged AR customers, partly
obsoleting Fix 2 for *sending*). Verified: PDVSA sendable 4 → 33 with override
ON. Original analysis kept below.

> ⚠️ **Note (v1.74.1):** a "populate-on-open" attempt (server action that
> pre-filled the list before the form mounted) was **reverted** — mounting the
> wizard with rows already present re-triggers the Owl `this.fiber.bdom is null`
> crash. The list still fills post-mount via onchange. The empty-list /
> force-refresh annoyance therefore remains open and needs a crash-safe fix.
>
> ✅ **RESOLVED 2026-07-01 (v1.75.0):** redesigned to a two-step **config → preview**
> flow — the onchange population was removed and the list now fills via a **warm**
> in-form reload («Ver lista →»), which is crash-safe (COLD-mounting rows was the
> trap). See the 2026-07-01 update section at the top of this doc.

**Impact: +7 PDVSA partners currently blocked.**

The 35% advance payment rule was designed to skip partners "on track." But SMS2 sheet includes all of them — they still owe the remaining ~65% on the June invoice (due June 10) and should receive a reminder.

All 7 affected partners have ONLY a June invoice, partially paid (35–87% advance):

| Partner | Balance owed | Advance paid |
|---------|-------------|-------------|
| VIRGILIO CASTRO | $256.60 | 35.0% |
| EDUARDO RANGEL | $239.78 | 39.3% |
| ALBERTO GONZALEZ | $119.89 | 39.3% |
| ILDEMARO ARRIOJA | $119.89 | 39.3% |
| RAQUEL LOPEZ | $119.89 | 39.3% |
| RAMLY REQUENA | $119.51 | 39.5% |
| MAGDA HERRERA | $25.31 | 87.2% |

Also caught in wizard via REP tag: EDIFEL MARIN $26.64, ENDIS PELEYON $26.64 (SMS2 does not list them — verify with business before including).

**Code fix:** In `wizard/invoice_reminder_wizard.py` `_compute_lines()`, remove the `PDVSA_ADVANCE_PAID` elif block entirely. The `BELOW_THRESHOLD` check ($1.00 minimum) already handles partners with zero net balance.

### Fix 2 — Assign missing category tags (data fix in Odoo, no code change)

**Impact: +4 REP + 3 PDVSA partners not found by wizard query.**

These partners exist in Odoo but have no `category_id` assigned, so `('category_id','in',[25,26])` never returns them:

| Tag to assign | Partner name | Odoo id | Sheet balance |
|--------------|-------------|---------|--------------|
| REP (25) | MIGUEL GONZALEZ | 2698 | $394.76 |
| REP (25) | VICTOR VILLAMIZAR | 2906 | $197.38 |
| REP (25) | WILMEILYS CONTRERAS | 2919 | $396.19 |
| REP (25) | MARIA MARTIN | 3658 or 2666 | $197.16 |
| PDVSA (26) | HECTOR CALLES | 2467 | $197.38 |
| PDVSA (26) | KELLY MONTAGUTH | 2590 | $197.38 |
| PDVSA (26) | ROSA MARCANO | 2822 | $383.82 |

⚠️ MARIA MARTIN has **two duplicate partner records** (ids 3658 and 2666, both no-tag). Resolve duplicate before assigning tag — merge or deactivate the blank one.

> **Data-hygiene note (2026-06-25):** Not every untagged partner with a balance
> should be *tagged into* the reminder list — some balances are stale and the
> right fix is to clear them. The new `all` ("Todos con saldo pendiente")
> segment surfaces these. Example: **YOJANA LEDEZMA** (id=2941, mobile
> `+58 414 0836783`, tag *After School* only) carried a single $30.07 residual
> from `INV/2024/00008` dated **2024-06-04** — a stale 2024 charge, no Glenda or
> reminder history. Resolved by **canceling the invoice + archiving the partner**
> (not by tagging her REP/PDVSA), which removes her from the `all` segment
> entirely. Vet untagged `all`-segment hits for stale/illegitimate balances
> before any send.

**Fix procedure (Odoo UI or XML-RPC):**
```python
# Assign REP tag (25) to REP partners
env['res.partner'].browse([2698,2906,2919,3658]).write({'category_id':[(4,25)]})
# Assign PDVSA tag (26)
env['res.partner'].browse([2467,2590,2822]).write({'category_id':[(4,26)]})
# Resolve MARIA MARTIN duplicate separately
```

### Deployment

Both fixes scheduled for **end-of-day maintenance window**. No module upgrade required for Fix 2 (data only). Fix 1 requires `ueipab_payroll_enhancements` update + upgrade on both envs.

---

## Related

- [QUERY_REPRESENTANTE_PDVSA_TAG_CHECK.md](QUERY_REPRESENTANTE_PDVSA_TAG_CHECK.md) — fiscal_check segmentation data (2026-04-15)
- [AI_AGENT_MODULE.md](AI_AGENT_MODULE.md) — MassivaMóvil API config and send patterns
- [AKDEMIA_DATA_PIPELINE.md](AKDEMIA_DATA_PIPELINE.md) — gspread pattern reused here
- `scripts/pagos_receipt_processor.py` — reference script architecture
- `scripts/ai_agent_escalation_bridge.py` — reference MassivaMóvil send function

---

## Technical Reference (CLAUDE.md extract)

- **Wizard:** `ueipab_payroll_enhancements` — Accounting → Customers → Recordatorio de Saldo (Email)
- **WA cron:** `/etc/cron.d/wa_invoice_reminder` — weekdays 07:00 VET (`0 11 * * 1-5`), runs `scripts/wa_invoice_reminder.py --live`
- **Segments:** TAG_REP=25 (Representante), TAG_PDVSA=26 (PDVSA), TAG_VIP=30 (excluded by default, override via `include_vip` toggle)
- **Exclusions (both channels):** VIP, active employees (VAT match), PDVSA fiscal_check on latest invoice, PDVSA ≥30% advance paid, balance < $1.00
- **Email channel:** `res.partner.email`; sends `mail.mail` From=`finanzas@` Reply-To/CC=`pagos@`; per-partner HTML with invoice table newest→oldest, payment options, BCV rate link
- **WA channel (v1.74.4, 2026-06-23 — wizard-driven):** "Enviar WA" now sends the wizard's **exact selected list**, including the `all` segment + PDVSA override. `action_send_wa` runs `_sync_eligibility()`, builds an ad-hoc payload (partner + Odoo `mobile` normalised to `+58…` + `is_pdvsa` + latest-invoice month), and writes it to `ir.config_parameter` `wa_invoice_reminder.adhoc_payload` (payload first, `trigger_at` last). The dev-server poller runs `wa_invoice_reminder.py --live --adhoc`, which consume-once reads the payload and sends that list verbatim (REP/PDVSA template by tag, same-day dedup, 120–140s anti-spam, chatter note). **Safety:** the script force-dry-runs while `ai_agent.dry_run=True` (global WA pause), so the armed button can't fire real sends until WA is restored. The legacy tag-based daily blast (Sheets col L phones) still runs via `wa_invoice_reminder.py --live` **without** `--adhoc` (daily cron, currently disabled). Button hides after queueing (`wa_queued_at` shown).
- **State file:** `scripts/wa_invoice_reminder_state.json` — per-partner `last_sent` date; idempotent same-day re-runs
- **First live send:** 2026-05-15 — 26 partners (REP + PDVSA); follow-up emails sent same day
