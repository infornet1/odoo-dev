# UEIPAB Odoo Development - Changelog

This file contains detailed version history, bug fixes, and deployment notes moved from CLAUDE.md.

---

## 2026-06-28 — FreeScout Turnstile CAPTCHA on main login (deployed)

**Type:** Security hardening / deploy | **Module:** FreeScout `ExtraSecurity` | **Env:** production (`freescout.ueipab.edu.ve`)

Enabled Cloudflare Turnstile CAPTCHA on the FreeScout agent/admin main login form.
Created a Turnstile widget via the Cloudflare API (domain
`freescout.ueipab.edu.ve`, mode `managed`, site key `0x4AAAAAADsURQLrsIeJlDCP`),
stored the encrypted secret in `.env`, set `EXTRASECURITY_RECAPTCHA_MAIN_*`
(enabled/turnstile/checkbox), and rebuilt the config cache. Verified: secret valid
via `siteverify`, config loaded, login page renders the `cf-turnstile` widget.
Backup at `.env.bak-20260628_070546`.

**Security debt:** the Cloudflare Global API Key + account password were shared in
chat — must be rotated; account 2FA was disabled and should be enabled.

See [FREESCOUT_TURNSTILE_LOGIN_CAPTCHA.md](FREESCOUT_TURNSTILE_LOGIN_CAPTCHA.md).

---

## 2026-06-27 — FreeScout Venezuela IP allowlist research

**Type:** Security research / hardening plan | **Module:** FreeScout `ExtraSecurity` | **Env:** production (`freescout.ueipab.edu.ve`)

Researched best practices for restricting FreeScout access to known Venezuela IP
ranges after the Extra Security module was installed. Key findings: the module
**cannot be configured via API**, its IP check **bypasses the REST API**, and it
is **IPv4-only** — so nginx/ipset is the stronger enforcement point. Recommended a
layered approach (module for back-office + nginx geo allowlist fed by ipdeny
`ve-aggregated.zone`, ~247 CIDRs, with cron refresh and admin exception IPs).

No config changed yet — awaiting decision on enforcement layer + exception IPs.

See [FREESCOUT_IP_ALLOWLIST_VENEZUELA.md](FREESCOUT_IP_ALLOWLIST_VENEZUELA.md).

---

## 2026-06-23 — prod payroll caught up to v1.73.0 (stale-registry OwlError fix)

**Type:** Incident / deploy fix | **Module:** `ueipab_payroll_enhancements` | **Env:** production (`DB_UEIPAB`)

### Symptom

Opening a payslip batch (`hr.payslip.run`) in prod threw an Owl lifecycle error:
`"hr.payslip.run"."advance_warning_count" field is undefined.` (client-side, at view `parseFieldNode` / `loadView`).

### Root cause

The 1.73.0 code (which adds the computed `advance_warning_count` field on
`hr.payslip.run` + the period-advance warning view that references it) had been
deployed to the prod **disk** within the prior ~3 days, but the container was
**never restarted or upgraded**. So:

- Prod DB held the **1.73.0 views** (id 2876, 3175) referencing the field, but
- the running workers' **live registry was still 1.72.0** and lacked the field
  (`fields_get` confirmed it absent; live ORM read faulted).
- `ir.module.module`: `installed_version=17.0.1.72.0`, `latest_version=17.0.1.73.0`.

The web client loaded the newer view arch, asked the server for the model's
fields, the field wasn't there → error.

### Fix (authorized 2026-06-23)

```bash
docker exec ueipab17 odoo -u ueipab_payroll_enhancements -d DB_UEIPAB --stop-after-init
docker restart ueipab17
```

Clean load (165 modules, "Modules loaded"). The lone `Unexpected indentation`
log line is the harmless RST warning from the manifest `description`, not a
failure.

### Verified (live, post-restart)

- `fields_get(['advance_warning_count'])` → `{'type': 'integer'}` ✓
- Live read of a batch → `advance_warning_count: 0` (no fault) ✓
- Module `installed_version` = `latest_version` = **17.0.1.73.0** ✓

### Lesson

Prod had silently lagged a version behind testing — a prior deploy bumped the
disk code but skipped the `-u`/restart, leaving DB views ahead of the live
registry. After a payroll-module deploy to prod, always run
`-u ueipab_payroll_enhancements` + restart the container so the registry,
views, and `installed_version` all match the disk manifest.

---

## 2026-06-17 — payslip batch: refuse-instead-of-delete audit trail (v1.72.0)

**Type:** Enhancement | **Module:** `ueipab_payroll_enhancements` → `models/hr_payslip.py`

### Problem

When a user clicked the delete (trash) icon on a payslip row inside a batch's `slip_ids` list, Odoo called `hr.payslip.unlink()` which permanently deleted the record from the database. No audit trail was left — there was no way to know which employee's payslip existed in the batch, who removed it, or when.

Example: JUNIO15 batch, employee Camila, SLIP/842 was deleted from the prod DB with no trace.

### Fix

Added `unlink()` override in `HrPayslip` (ueipab_payroll_enhancements). For any **draft payslip that belongs to a batch**, the override intercepts the delete and instead:

1. Posts a chatter note on the payslip: *"Refused and removed from batch JUNIO15 by [user] on [date]. Record preserved for audit — not deleted."*
2. Logs `_logger.info()` to the server log (batch name, employee, user id, timestamp)
3. Sets `state = 'cancel'` (Rejected) and clears `payslip_run_id` so the row disappears from the batch UI

All other cases (payslips with no batch, already-cancelled payslips) continue with normal deletion via `super().unlink()`.

### Behaviour after fix

- Delete icon on batch slip → row disappears (UX unchanged)
- Payslip survives in DB as "Rejected", findable in Payslips list
- Chatter on the payslip records batch name, user, and timestamp
- `Total Net Payable` on the batch updates automatically: `payslip_run_id = False` removes the record from `slip_ids`, which fires `@api.depends('slip_ids')` → recomputes stored total

### Deployed

Testing + production — 2026-06-17.

---

## 2026-06-09 — partner_ack: voting deadline guard (budget_consulta_2026_2027)

**Type:** Bug fix | **File:** `addons/ueipab_attendance_report/controllers/partner_ack.py`

### Problem

`_record_decision` had no date-based guard. Any of the 64 pending parents who still had their original vote email could click the personalized `/partner-ack/<token>/si` or `/no` link and have their vote recorded — even after the consultation closed on 2026-05-26 and the stated deadline of 2026-06-08 passed.

Discovered when ILDEMARO ARRIOJA submitted a vote on 2026-06-09 (one day after deadline) via his email link, triggering a CC confirmation to `votacion@ueipab.edu.ve`.

### Fix

Added `_VOTE_DEADLINES` dict on the controller class. Both `_record_decision` and `partner_ack_landing` now check the deadline for the ACK's `notice_key` before accepting input. If today > deadline → show `_page_voting_closed` page (yellow warning, redirects to `pagos@`). No vote is written, no confirmation email sent.

```python
_VOTE_DEADLINES = {
    'budget_consulta_2026_2027': datetime.date(2026, 6, 8),
}
```

Deployed to testing + production on 2026-06-09.

---

## 2026-06-08 — pagos_faq_email_checker: draft-only mode + post-vote knowledge update

**Type:** Script behavior + knowledge | **File:** `scripts/pagos_faq_email_checker.py`

### No more customer-facing replies

`pagos_faq_email_checker.py` now operates in **draft-only mode**: Glenda never posts a customer-visible reply.

| Claude decision | Before | After |
|---|---|---|
| `action=responder` | `POST /threads` type=`message` (customer sees it) | `POST /threads` type=`note` — "💬 Borrador de respuesta sugerida por Glenda FAQ" |
| `action=escalar` | `POST /threads` type=`note` (unchanged) | same — no change |

Both paths now write internal notes only. The pagos@ team reviews the draft and sends manually if appropriate.

### SYSTEM_PROMPT knowledge update

The hardcoded knowledge block was frozen at pre-vote state (voting framing, stale "etapa de votación", Option B still present). Updated to reflect the closed consultation:

- **Removed:** voting timeline (18/05, 21-23/05, 26/05), "ETAPA DE CONSULTA ACTIVA" section, Opción B, "NO inventes resultados" instruction, "sin enlace de votación" guidance
- **Added:** "APROBADA" heading — Opción A confirmed 108/114 votes (60.7%) on 2026-05-26
- **Split tariffs:** "TARIFAS CONFIRMADAS 2026-2027" ($218,88/$207,93) vs "TARIFA ACTUAL 2025-2026" ($197,38/$162,39)
- **Response instruction:** always lead with early-bird promotion ($187,51 inscripción + $197,38 sept, hasta 31 jul 2026) before quoting confirmed mensualidad

---

## 2026-06-05 — EMILIO ISEA liquidation closed (SLIP/840 + SLIP/841)

**Payslip 891 → SLIP/840** (`LIQUID_VE_V2`): NET = **$514.51** (includes LIQUID_ANTIGUEDAD_V2 2.5-day fix). Confirmed `done`.

**Payslip 892 → SLIP/841** (`VE_PAYROLL_V2`, `is_partial_quincena=True`): Jun 1–4 (4 days), ratio=0.27, NET = **$44.52**. Confirmed `done`.

**Email:** Comprobante de Pago sent to `emilio.isea@ueipab.edu.ve` (mail id=7477, `exchange_rate_used=563.2892`). Mail queue cron triggered manually as automated fire was ~4 min away.

**Contract id=94 (prod):** `ueipab_vacation_prepaid_amount` cleared to `$0.00` — no longer needed; payslip 891 is confirmed and paid.

**Employee status:** no longer with UEIPAB as of 2026-06-04 (contract `close`).

**LOTTT research note (utilidades vs aguinaldos):** `LIQUID_UTILIDADES_V2` uses 15 days/year (LOTTT minimum) but UEIPAB's aguinaldo policy pays 60 days/year (2× monthly salary). Under LOTTT Art. 131, utilidades and aguinaldos are the same concept. This creates a rate inconsistency in liquidation; additionally, the rule uses full `service_months` (10.27) which overlaps with the Dec 2025 aguinaldo already paid for fiscal year 2025 — the proportional amount in liquidation should ideally cover only the current fiscal year (Jan–Jun 2026 ≈ 5.1 months). See PENDING in CLAUDE.md.

---

## 2026-06-05 — LIQUID_ANTIGUEDAD_V2: 2.0 → 2.5 days/month (LOTTT Art. 142 fix)

**Rule:** `LIQUID_ANTIGUEDAD_V2` (prod id=29, testing id=59)

**Fix:** Rate changed from `2.0 days/month` (24 days/year) to `2.5 days/month` (30 days/year) per LOTTT Article 142 System B: `30 days × years of service × last integral salary`.

**Impact on payslip 891 (EMILIO ISEA liquidation):**
- `LIQUID_ANTIGUEDAD_V2`: $132.95 → **$166.19** (+$33.24)
- `LIQUID_NET_V2`: $481.27 → **$514.51**

**LOTTT basis:** System B retroactive formula = 30 days/year ÷ 12 = 2.5 days/month. Previous 2.0 days/month rate was a 20% underpayment on seniority benefit.

**`previous_liquidation_date` behaviour confirmed correct:** True termination on 2025-07-31 (full settlement including antigüedad). Current slip covers new employment period Aug 2025–Jun 2026 = 10.27 net months only. Formula's `total_months − paid_months` approach is legally correct for this scenario.

**Both envs updated.** Payslip 891 recomputed.

---

## 2026-06-05 — EMILIO ISEA contract salary_v2 accidentally zeroed (incident)

**Incident:** `ueipab_salary_v2` on production contract id=94 (EMILIO ISEA) was set to `$0` at `04:01:21` when editing the contract via UI (field cleared on save).

**Evidence:** Prior confirmed payslip id=866 (May 16–31) showed `VE_SALARY_V2=$80.38` → implied monthly `salary_v2 = $160.76`. `ueipab_bonus_v2=$135.66` was unaffected.

**Resolution:** Restored manually via UI to `$160.76` at `04:10:05`. Contract id=94 verified.

**Note:** `ueipab_vacation_prepaid_amount=$221.65` was intentionally kept during processing. **Resolved 2026-06-05:** cleared to `$0.00` on contract id=94 (prod) after payslip 891 was confirmed and paid.

---

## 2026-06-05 — Partial Quincena Pro-ration + Single Payslip Email Actions (v71.0)

**Features:**

1. **`is_partial_quincena` flag on `hr.payslip`** — Boolean toggle "Período Parcial (prorratear)" in the payslip form (next to Credit Note). When enabled, all VE_PAYROLL_V2 earnings and deductions are multiplied by `period_days / 15`. Defaults to `False`; must be set manually.

2. **`VE_PERIOD_RATIO_V2` helper salary rule** — sequence 0, `condition_select=none`; returns `period_days / 15.0` when `is_partial_quincena=True`, else `1.0`. Linked to VE_PAYROLL_V2 structure. 9 existing rules updated: `VE_SALARY_V2`, `VE_EXTRABONUS_V2`, `VE_BONUS_V2`, `VE_CESTA_TICKET_V2`, `VE_SSO_DED_V2`, `VE_PARO_DED_V2`, `VE_FAOV_DED_V2`, `VE_ARI_DED_V2`, `VE_OTHER_DED_V2`.

3. **Single-payslip email actions** — two new buttons in the payslip form header:
   - **📧 Payslip Email** — sends "Payslip Email - Employee Delivery" template to the employee; visible on all non-cancelled payslips; emails queued via mail cron (`force_send=False`)
   - **🔔 Send Ack Reminder** — sends ack reminder template + increments `ack_reminder_count`; visible only on `done` + not acknowledged

**Rules excluded from pro-ration by design:** `BONO_CALIBRACION` (per-session calibration bonus), `VE_LOAN_DED_V2` (fixed installment per quincena).

**Validation (testing):**

| Scenario | `is_partial` | Ratio | NET | Result |
|---|---|---|---|---|
| Jun 1–15 (full quincena) | False | 1.0 | $166.96 | ✅ unchanged |
| Jun 1–4 (4 days, resignation) | True | 0.27 | $44.52 | ✅ prorated |
| Feb 16–28 (13 days, full per HR policy) | False | 1.0 | $166.96 | ✅ no accidental proration |

**Deployed:** both envs. Rule IDs — testing: `VE_PERIOD_RATIO_V2`=72; prod: `VE_PERIOD_RATIO_V2`=43.
**Module:** `ueipab_payroll_enhancements` v17.0.1.71.0.
**Deployment script:** `scripts/deploy_ve_period_ratio_prod.py`

---

## 2026-06-04 — Liquidation V2: LIQUID_SERVICE_MONTHS_V2 net-period fix 🔴 CRITICAL

**Problem:** `LIQUID_SERVICE_MONTHS_V2` always counted from `contract.date_start`, ignoring `ueipab_previous_liquidation_date`. All downstream rules (Vacaciones, Bono Vacacional, Utilidades, Prestaciones, Intereses) computed against the **full tenure** instead of the net period since the last full liquidation. Only `LIQUID_ANTIGUEDAD_V2` previously handled `previous_liquidation_date` correctly.

**Impact (payslip 891 — EMILIO ISEA):**
- Contract start: 2023-10-02 | Previous liquidation: 2025-07-31 | Period end: 2026-06-04
- School obligation: 10.27 net months (2025-08-01 → 2026-06-04) — all benefits through Jul 2025 already paid
- Payslip was computing 32.53 months for every rule → **overstatement of $662.87**

| Rule | Before | After |
|------|--------|-------|
| LIQUID_SERVICE_MONTHS_V2 | 32.53 mo | **10.27 mo** |
| LIQUID_PRESTACIONES_V2 | $1,053.28 | $332.39 |
| LIQUID_INTERESES_V2 | $185.61 | $18.48 |
| LIQUID_VACACIONES_V2 | $242.24 | $76.44 |
| LIQUID_BONO_VACACIONAL_V2 | $242.24 | $76.44 |
| LIQUID_UTILIDADES_V2 | $80.38 | $68.77 |
| LIQUID_VACATION_PREPAID_V2 | −$564.86 | $0.00 |
| LIQUID_ANTIGUEDAD_V2 | $132.95 | $132.95 (unchanged — already correct) |
| **NET** | **$1,365.79** | **$702.92** |

**Fix:** `LIQUID_SERVICE_MONTHS_V2` now uses `ueipab_previous_liquidation_date` as the period start when it is set and `> contract.date_start`. All dependent rules automatically inherit the net period. Contract's `ueipab_vacation_prepaid_amount` cleared to $0 (that value was the previous liquidation's vacation payment; it is not needed as a manual offset once the period boundary is correct).

**Rule updated:** prod id=21, testing id=51. Contract updated: prod id=94 (EMILIO ISEA), testing id=127 (RAMON BELLO).
**Migration script:** `scripts/fix_liquid_service_months_testing.py`

---

## 2026-06-01 — Invoice Reminder Wizard Owl crash fix (v70.5)

**Problem:** Opening *Accounting → Customers → Recordatorio de Saldo* threw an Owl lifecycle error: `TypeError: can't access property "bdom", this.fiber is null`. The wizard opened blank with an error dialog.

**Root cause:** `default_get()` computed and stored `line_ids` (~40 partner records), then the browser triggered `@api.onchange('tag_filter','include_vip')` automatically (because those fields have defaults). The onchange issued `(5,0,0)` to delete all lines and recreated them immediately. Owl's component fiber was still mounting from the first batch when the second batch arrived, leaving `this.fiber = null`.

**Fix:** Removed `line_ids` from `default_get`. The onchange is now the single code path that populates partner lines. Module bumped to v70.5, deployed both envs.

**Pending follow-up:** 2 enhancements identified via SMS1/SMS2 sheet comparison — see [WA_INVOICE_REMINDER_PLAN.md](WA_INVOICE_REMINDER_PLAN.md#pending-enhancements-2026-06-01). Scheduled end-of-day maintenance window.

---

## 2026-05-29 — NTP Fix (both DigitalOcean droplets)

Both servers (`freescout.ueipab.edu.ve` dev + `10.124.0.3` prod) had `NTPSynchronized=no` since initial provisioning. `System clock synchronized: yes` confirmed on both after fix.

**Root cause:** the DO cloud firewall (`ueipab-fw`) had no outbound UDP 123 rule. NTP packets left the VM's eth0 (visible in tcpdump) but were silently dropped by the hypervisor firewall before reaching the internet. Inbound rules were never the blocker. Fix: added `outbound udp 123 → 0.0.0.0/0` via DO API.

Config written to `/etc/systemd/timesyncd.conf.d/ntp.conf` on both servers:
```
[Time]
NTP=time.cloudflare.com
FallbackNTP=ntp.ubuntu.com
```

Prior drift: ~46s on production, ~14s on dev. Kiosk attendance timestamps (server-side UTC) are now accurate.

---

## 2026-05-29 — Attendance Kiosk Investigation (YUDELYS BRITO / 2026-05-27)

Employee raised a formal complaint attributing attendance discrepancies to a "biometric device offline" and a "clock mismatch" on the director's equipment. Technical audit findings:

**Source confirmed: Odoo web kiosk (Chrome), NOT a biometric terminal.**
`hr_attendance.in_mode = 'kiosk'`, `in_browser = 'chrome'`, `in_ip_address = 186.14.93.234` (school's internet IP). Timestamps are 100% server-side — the production Odoo server records `datetime.utcnow()` on HTTP POST receipt.

**Entry discrepancy (claimed 6:55, recorded 7:19):**
A queue pattern is visible in the data: 8 employees checked in within 40 seconds starting at 07:07, preceded by an 8-minute gap after YARITZA BRUCES at 06:59. This suggests a kiosk connectivity issue between ~6:59–7:07, followed by a queue that backed up. Yudelys was position ~12 in that queue; DIXIA BELLORIN checked in 6 seconds after her. Her arrival at 6:55 is plausible but unverifiable from the system.

**Exit discrepancy (claimed 12:03, recorded 11:59):**
She pressed the kiosk checkout button at 11:59:01 VET. Her 12:03 is when she physically left the building — 4 minutes after pressing checkout. The server timestamp is correct.

**Her letter's claim about "biometric device offline"** is technically inaccurate — the kiosk is a browser app, not a biometric reader. The connectivity gap at ~6:59–7:07 is consistent with an internet outage at the school, which would have prevented kiosk access. But the 12-minute queue from 7:07 to her 7:19 check-in is simply a physical line.

**HR guidance:** Worked hours (4.65h) are accurate by system records. Entry correction (6:55) is a judgment call — unverifiable. Exit discrepancy (4 min) is normal checkout-vs-departure gap. Correction form path is appropriate if HR chooses to credit early arrival.

**Key query for future audits:**
```sql
SELECT in_mode, out_mode, in_ip_address, in_browser, create_uid
FROM hr_attendance WHERE employee_id = X AND check_in >= 'Y';
```

---

## 2026-05-29 — Attendance Correction Director CC (v6.22)

`arcides.arzola@ueipab.edu.ve` (school director) now CC'd on all 5 correction email touchpoints: (1) employee submission confirmation, (2) HR notification on submission, (3) "Poner en Revisión" Freescout conversation thread, (4) approved email, (5) rejected email. Guard applied on all employee-facing emails: if ARCIDES is himself the subject employee, his address is dropped from CC to avoid duplicate delivery. `_build_cc()` helper centralises the logic. Also adds the missing `recursoshumanos@` CC to the rejected email (was previously missing). v6.21 → v6.22, deployed both envs 2026-05-29.

---

## 2026-05-29 — Attendance Correction Rejection Wizard (v6.21)

**Problem:** The `rejection_reason` field on `hr.attendance.correction` was only visible after the record was already in `rejected` state. The ❌ Rechazar button called `action_reject()` directly — email fired immediately with no reason because the manager had no UI opportunity to enter one beforehand.

**Fix:** Added `hr.attendance.rejection.wizard` (TransientModel) following the same pattern as the existing `hr.attendance.revision.wizard`. Clicking ❌ Rechazar now opens a small popup with an optional "Motivo de rechazo" text field. On confirm, the reason is written to the record before `send_mail()` fires, so the red "Observación de RRHH" block in the employee email is populated correctly.

- `rejection_reason` on the form view is now `readonly=1` (audit display only — set exclusively via wizard)
- `action_reject(reason=None)` accepts the reason param; still callable programmatically with no args
- Module version: `17.0.1.6.20` → `17.0.1.6.21` | Deployed both envs 2026-05-29

---

## 2026-05-29 — Infrastructure Audit

Full cron/service audit triggered by the BCV rate gap incident. Findings:

**Healthy (all running as expected):** `absence_processor`, `leave_notification`, `attendance_daily_alert`, `dmarc_processor`, `glenda_supervisor`, `pagos_receipt_processor`, `wa_invoice_reminder_poller`, `sync_customers_sheet`, `sync_family_billing`, `sync_google_directory`, `sync_bcv_odoo`, BCV scraper root crontab, Freescout PHP scheduler.

**`hr_leave_attendance_digest`** — No log yet; script works correctly. Feature was installed after the last 12:00 UTC cron slot — first run pending (next weekday 12:00 UTC).

**`voting_digest` cron — EXPIRED.** Day-of-month constraint `19,20,21,22,23,24,25,26` in May means the cron will never fire again. Budget vote closed 2026-05-26. Pending removal of `/etc/cron.d/voting_digest`.

**`wa_primary_relay`** — Running every 5 min in intentional DRY_RUN (no `--live` flag). Disabled 2026-05-23 per CLAUDE.md. 288 no-op executions/day. Will stay disabled until WA primary +584148321989 is restored by Massiva.

---

## 2026-05-29 — BCV Exchange Rate Gap — Root Cause + Backfill + Cron Restore

**Problem:** `res.currency.rate` in production (and testing) had no VEB rates from 2026-05-20 to 2026-05-27. Reports (Relación de Liquidación, etc.) were using the stale May 19 rate (517.9619) instead of the current BCV rate (544.5794).

**Root cause:** Commit `d7c323c` in `odoo_api_bridge` (2026-05-19) removed a root-crontab entry that called `POST /odoo_api_bridge/sync_currency_rate` daily. It was labelled "duplicate" of `/etc/cron.d/sync_bcv_odoo` — but those two jobs update completely different destinations:
- `sync_bcv_odoo` → `ir.config_parameter` `ai_agent.bcv_rate_context` (Glenda AI only)
- `sync_currency_rate` → `res.currency.rate` (reports, payroll, accounting)

**Fix applied 2026-05-29:**
1. **Rate restored:** Called `sync_currency_rate` endpoint manually → 544.5794 written for 2026-05-28 (both envs)
2. **Gap backfilled:** 6 missing weekday rates written directly via XML-RPC to both prod + testing from MySQL source:
   - 2026-05-20: 520.9142 · 2026-05-21: 523.6750 · 2026-05-22: 526.8694
   - 2026-05-25: 530.5047 · 2026-05-26: 535.3853 · 2026-05-27: 540.0431
3. **Cron restored:** `/etc/cron.d/bcv_odoo_currency_sync` installed (weekdays 10:00 UTC = 06:00 VET) with an explicit comment distinguishing it from `sync_bcv_odoo` to prevent future removal.

---

## 2026-05-29 — Finiquito Report Added to Payroll Reports Menu (v70.3)

`Acuerdo Finiquito Laboral` was missing from Payroll → Reports sidebar. The wizard action existed and was bound to the payslip list (⚙️ Action dropdown) but had no `menuitem` in `payroll_reports_menu.xml`. Added at sequence=14 between Comprobante de Pago and Prestaciones Soc. Intereses. Deployed to both environments.

---

## 2026-05-28 — Ajuste Guías de Inglés — Email Blast to Parents

Sent official communication about the English guide cost adjustment for 2026-2027 to all ACTIVE/PIPELINE families.

- **Script:** `scripts/send_english_guide_announcement_email.py`
- **From:** `soporte@ueipab.edu.ve` | **Reply-To:** `pagos@ueipab.edu.ve`
- **Subject:** `📢 Comunicado Importante: Ajuste en Guías de Inglés 2026-2027 — Instituto Andrés Bello`
- **Doc link:** `https://docs.google.com/document/d/1LeeTB-7vk8BWSl9NH_JHZoXSiq3mvtSKpmAgWUh0r-0/edit?usp=sharing`
- **Recipients:** 185 sent (180 sheet + 6 institutional) | 2 skipped (hard-bounce DSNs confirmed in Freescout)
  - Skipped: DAMIRIS HEREDIA `eledeher@gmail.com` (conv #46552, active today) + EMIRO GONZALEZ `olysamg@gmail.com` (conv #44815, failing since 2026-05-17)
- **Pre-blast bounce audit:** Scanned 529 soporte@ conversations via Freescout REST API; found 10 unique hard-bounce addresses; 2 matched ACTIVE/PIPELINE sheet rows → skipped

---

## 2026-05-28 — Guía de Inglés price update: $35 (hasta 31 jul) / $40 (desde 1 ago)

Updated Glenda's annual costs knowledge base to reflect new two-tier pricing for the Guía de Inglés:
- **Hasta el 31 jul 2026:** $35/alumno → total costos anuales **$111,58/alumno**
- **Desde el 1 ago 2026:** $40/alumno → total costos anuales **$116,58/alumno**

**Files changed:**
- `addons/ueipab_ai_agent/skills/general_inquiry.py` — 6 locations (static prompts + dynamic billing enrichment function made date-aware)
- `addons/ueipab_ai_agent/models/mail_bot_glenda.py` — OdooBot/Discuss channel prompt
- `documentation/AI_AGENT_MODULE.md`, `GLENDA_TECHNICAL_PATTERNS.md`, `GLENDA_AI_AGENT_OVERVIEW.md`, `CLAUDE.md` — docs updated

---

## 2026-05-28 — Audit: NIDYA LIRA Correction Request — "Kiosk Down" Claim Denied

**Employee:** NIDYA LIRA | **Correction date claimed:** 2026-05-26 | **Claimed check-in:** 06:40 VET
**Reason given:** "Ingrese al sistema por mi dispositivo ya que el kiosco a esta hora estaba caída la plataforma."

**Audit result: Claim not supported by evidence. Case put under revision.**

Queried `hr.attendance` for May 26, 06:00–09:00 VET. Found **38 successful registrations** with zero kiosk complaints:

| Window | Evidence |
|--------|----------|
| 06:17 | ZARETH FARIAS — kiosk operational |
| 06:30–06:33 | GLADYS BRITO, Maria Figuera, ANDRES MORALES — kiosk operational 1m54s before claimed outage |
| **06:35–06:40** | **Zero registrations from any employee** — claimed outage window |
| 06:53–06:59 | MAIRELSY MOTTA, MARIA NIETO, NORKA LA ROSA + 6 others — kiosk operational 13 min after claimed outage |

No evidence of a kiosk outage. Kiosk was functional at 06:33 and again at 06:53. No other employee reported issues.

**Action taken:** Case set to `under_revision` via Freescout bridge. Note sent to employee:
> "Estimada Nidya, su solicitud de corrección se encuentra en revisión. Tras revisar los registros de video y contrastar con los registros de otros empleados, hemos detectado posibles inconsistencias con la información suministrada. La invitamos cordialmente a conversar con el director sobre este caso."
CC: arcides.arzola@ueipab.edu.ve (School Director)

---

## 2026-05-28 — Attendance Correction "En Revisión" + Freescout Bridge (`ueipab_attendance_report` v6.20)

### New: `under_revision` state on `hr.attendance.correction`

Full audit/ping-pong workflow between RRHH and the employee via Freescout, without leaving Odoo.

**New fields on `hr.attendance.correction`:**
- `revision_note` (Text) — RRHH note stored on the record
- `freescout_conversation_id` (Integer) — links the record to the FS employee-dialogue conversation

**New model: `hr.attendance.revision.wizard` (TransientModel)**
- Popup with expanding optional note textarea + optional binary attachment
- Calls `action_set_under_revision(note, attachment_data, attachment_name)`

**New buttons on the correction form:**
- `🔍 Poner en Revisión` (pending only) → opens wizard → creates FS conversation (mailbox 4, employee as `customer`, unassigned) with yellow-header HTML email including RRHH note block; CC `arcides.arzola@ueipab.edu.ve` automatically
- `🔄 Re-invitar al Empleado` (under_revision only) → adds second FS thread with blue-header email + form link button; resets state to `pending`
- `💬 Ver en Freescout` smart button → `ir.actions.act_url` to FS conversation (appears once linked)
- Approve / Reject both work from `under_revision` state (not only `pending`)

**Controller update (`attendance_fix.py`):**
Employee re-submitting the form via token now updates the existing `pending`/`under_revision` record in place (preserving `freescout_conversation_id`) instead of creating a new one.

**State machine:** `pending → under_revision → pending (re-invite) → approved/rejected`

**Infrastructure fix (dev only):** Added `extra_hosts: freescout.ueipab.edu.ve:172.18.0.1` to `docker-compose.yml` — the dev container's inherited `/etc/hosts` mapped the domain to `127.0.1.1` (container loopback), blocking outbound API calls. Production container was unaffected (resolves via public DNS).

**Deployment:**
- Testing: validated full flow (wizard → FS conv #46397 created, re-invite thread added, controller update-not-create confirmed)
- Production: rsync + `--stop-after-init -u ueipab_attendance_report` + container restart

---

## 2026-05-27 — Env Sync: ueipab_attendance_report 6.18 on Testing

`ueipab_attendance_report` was at 17.0.1.6.17 on testing vs 17.0.1.6.18 on production.
Upgraded via `docker exec odoo-dev-web /usr/bin/odoo -d testing -u ueipab_attendance_report`.
All 6 custom modules now in sync across both environments.

---

## 2026-05-27 — Budget Results Email Blast + Glenda v57.19

### Glenda Knowledge Update (ueipab_ai_agent v57.19)

Voting closed 2026-05-26 (Opción A: 108 votes, 60.7%). Updated `general_inquiry.py`:

- **`_BUDGET_KNOWLEDGE`**: Rewritten — Opción B removed, voting schedule/process removed.
  Replaced with confirmed-result block: Opción A won, prices confirmed from Sep 2026.
- **`_INSTITUTIONAL_KNOWLEDGE`**: Removed all "preliminar / sujeta a confirmación" language.
  Table caption → "confirmadas Opción A". Section label → "TARIFAS CONFIRMADAS 2026-2027".
- **Early-bird promotion preserved**: $187.51 inscripción + $197.38 sept — valid until 2026-07-31.
- **Seguro Escolar unblocked**: already present in `_INSTITUTIONAL_KNOWLEDGE` since v57.17; now officially active.
- **`_FLYERS`**: `inscripcion` and `pronto_pago` descriptions updated to confirmed pricing.
- Deployed to testing + production (both containers restarted).

### Budget Results Email Blast

**Script:** `scripts/send_budget_results_email.py`
**Docs:** [BUDGET_RESULTS_EMAIL_BLAST.md](BUDGET_RESULTS_EMAIL_BLAST.md)

- 201 emails queued to production `mail.mail` and delivered via queue cron.
- FROM `soporte@ueipab.edu.ve` · REPLY-TO `pagos@ueipab.edu.ve`
- Recipients: 195 from Customers sheet col J + 6 hardcoded institutional addresses.
- **⚠️ Post-blast fix:** Status filter (ACTIVE + PIPELINE only) added after initial blast
  inadvertently included all rows. Filter now enforced in `_load_recipients()`.

### Lesson Learned — Blast Email Status Filter

Always filter Customers sheet (col C) by `ACTIVE` + `PIPELINE` before any blast.
Confirm the filter with the user before implementing. See memory:
`feedback_blast_email_status_filter.md`.

---

## 2026-05-25 — Attendance Alert Weekend Skip Fix (scripts/attendance_daily_alert.py)

**Bug:** Morning cron (`30 11 * * 1-5`) fired on Monday 2026-05-25, recapped Sunday 2026-05-24, and emailed ~37 employees about missing attendance on a non-working day.

**Root cause:** `run_morning()` only checked the explicit `holidays` config param before proceeding. No guard against recapping a Saturday or Sunday.

**Fix:** Added `if yesterday.weekday() >= 5: return 0` before the holidays check. One-line change at `scripts/attendance_daily_alert.py:run_morning()`.

**Note:** Holiday handling (Venezuelan public holidays not in the config param) is a follow-up.

---

## 2026-05-21 — Telegram Parent Matching Initiative (ueipab_ai_agent v57.0→v57.1)

**Docs:** [TELEGRAM_PARENT_MATCHING.md](TELEGRAM_PARENT_MATCHING.md)

**Business driver:** WA primary number disabled by Meta after 49 sends during Budget Vote blast. Telegram as spam-free, free, instant alternative for future campaign blasts.

**Phase 1 — `telegram_chat_id` on `res.partner` (v57.0):**
- New `res_partner.py` model extension in `ueipab_ai_agent`
- `telegram_chat_id = fields.Char(readonly=True, index=True)` — auto-populated, never typed
- Visible in contact form under new "Canales Digitales" tab (`//notebook` xpath)
- View xpath bug fixed: `//page[@name='internal']` doesn't exist in Odoo 17 → replaced with `//notebook`

**Phase 2 — Dry retroactive match (0/61):**
- Scanned 162 inbound Telegram messages across 61 conversations
- 0 matches — parents used nicknames only, no phones shared
- Confirms opt-in email blast is the only viable path

**Phase 3 — FAM_ deep-link handler (v57.1):**
- `_handle_telegram_parent_start()` in `ai_agent_conversation.py`
- `/start FAM_{token}` → lookup `partner.communication.ack` by token → write `telegram_chat_id` on `res.partner` → re-link placeholder conversations → send welcome message
- Live test 2026-05-21: Gustavo Perdomo (id=7) clicked → `telegram_chat_id=950519055` captured ✅

**Phase 4a — Email opt-in blast script:**
- `scripts/send_telegram_optin_email.py` — branded HTML, school logo + Glenda banner
- Personalized `FAM_{token}` CTA per parent; 174 ACTIVE parents from Customers sheet
- Preview sent to gustavo.perdomo@ueipab.edu.ve (mail id=5909) — approved

**Vote digest enhancement:**
- `voting_digest.py`: new `_fetch_telegram_status()` + Telegram section in HTML
- Shows linked/unlinked/total Representante partners + linked names list
- Preview sent mail id=5911 (currently 0/241 linked — no parent blast fired yet)

---

## 2026-05-21 — Env Sync Verified

Both testing and production confirmed in sync across all 7 custom modules:
`ueipab_attendance_report` 1.6.15, `ueipab_payroll_enhancements` 1.70.2, `ueipab_ai_agent` 1.56.0, `ueipab_hr_employee` 1.3.0, `ueipab_hr_contract` 2.0.0, `ueipab_bounce_log` 1.4.0, `ueipab_hrms_dashboard_ack` 1.0.0.

---

## 2026-05-21 — Resume Conversation Button (ueipab_ai_agent v57.2)

**Feature:** `action_resume_conversation()` + "▶️ Retomar Conversación" button on `ai.agent.conversation` form.

**Problem solved:** Conv 258 (Luis Albert, Telegram) — rapid messages ("Hola", "1", "Mi estado de Cuenta" < 2s apart) triggered bot-speed auto-silence. Glenda logged all 9 subsequent inbound messages but suppressed replies. Previously required manual `write({'silent': False})` + shell re-trigger.

**Implementation:**
- `action_resume_conversation()`: sets `silent=False`, posts audit note, finds last inbound message, calls `action_process_reply()` to re-fire Claude immediately
- Button visible only when `state=active AND silent=True` — no false positives
- Confirm dialog before firing
- `silent` boolean toggle field added to Seguimiento group in form (previously only in tree view)

**Also added:** `silent` field visible in conversation form Seguimiento group.

---

## 2026-05-21 — Telegram Invitation Email Blast (165 parents) + First FAM_ Link

**Blast fired:** `send_telegram_optin_email.py --live` → 165 ACTIVE parents, personalized FAM_ deep-link per parent. Cron trigger timed out (504) but all 165 queued and delivered via mail queue cron.

**Exclusions (9 total):**
- 7 Akdemia 5to. Año only: ALEXIS QUILARQUE, AMIRA KHATIB, ANGELICA GOMES, CHENIANA NOGALES, JEAN CARLOS SEQUEA, MARIA NIETO, SHARIFA AL RIFAI RIFAI
- 2 PDVSA No continuará: ANDRES HERNANDEZ, MARIA APONTE

**Bug fixed post-blast:** `email_cc/reply_to: votacion@ueipab.edu.ve` incorrectly added (copy-paste from vote script). Fixed to `reply_to: soporte@ueipab.edu.ve`, no CC. Caused 165 CC copies to votacion@ inbox on this first run.

**First FAM_ opt-in confirmed:** RAIZA RENDON (id=2791) clicked her invitation link at 19:32 VET → `telegram_chat_id=1441621803` written to `res.partner`. She had already voted Opc A via email_link — no double vote.

**Conv 258 — Luis Albert (unidentified Telegram lead):** Glenda sent welcome menu but silenced subsequent messages (stub partner, no email/mobile). Resolved manually → next `/start` creates fresh conversation. Glenda handles unidentified contacts as potential leads (asks name/cédula naturally via `partner_found_in_odoo=False` path).

**Telegram opt-in digest:** `telegram_optin_digest.py --force` shows real-time FAM_ link stats. Employee blast pending — separate template needed.

---

## 2026-05-21 — Vote Reminder Email + Bounce Cleanup Round 2

**Vote reminder:** 89 pending parents received a vote reminder email (subject: `[Recordatorio] Consulta Presupuestaria 2026-2027 - Tu voto esta pendiente`). Same original vote template with orange banner "RECORDATORIO — cierra el viernes 23 de mayo". Same ACK tokens — no reset, links vote directly. Queued via `mail.mail state=outgoing` + cron id=3 triggered via docker exec (web timeout workaround). All 89 confirmed sent (outgoing=0 after trigger).

**Vote status at send time:** A:84 / B:4 / Pending:89 / Total:178 / Participation: 49.4%

**Bounce cleanup Round 2:** 5 new DSN convs (45710, 45713, 45714, 45715, 45716) from repeated bounce notifications on already-cleaned addresses (annibelmartinez32@, dcontrerasperez82@, domin.anuel0608@, tampa.navarro@). No Odoo/Sheet action needed — all 4 addresses already removed in Round 1. Closed via Freescout API only.

---

## 2026-05-21 — Voting Digest: PDVSA "No continuarán" Detail Breakdown

**Script:** `scripts/voting_digest.py`

Enhanced the PDVSA Continuity Campaign section of the 15-min vote digest email to show a full breakdown of families who selected "No continuarán" (state=`leaving`).

**Changes:**
- `_fetch_pdvsa()`: added `partner_email` to fetched fields; added `leaving_detail` list (full records for `state='leaving'`) to returned dict
- `_build_html()`: added orange alert block below the 3-box PDVSA count row when `leaving_detail` is non-empty — shows a table with representante name (clickable link to Odoo ACK form) and email(s); hidden when no families have left
- Current "No continuarán": **MARIA APONTE** (apontemarivic + apontemarivict) and **ANDRES HERNANDEZ** (miregamboab + andresmhernandez)

No cron, schema, or dependency changes.

---

## 2026-05-21 — Bounce Email Cleanup — Budget Vote 2026-2027 Campaign

**Procedure doc:** [BOUNCE_EMAIL_CLEANUP_PROCEDURE.md](BOUNCE_EMAIL_CLEANUP_PROCEDURE.md)

Post-campaign bounce cleanup triggered by 24 DSN conversations (9 Failure + 15 Delay) landing in Freescout `soporte@` inbox (mailbox_id=3).

**5 unique confirmed bounced emails identified and removed:**

| Customer | Bounced Email | Action |
|---|---|---|
| ANNIBEL MARTINEZ | annibelmartinez32@gmail.com | Cleared from Odoo + Sheet row 20 |
| DANIEL DOMINGUEZ | domin.anuel0608@gmail.com | Stripped from Odoo + Sheet row 46 (2 good emails kept) |
| DIANA CONTRERAS | dcontrerasperez82@gmail.com | Cleared from Odoo + Sheet row 54 |
| WILLIANS VELASQUEZ | williamjose.velasquezgonzalez@gmail.com | Cleared from Odoo + Sheet row 169 |
| DANNEYSE LA CRUZ | lacruzde@pdvsa.com | Stripped from Odoo only (not in Customers sheet) |

**Actions taken:**
1. Google Sheet Customers tab col J — bounced emails removed, cells flagged 🔴 red
2. Google Sheet BounceEmail tab — created from scratch; headers + 5 data rows (Date / Customer Name / Bounced Email / Source / Status in separate columns)
3. Odoo PROD `res.partner` — 5 partners cleaned (testing was clean, no action needed)
4. Freescout — 24 DSN conversations closed via `PUT /api/conversations/{id}` with `status=closed, byUser=1`

**Key triage decision:** `tampa.navarro@gmail.com` — Delay-only (no Failure DSN ever), previously resolved twice (`[RESUELTO-AI]`). Not removed from Odoo/Sheet — 3 active delay convs closed only.

**SSH router convs 45508–45512** — NOT touched (MikroTik system alerts, unrelated to bounce emails).

---

## 2026-05-21 — partner.communication.ack Form & List UX (`ueipab_attendance_report` v1.6.11→v1.6.13)

**Context:** Budget Vote 2026-2027 campaign monitoring surfaced 10 UX issues in the ACK form/list view used for both the budget vote and PDVSA continuity campaigns.

**v1.6.11 — 8 pure-XML fixes:**
- Fix #1: `leaving` row decoration changed from `decoration-info` (blue) to `decoration-danger` (red) — later revised to `decoration-info` in v1.6.13
- Fix #2: Added `confirm` dialog to "Reiniciar a Pendiente" button — prevents accidental vote resets
- Fix #3: Added colored outcome banners at top of form sheet (green=A, blue=B, yellow=pending)
- Fix #4: `token` field restricted to `base.group_system` — prevents HR users from copying tokens to vote on behalf of families
- Fix #5: Removed duplicate `partner_phone` from Sistema group (was also in Representante group)
- Fix #6: Replaced `statusbar` widget with `badge` — A/B are parallel choices, not sequential steps
- Fix #7: Moved `ack_ip` from Votación group to Sistema group — no meaning to HR users
- Fix #8: `vote_notes` readonly once state is `continuing` or `leaving` — audit integrity

**v1.6.12 — State label rename:**
- `('continuing', 'Continuará')` → `('continuing', 'Opción A')` — model-level, applies everywhere (badges, reports, exports)
- `('leaving', 'No continuará')` → `('leaving', 'Opción B')` — "No continuará" was PDVSA-specific; both campaigns use A/B terminology

**v1.6.13 — Color correction:**
- Opción B (`leaving`) changed from `decoration-danger` (red) to `decoration-info` (blue) in tree rows, state badge, and form header
- Outcome banner for Opción B changed from `alert-danger` to `alert-info`
- Rationale: both A and B are valid confirmed decisions; only `pending` (yellow) signals action needed

**v1.6.14 — Fixes 9–10 (Python):**
- `response_time` computed `Char` field: `@api.depends('sent_date','ack_date','state')` — formats delta as *"Respondió Xh Ymin después del envío"* (days/hours/minutes). Only visible in form when voted. Hidden via `invisible="not response_time"`.
- `action_open_partner()` method returns `act_window` to `res.partner` form with `res_id=partner_id.id`.
- `button_box` `invisible` moved from the box to the individual tablet button — partner stat button always visible.

**⚠️ Structural note:** `partner.communication.ack` is misplaced in `ueipab_attendance_report`. Pending refactor → `ueipab_ai_agent` or new `ueipab_campaigns`. See [ACK_FORM_UX_IMPROVEMENTS.md](ACK_FORM_UX_IMPROVEMENTS.md) for full file list.

**v1.6.15 — Owl rendering bug fix:**
- `oe_stat_button` with inner `<div class="o_stat_info">` causes `UncaughtPromiseError` in Odoo 17 Owl — arbitrary inner HTML not supported in stat buttons. Fixed by replacing with flat `string=` attribute on both buttons. Also removed `&#10;` newline entity from button string (not safe in Odoo view XML attributes).

---

## 2026-05-20 — DMARC p=reject → p=quarantine (Akdemia DKIM fix pending)

- **Problem:** Akdemia sends notification emails FROM `@ueipab.edu.ve` via SendGrid IP `50.31.44.87` (`em.akdemia.com`). DMARC for `ueipab.edu.ve` was `p=reject pct=100`. Google Workspace rejected all 4 recipients with `550 5.7.26 Unauthenticated email`. Root cause: (1) SPF alignment fails — Return-Path `@em.akdemia.com` ≠ org domain `ueipab.edu.ve`; (2) no DKIM signing for `ueipab.edu.ve` from Akdemia/SendGrid. Adding Akdemia's IP to SPF alone cannot fix DMARC alignment.
- **Fix (2 steps):** First changed to `p=quarantine`, then changed to `p=none` (monitor-only). Akdemia emails now deliver to inbox. DMARC reports still sent to `finanzas@`. TTL=3600s — propagation within 1h.
- **Permanent fix required:** Set up DKIM domain authentication in Akdemia/SendGrid dashboard for `ueipab.edu.ve` → receive 3 CNAME records → add to DigitalOcean → verify → revert DMARC to `p=reject`.
- **Note:** SPF upgrade to `-all` must NOT proceed until DKIM is confirmed working.

## 2026-05-20 — Attendance check_out Auto-fill via Router 2 WiFi Log

**Script:** `scripts/attendance_daily_alert.py` — evening mode enhanced (no version bump, host script)

- **Phase 1 (earlier today):** Evening cron replaced "missing check_out" email alert with silent auto-fill. Instead of sending an email to the employee, writes `check_out = 14:00 VET (18:00 UTC)` directly on the `hr.attendance` record via Odoo XML-RPC. No email sent.
- **Phase 2 (this session):** Auto-fill now uses the employee's **actual WiFi departure time** from Router 2 (HapAC3) hotspot log when available:
  - One SSH call (sshpass → ZeroTier `172.28.10.10`) queries all hotspot `logged out` events during school hours (06:00–18:00 VET) in a single router command
  - Python filters results per employee using `payroll_db.wifi_hotspot_users` username mapping (same table as `sync_mikrotik_attendance.py`)
  - WiFi logout time used if found and before 20:00 VET; otherwise 14:00 VET fallback
  - Router in-memory log has 32,800 entries (~1 month of history); query takes ~30s (linear scan — acceptable for nightly background cron)
- **Norka La Rosa (May 19):** WiFi showed device left at 13:12 VET (2 min after kiosk check-in at 13:10 VET). Auto-fill will write 13:12 instead of 14:00 for employees with WiFi mappings.
- **SolarWinds Observability API** researched: `GET /v1/logs?filter=USERNAME` with Bearer token works but only has data from today onwards (remote logging recently activated).

## 2026-05-20 — Glenda Prior Conversation History (v56.0)

**Feature #73** — `ueipab_ai_agent` 17.0.1.56.0

- **Problem:** When a contact sent a follow-up message after a resolved conversation (even 2 min later), Glenda started fresh with the welcome menu, saying "No veo una consulta anterior." Root cause: the state machine correctly creates a new conversation on each inbound message after `resolved`, but the new conv had zero context.
- **Fix:** New static method `_get_prior_conversation_summary(conversation)` in `GeneralInquirySkill` (skills/general_inquiry.py).
  - Called from `get_context()` → `prior_history` key → injected in `get_system_prompt()` after `contact_ctx`.
  - Queries last 1–2 resolved conversations in the last 7 days for the same contact.
  - Match priority: `telegram_chat_id` → identified `partner_id` → `phone`.
  - Returns a compact `HISTORIAL PREVIO` block: "hace X min/h/días" + up to 4 message snippets (150 chars each per message).
  - Directive to Claude: if the message continues a prior topic, answer directly — no welcome menu, no re-greeting.
  - Returns `''` when no history found (no prompt bloat, zero cost impact).
- **Example:** Gaby (conv #121) asked "Eso es con pronto pago?" 2 min after conv #120 (inscription quote). Previously Glenda re-greeted. Now Glenda will see the $187.51 context and answer directly.
- **Deployed:** both testing + production, both on 17.0.1.56.0.

## 2026-05-20 — Freescout Orphaned Conversation Cleanup

- **Issue diagnosed:** 64 conversations across all mailboxes had `state=3` (soft-deleted) but `status=1` (active), causing them to appear in active counts as ghost entries.
- **Root cause:** scripts that soft-delete conversations (BCV checker, bounce processor, etc.) set `state=3` but leave `status=active` instead of closing.
- **Breakdown:** pagos@=11, soporte@=17, recursoshumanos@=4, finanzas@=13, compras@=0, afterschool@=2, votacion@=17.
- **Fix:** closed all 64 via `PUT /api/conversations/{id}` with `{"status":"closed","byUser":1}` — 0 failures.
- **Note:** BCV rate emails will recur (BCV script sends to both finanzas@ + pagos@, 3×/day). Long-term fix: remove pagos@ from BCV recipients or add close-on-delete logic to the checkers.

---

## 2026-05-19 — Budget Vote Email + AI Agent Enhancements

### ueipab_ai_agent v17.0.1.53.0 — Optional partner + Placeholder badge

**Feature #73:** `start_conversation_wizard.py` — `partner_id` is now optional.

- `_get_or_create_placeholder_partner(phone)`: matches existing contacts across 3 phone formats (`+58 414 XXXXXXX`, `0414XXXXXXX`, E.164); creates `Consulta WhatsApp {phone}` partner if no match
- `partner_id` removed from `required=True` in wizard; model stays required (placeholder always resolved before conversation create)
- New stored computed `is_placeholder` Char field on `ai.agent.conversation`: returns `'Desconocido'` when partner name starts with `Consulta WhatsApp`, otherwise `''`
- `widget="badge" decoration-warning` column in conversation tree view — amber **"Desconocido"** badge visible at a glance
- Wizard form: partner field shows `"Opcional — déjalo en blanco si el número no está en Odoo"` placeholder text

**Use case:** staff can start a conversation with an unknown lead using only a phone number. Inbound unknown contacts already triggered this path automatically; the wizard now matches.

---

### ueipab_ai_agent v17.0.1.53.1 — Bot detection false-positive fix

**Bug:** first inbound message of any `general_inquiry` conversation was silenced by the 2-second bot detection guard.

**Root cause:** `_get_or_create_general_inquiry_conversation()` sets `last_message_date=now()` and `last_sender='customer'` at creation. `action_process_reply()` runs for the first message moments later in the same cron window — gap < 2s → bot detection fired.

**Fix:** added `self.turn_count > 1` guard to the speed check. Bot detection now only fires when there is already more than one inbound message, making it impossible to trigger on a brand-new conversation.

```python
# Before
if (prev_last_msg and prev_sender_was_customer
        and (now_dt - prev_last_msg).total_seconds() < 2):

# After
if (prev_last_msg and prev_sender_was_customer
        and self.turn_count > 1                          # ← new guard
        and (now_dt - prev_last_msg).total_seconds() < 2):
```

**Immediate fix:** conversation #88 (Jessica Bolívar, "cómo pagar con Cashea") — silenced since 2026-05-18 — unsilenced via Odoo shell, reply triggered manually.

---

### ueipab_attendance_report v17.0.1.6.5 — notice_key-aware partner_ack confirmation pages

`controllers/partner_ack.py` now adapts confirmation text based on `ack.notice_key`:

- New `_vote_context(ack, decision)` helper returns label, bg, border, color, emoji per campaign
- `budget_consulta_2026_2027`: "Votó por Opción A — $218,88/mes ✅" / "Votó por Opción B — $236,58/mes ✅"
- All other keys: existing continuity labels unchanged
- New `_page_budget_vote_success(ack, decision)` page: large price display, annual cost, results date
- `_send_ack_confirmation` CC email uses campaign-specific labels
- `_page_already_done` uses `_vote_context` for correct historical display

---

### Budget Vote Email — `scripts/send_budget_vote_email.py` (new)

New script to send the 2026-2027 budget consultation vote email to 226 Representante families.

**Key design:**
- Two side-by-side ballot cards: Option A (navy) and Option B (purple)
- Context box: inflation 611.86%, Bs. 487.12, growth 8.5%
- Brother discounts table (5%/8%/11%)
- Annual extras breakdown ($101.58/alumno — seguro + inglés + olimpiadas + enciclopedia)
- 🛡️ Seguro Escolar callout: Seguros Caracas, claim contacts, [policy PDF link](https://drive.google.com/file/d/1KLJ5i9IgE5f0BhN1sGJvmVUCZMX7-mtU/view)
- Early enrollment offer ($187.51 until Jul 31)
- Process timeline (4 steps with status chips)
- ⚖️ Mora policy callout: 4-step summary + link to `/mora-policy/`
- Red test banner in `TEST=true` mode
- Skips partners who already voted

**Test email sent:** `gustavo.perdomo@ueipab.edu.ve` — pending CEO approval before live send.

See [BUDGET_VOTE_EMAIL.md](BUDGET_VOTE_EMAIL.md) for full reference.

---

## 2026-05-19 — PDVSA Campaign: Enhanced Email + Budget Proposal Section

**Type:** Email campaign | **Script:** `scripts/send_pdvsa_communication.py` pattern | **Env:** Production (DB_UEIPAB)

### What was sent

Enhanced version of the PDVSA continuity email fired to **84 ACTIVE families** (Industry=Yes, Status=ACTIVE from Customers spreadsheet `1Oi3Zw1OLFPVuHMe9rJ7cXKSD7_itHRF0bL4oBkKBPzA`).

**Enhancements over original May-15 send:**
- New section added after 3-bullet summary: **📊 Nueva Propuesta Económica 2026-2027**
  - Option A ($218.88) / Option B ($236.58) mini-cards
  - Google Slides CTA → `16EmMb-8mMtnsvdLLnc4Cx8srhzDrzjrsOvNIcXvTkEA`
  - WhatsApp + Telegram + pagos@ query channels
- **CC:** `pagos@ueipab.edu.ve` on every outgoing email
- **Reply-To:** `pagos@ueipab.edu.ve` (parent replies land in pagos@ inbox)
- Sí/No buttons use real `partner.communication.ack` tokens (83 with token, 1 mailto fallback — RAFAEL DUERTO, no Odoo partner)

**ACK confirmation flow (unchanged):** when parent clicks Sí/No → confirmation email To: parent, CC: `votacion@ueipab.edu.ve`

### Delivery stats
- 71 sent / 13 still outgoing at time of check → all 84 delivered by Odoo mail queue
- Source: Customers spreadsheet col J (email) filtered by col O=Yes + col C=ACTIVE

---

## 2026-05-19 — Freescout Calibration Loop + pagos_faq Sender Filter

**Type:** Script enhancements | **Files:** `scripts/pagos_faq_email_checker.py`, `scripts/glenda_daily_digest.py`

### pagos_faq_email_checker.py — Automated email filter

Added `SYSTEM_SENDERS` blocklist and `_AUTO_SUBJECT_RE` pattern to stop wasted Claude calls on system noise:
- **Sender blocklist:** `mailer-daemon`, `noreply`, `finanzas@ueipab.edu.ve`, `pagos@` (circular), `soporte@`, `recursoshumanos@`
- **Subject patterns:** BCV rate updates (`tasa bcv`), DSN failures, out-of-office, auto-replies, Glenda-loop escalations, payment marketing
- Filtered convs are added to `processed_ids` so they are not re-checked on the next 10-min run

### glenda_daily_digest.py — Freescout escalation outcomes section

New 6th section added between escalations and suspicious activity:
- **Chips:** escalaciones hoy / FAQ respondidas / FAQ escaladas / abiertas >24h
- **Table:** each Glenda-generated Freescout conv — subject, status badge, time to first human reply, clickable link
- **Stale block:** convs open >24h shown in red; ✓ green if all resolved
- Subject line now includes FAQ count: `· 4FAQ ✓`
- Data source: `pymysql` direct query to local Freescout MySQL (same server as the script)

---

## 2026-05-19 — Freescout Cron Intervals: Near-Real-Time Response

**Type:** Infrastructure / Cron | **Scope:** `/etc/cron.d/` (host crons, not git-tracked)

### Changes

| Cron | Before | After | Reason |
|---|---|---|---|
| `pagos_faq_email_checker` | 30 min, Mon–Fri only | **10 min, Mon–Sun 06:00–21:00 VET** | Parents email evenings/weekends too; 30 min too slow for FAQ auto-reply |
| `ai_agent_email_checker` | 15 min (4×/hour) | **5 min (12×/hour)** | Align with escalation bridge; bounce customers waiting for verification |

**Technical:** `pagos_faq_email_checker` now wrapped with `flock -n /tmp/lock.pagos_faq_checker` (previously had no overlap guard — safe at 30 min, required at 5 min).

**Permanent change** — 10 min is the production baseline; covers all pagos@ FAQ topics year-round.

---

## 2026-05-19 — ueipab_ai_agent v52.0: Glenda Welcome Menu + Budget UX

**Module:** `ueipab_ai_agent` | **Environments:** Both (testing + production)

### Changes

**Feature #72 — Structured welcome menu (`get_greeting()`):**
- 5-option numbered menu sent when a conversation is manually started via Iniciar Conversación wizard
- Options: saldo pendiente / propuesta 2026-2027 / inscripción anticipada / información general / otro asunto
- Telegram footer appended on WhatsApp channel only (skipped on Telegram to avoid circular invite)

**Audience context block (`get_system_prompt()`):**
- `audience_block`: flags non-tech-savvy parent audience (Media General parents); menu routing instructions (option 1→balance, 2→proposal, 3→enrollment, 4→info, 5→other); tone rules (short first paragraph, no jargon, repeat-with-patience, always offer email contact)

**PRIMER CONTACTO — organic inbound menu (`get_system_prompt()`):**
- `menu_block`: instructs Claude to show the full 5-option menu when the first message is a generic greeting (hola, buenas, etc.) and to answer directly when it includes a specific question
- Telegram footer conditional: only included in menu text for WhatsApp channel

**Balance gate — 2025-2026 debt check before 2026-2027 quote:**
- Replaced `COTIZACIÓN MULTI-ALUMNO` `REQUISITO PREVIO` note with a mandatory first-step check
- If pending invoices exist: inform saldo first, calculate total to regularize (saldo + remaining months × $197.38), explain enrollment blocked, offer pagos@ connection
- If saldo=0: confirm al día, proceed with quotation
- If contact unidentified: request cédula first

**Side-by-side A vs B quotation format:**
- Replaced single-option format with two-column OPCION A / OPCION B table
- Mandatory closing note: "Las tarifas definitivas se confirman tras el escrutinio del 26/05/2026"
- Handoff example updated to reference both options

**Emoji rule:**
- Updated from "No uses emojis" → "No uses emojis decorativos, excepto los numeros del menu (1️⃣–5️⃣)"

**Design decision:** No new skill created for budget consultation — it is a topic within `general_inquiry`, not a separate conversation channel.

---

## 2026-05-17 — Nginx: Add `my` to Odoo Route Whitelist (dev.ueipab.edu.ve)

**Type:** Infrastructure fix | **File:** `/etc/nginx/sites-available/dev.ueipab.edu.ve`

### Problem
`https://dev.ueipab.edu.ve/my/ari` (and all other Odoo portal `/my/*` routes) returned HTTP 404. The nginx config for the dev server uses an explicit regex whitelist to route paths to Odoo on port 8019:

```nginx
location ~ ^/(web|website|payslip|mail|report|arc|attendance-ack|...|ai-agent)(/|$) {
    proxy_pass http://127.0.0.1:8019;
```

`my` was not in the list, so the request fell through to the default `location /` block (Flask app on port 5000), which returned 404.

The route itself was correctly registered — `curl localhost:8019/my/ari` returned 303 (login redirect) confirming Odoo handled it fine locally.

### Fix
Added `my` to the regex alternation group:

```nginx
location ~ ^/(web|website|payslip|mail|report|arc|attendance-ack|attendance-fix|attendance-correction|notice-ack|glenda-calibracion|employee-info|partner-ack|ai-agent|my)(/|$) {
```

`nginx -t && nginx -s reload` applied with no errors.

**Impact:** All standard Odoo portal pages (`/my/account`, `/my/invoices`, `/my/ari`, etc.) now route correctly through the dev proxy.

---

## 2026-05-16 — Pagos Processor: Venezuelan Bank Code Detection

**Type:** Enhancement | **Script:** `scripts/pagos_receipt_processor.py`

### Problem
When a payment receipt contained a Venezuelan bank account number (e.g. `"0174 **** **** 74138559"`), the bank was not detected. The `0174` prefix identifies **Banplus**, but the extractor only matched text keywords like `"banplus"`, `"venezuela"`, etc. — not numeric bank codes. The processor fell back to `fallback_veb` (Banco Venezuela journal 162) instead of the correct Banplus journal (164).

**Triggered on:** Maria Nieto's receipt (Freescout conv #44779, 2026-05-16) — payment PBDV/2026/00897 was created on wrong journal; manually corrected to PBPLUS/2026/00021.

### Fix
Added `_BANK_CODE_MAP` dict with 18 Venezuelan bank code prefixes. Three extraction paths updated:

| Path | Change |
|------|--------|
| Strategy A (regex) | After keyword scan fails, searches for `\b0NNN\b` pattern and maps via `_BANK_CODE_MAP` |
| Strategy B (GPT text) | Prompt now lists bank code → name mappings explicitly |
| Strategy C (GPT vision) | Same bank code hints added to image analysis prompt |

**Key codes mapped:**

| Code | Bank | Journal keyword |
|------|------|----------------|
| 0102 | Banco de Venezuela | venezuela |
| 0105 | Mercantil | mercantil |
| 0108 | Provincial/BBVA | provincial |
| 0134 | Banesco | banesco |
| 0166 | Banplus | banplus |
| 0172 | Bancamiga | bancamiga |
| 0174 | Banplus | banplus |
| 0175 | Bicentenario | bicentenario |

### Sync status
Both `testing` and `production` `ai_agent.payment_journal_map` are identical — no config changes needed. Script change takes effect on next cron run (15 min).

---

## 2026-05-15 — Fix BONO_CALIBRACION Salary Rule Crashing Payslip Generation

**Type:** Bug fix | **Status:** Production ✅ Testing ✅

### Symptom
Clicking "Generate Payslips" on any V2 batch (e.g. MAYO15) raised:
> "Invalid Operation — Wrong python condition/code defined for salary rule Bono Calibracion Glenda (BONO_CALIBRACION)"

### Root Cause (two compounding bugs)

**Bug 1 — Skipped-rule NameError in VE_NET_V2:**
`BONO_CALIBRACION` had `condition_select='python'`. When an employee has no `CALIBRACION_GLENDA` input line, the condition evaluates to `False`, the rule is skipped, and its code is never added to `localdict`. `VE_NET_V2`'s formula `result = VE_GROSS_V2 + VE_TOTAL_DED_V2 + BONO_CALIBRACION` then raises `NameError` — re-wrapped as the misleading "Wrong python condition defined" error.

**Bug 2 — Wrong `payslip` object access in production formula:**
The production `amount_python_compute` used `payslip.input_line_ids` directly. In salary rule context, `payslip` is a `Payslips(BrowsableObject)` wrapper — accessing `.input_line_ids` on it returns `0.0` (BrowsableObject fallback). Iterating `for i in 0.0` raises `TypeError` → "Wrong python code defined".

### Fixes Applied (XML-RPC to production, Odoo shell to testing)

| Fix | Field | Change |
|-----|-------|--------|
| 1 | `condition_select` | `'python'` → `'none'` (rule always runs, always seeds localdict) |
| 2 | `amount_python_compute` | Replace with `payslip.dict.input_line_ids` pattern |

**Correct amount formula (both envs):**
```python
slip = payslip.dict
sessions = sum(l.amount for l in slip.input_line_ids if l.code == 'CALIBRACION_GLENDA')
monthly = contract.wage or 0.0
result = sessions * (monthly / 21.75)
```

For employees without calibration inputs `result = 0.0`; report template filters `total_in_ves > 0` so the line is invisible.

### Key Pattern (documented in CLAUDE.md Key Technical Patterns)
- Always use `payslip.dict.input_line_ids` — never `payslip.input_line_ids`
- Any rule referenced by name in a NET/GROSS formula must use `condition_select='none'`; return `0.0` in the amount formula for the "don't apply" case

---

## 2026-05-14 — Mora Policy Page Moved to Production Domain (ueipab_ai_agent v17.0.1.41.4)

**Type:** Infrastructure fix | **Status:** Production ✅

| Item | Details |
|------|---------|
| **Canonical URL** | **https://odoo.ueipab.edu.ve/mora-policy/** |
| **Dev URL** | https://dev.ueipab.edu.ve/mora-policy/ (still works) |
| **nginx** | `/mora-policy/` location added to `/etc/nginx/sites-available/odoo.ueipab.edu.ve` on `10.124.0.3` |
| **Files** | `/var/www/mora/` on production server — 8 JPEGs + `index.html` |
| **Logo** | Uses relative path `/web/image/res.company/1/logo` (served by Odoo, no external dep) |
| **Glenda** | Knowledge updated to reference `odoo.ueipab.edu.ve/mora-policy/` |

---

## 2026-05-14 — Glenda P2A Mora Policy + Webpage + Enrollment URL Split (ueipab_ai_agent v17.0.1.41.3)

**Type:** Knowledge update + new public page | **Status:** Production ✅
**Resolves:** Calibration suggestions #3, #15, #16 (LUISA ELENA ABREU × 3 — P2A)

### Mora Policy Knowledge

Full 4-step process from *Manual de Acuerdos de Convivencia Escolar* added to `_INSTITUTIONAL_KNOWLEDGE`:

| Step | Trigger | Who's involved | Goal |
|------|---------|---------------|------|
| Fechas de pago | — | — | Payment due within first 10 days of month |
| Incumplimiento | 1 month without payment | — | Administrative procedure activated |
| **Primer Llamado** | After 1 month default | Representante + Admin | Convenio de pago: review, set amounts, set dates |
| **Segundo Llamado** | Convenio not met | Dirección + Admin + Legal | Resolve responsibly |
| **Tercer Llamado** | Reincidence | + CDCE Municipal | Due process guaranteed |
| **Notificación** | Persists | Defensoría + CDCE + Consejo Protección | Gestionar cupo en institución pública |

Key: **student always continues attending during entire process**. Institution always protects right to education.
Glenda: empathetic response, mentions Cashea, explains process without alarming, links to policy page.

### Mora Policy Webpage

URL: **https://odoo.ueipab.edu.ve/mora-policy/** (also at https://dev.ueipab.edu.ve/mora-policy/)
- Standalone HTML/CSS — school colors (#1a2c5b/#2471a3/#f0c400), Poppins font
- Sticky nav with school logo, hero, 4 summary cards, 4-step timeline with institutions
- 8 story images (864×1080 JPEG) in responsive grid with lightbox (keyboard nav ← →, Esc)
- CTA: pagos@ueipab.edu.ve
- nginx location `/mora-policy/` → `/var/www/dev/mora/` added to `dev.ueipab.edu.ve` config

### Enrollment URL Split

Two distinct Akdemia links now in Glenda's knowledge:
- **Solicitar Cupo** (new applicants, not yet enrolled): https://edge.akdemia.com/enrollments/b87d60bc6ba93746
- **Inscripción** (current students, re-enrolling): https://edge.akdemia.com/admissions/09f8190d36eef4ea/start
- Glenda identifies which applies before sending the link.

---

## 2026-05-14 — Glenda P2B Enrollment Process → Akdemia Link (ueipab_ai_agent v17.0.1.41.2)

**Type:** Knowledge update | **Status:** Production ✅
**Resolves:** Calibration suggestion #18 (AUDREY GARCIA — P2B)

Enrollment documentation process is fully online via Akdemia — no static document checklist needed.

| Item | Details |
|------|---------|
| **Trigger** | Any question about: enrollment documents, how to inscribe, what is needed, steps to follow |
| **Glenda response** | Provides direct link: https://edge.akdemia.com/admissions/09f8190d36eef4ea/start |
| **Rationale** | Akdemia guides applicants step by step — simpler and always up to date vs a static checklist |
| **Fallback** | soporte@ueipab.edu.ve for additional questions |
| **Deployment** | Pure Python — `docker restart ueipab17`, no DB upgrade |

---

## 2026-05-14 — Glenda Bachillerato Knowledge (ueipab_ai_agent v17.0.1.41.1)

**Type:** Knowledge update | **Status:** Production ✅ | **Source:** MPPE official document BachilleTIC.pdf — *Propuesta Juntos por la educación del futuro*
**Resolves:** Calibration suggestion #21 (AUDREY GARCIA — P2C)

| Item | Details |
|------|---------|
| **Diploma** | Bachiller en Ciencias y Tecnología — official MPPE title, replaces old Ciencias/Humanidades |
| **Duration** | 5 years (1° a 5° año Educación Media General) |
| **Componente General** | 8 areas: Lengua/Lit, Idiomas, Matemáticas, Ed.Física, Biología/Amb/Tec, Física, Química, Geo/Hist/Ciudadanía |
| **Componente Productivo** | 2 areas: Orientación Vocacional (2 h/sem) + Innovación Tecnológica y Productiva (6 h/sem — every year) |
| **Total hours** | 36 h/sem (1°-2°) → 40 h/sem (3°-5°) |
| **Career access** | All university careers + direct workforce entry (no restrictions like old Humanidades) |
| **Virtual track** | Bachillerato Virtual via Dawere (online/flexible) — details at soporte@ |
| **IB clarification** | School does NOT offer International Baccalaureate (IB Geneva). Glenda explains the difference when parents ask. |
| **Deployment** | Pure Python — `docker restart ueipab17`, no DB upgrade |

---

## 2026-05-14 — Glenda P1 Farewell Auto-Resolve + P3 Cashea Proactive (ueipab_ai_agent v17.0.1.41.0)

**Type:** UX fix + knowledge | **Status:** Production ✅
**Resolves:** Calibration suggestions #1, 4, 5, 6, 7, 8, 13, 14 (P1 — 8/8 testers), #2, 9 (P3 — 2 testers)

### P1 — Farewell Auto-Resolve

| Item | Details |
|------|---------|
| **Problem** | 8/8 calibration testers complained Glenda sends multiple closing messages and keeps asking "¿Hay algo más?" after goodbye |
| **`_FAREWELL_PHRASES`** | 30 Venezuelan Spanish farewell expressions (frozenset) in `ai_agent_conversation.py` |
| **`_is_farewell_message()`** | Strips farewell phrases + filler words from message; True only if no meaningful remainder; `?` anywhere always blocks; >80 chars never triggers |
| **Auto-resolve logic** | After sending Claude reply: if `skill.code == 'general_inquiry'` and `_is_farewell_message(customer_msg)` → `action_resolve()`. State becomes `resolved`, not `waiting` |
| **Prompt hardening** | Explicit trigger list + PROHIBIDO block + two ❌/✅ examples added to `REGLAS DE COMUNICACIÓN` |
| **Unit tests** | 16/16 cases passing (correct and incorrect farewells) |

### P3 — Cashea Proactive

| Item | Details |
|------|---------|
| **Problem** | Cashea was known but only mentioned reactively; 2 testers wanted it offered proactively on payment difficulty |
| **Fix** | `POLÍTICA DE MORA` updated: payment difficulty / mora / financing question → proactively mention Cashea + pagos@ confirm link |

---

## 2026-05-14 — Staff Announcement Email: Glenda in OdooBot

**Type:** Communication | **Script:** `scripts/send_glenda_odoobot_announcement.py`

HTML announcement email introducing the OdooBot/Glenda integration to all 52 internal Odoo users.

| Item | Details |
|------|---------|
| **Recipients** | 52 active internal users with valid email (auto-filtered, excludes system accounts) |
| **Subject** | "Glenda ya está en Odoo — tu asistente virtual ahora también responde en el chat interno" |
| **Content** | 3-step usage guide · what Glenda knows table · live chat example bubble · plain-text note |
| **Branding** | Navy blue #1a2c5b / #2471a3 / #f0f4fa — no red |
| **How to send** | Set `DRY_RUN = False` in script, then run via production Odoo shell |
| **Frontend roadmap** | Next: install `im_livechat` → extend bridge to `channel_type='livechat'` → customers on website |

---

## 2026-05-14 — Glenda Promotion-First Priority + Cashea Reminder (ueipab_ai_agent v17.0.1.40.3)

**Type:** Behaviour fix | **Status:** Production ✅

Glenda was answering pricing questions correctly but leading with the September base rate ($218,88) instead of the inscription promotion. Added explicit `PRIORIDAD AL RESPONDER` block to both the WA skill (`general_inquiry.py`) and the OdooBot bridge (`mail_bot_glenda.py`).

| Item | Details |
|------|---------|
| **Promotion first** | Always lead with promo anticipada: inscripción $187,51 + mensualidad sep $197,38 (current rate, not $218,88) + eligibility requirement |
| **Sep rate second** | After promotion: explain $218,88 base with sibling discounts table |
| **Cashea** | Always mention Cashea as payment option (confirm link with pagos@) |
| **Applies to** | Both WA (general_inquiry) and OdooBot Discuss (mail_bot_glenda) |

---

## 2026-05-14 — Glenda OdooBot Bridge — Glenda in Odoo Discuss (ueipab_ai_agent v17.0.1.40.2)

**Type:** New feature | **Status:** Production ✅

Internal staff can now chat with Glenda directly inside Odoo Discuss via the OdooBot private chat. No WhatsApp or external access required.

| Item | Details |
|------|---------|
| **File** | `models/mail_bot_glenda.py` — `AbstractModel` inheriting `mail.bot` |
| **Hook** | Overrides `_get_answer()` — the officially sanctioned extension point (same as `im_livechat_mail_bot` in Odoo core) |
| **Trigger** | `channel_type == 'chat'` only (private OdooBot DM). Group channels / @mentions not intercepted |
| **Knowledge** | Reuses `_INSTITUTIONAL_KNOWLEDGE` from `general_inquiry.py` — same pricing, policies, PDVSA, Cashea, payment methods |
| **History** | Reads last 10 `mail.message` records from the channel; maps author → user/assistant; merges consecutive same-role turns |
| **Guards** | `dry_run=True` → skips (falls back to default OdooBot); `credits_ok=False` → blocked by `claude_service`; any exception → falls back silently |
| **Cost** | Zero MassivaMóvil credits — never touches `whatsapp_service.py`. Only Claude Haiku tokens (~$0.001–0.003/conversation) |
| **DB changes** | None — no new models, no migrations |
| **Deployment** | `-u ueipab_ai_agent` + `docker restart ueipab17`. Verified: `_glenda_system_prompt` and `_glenda_history` present on `mail.bot` in both envs |

---

## 2026-05-14 — Glenda Pricing & Discount Full Revision (ueipab_ai_agent v17.0.1.40.1)

**Type:** Knowledge update | **Status:** Production ✅ | **Source:** Proyecto Educativo 2026-2027 (Google Slides, parent approval vote May 22)

Corrected annual one-time costs, replaced sibling discount tiers, added enrollment eligibility gate and advance-mensualidad option.

| Item | Old | New |
|------|-----|-----|
| **Seguro Escolar** | $15 | **$30,58** |
| **Guía de Inglés** | Enciclopedia de Inglés $30 | **$25** |
| **Olimpiadas** | $10 | $10 (sin cambio) |
| **Enciclopedia** | $36 solo bachillerato | **$36 todos los niveles (Inicial, Primaria, Bachillerato)** |
| **Total costos anuales** | $55 estándar + $36 bach | **$101,58/alumno (todos)** |
| **Forma de pago costos anuales** | No especificada | **Acuerdo especial, mayo–julio 2026** |
| **Descuento hermanos** | 1° tarifa completa · 2° 5% · 3° 6% · 4°+ 7% | **1° 5% · 2° 8% · 3°+ 11%** |
| **Tabla mensualidad sep 2026** | $218,88/$207,94/$205,55/$203,56 | **$207,94/$201,37/$194,80** |
| **Tabla pronto pago sep 2026** | $207,93/$197,54/$195,27/$193,38 | **$197,54/$191,30/$185,06** |
| **Inscripción en cotización** | $264,48 (precio proyectado) | **$187,51 (precio promo confirmado)** |
| **Ejemplo total primer mes (2 alumnos)** | $1.154,70 / PP $1.109,23 | **$987,49 / PP $967,02** |
| **Requisito inscripción anticipada** | No existía | **2025-2026 completamente saldado — sin excepciones** |
| **Mensualidades en avance** | No mencionado | **Puede prepagar tantos meses como desee a $197,38 + descuentos hermanos** |

**Deployment:** SCP → `docker restart ueipab17` · No DB upgrade required (pure Python skill change)

---

## 2026-05-14 — WA Invoice Reminder: Phase 0 Complete + Script Built

**Type:** New Feature | **Status:** Ready — first live send 2026-05-15
**Script:** `scripts/wa_invoice_reminder.py` | **Plan:** [WA_INVOICE_REMINDER_PLAN.md](WA_INVOICE_REMINDER_PLAN.md)

### What was built

Daily WhatsApp balance reminder for customers tagged **Representante** (tag 25) and
**Representante PDVSA** (tag 26) with outstanding invoices. Sends via MassivaMóvil
primary account (+584148321989) as plain text. Customers who reply are picked up
naturally by Glenda's `general_inquiry` skill.

**Segment logic:**
- Representante: generic balance reminder
- PDVSA: monthly invoice notice + 35% advance prompt; partners with ANY `fiscal_check=True`
  outstanding invoice excluded (Option A — hard exclude)
- Sheet eligibility gate: column C ∈ {ACTIVE, PENDING}, Q=YES, R=YES
- Minimum balance: $1.00 USD
- Frequency: daily; idempotent re-runs via state file

**Dry run result (2026-05-14, production data):** 40 partners, $11,012.38 USD total,
~80–93 min run time. 240 BELOW_THRESHOLD, 35 PDVSA_FISCAL_EXCLUDED, 8 NO_PHONE_IN_SHEET.

### Phase 0 — WA Number Audit + Odoo Sync

New scripts `compare_wa_numbers.py` + `sync_wa_numbers_from_sheet.py`:
- Audited all Representante/PDVSA Odoo partners against Google Sheets Customers col L
- Fixed 39 `res.partner.mobile` fields in `DB_UEIPAB`:
  - 19 SHEET_ONLY (added missing mobile)
  - 12 format normalisation (spaces stripped)
  - 7 MISMATCH (sheet replaced Odoo value)
  - 1 email stored in mobile field (JOYCE MOGOLLON — cleared)
- Post-sync: 171 MATCH, 0 MISMATCH/SHEET_ONLY/BOTH_EMPTY

### Pending
- 2026-05-15: first live send (`python3 scripts/wa_invoice_reminder.py --live`)
- After confirmed delivery: install `/etc/cron.d/wa_invoice_reminder` (daily 11:00 UTC)

---

## 2026-05-14 — Testing Environment Double-Processing Bug Fix

**Type:** Infrastructure Bug Fix | **Status:** Production ✅

### Root cause

The testing Odoo was silently racing production on every inbound WhatsApp message. Both environments share the same MassivaMóvil credentials, so every audio Glenda received triggered two Claude calls and two WA sends — one correct (production, with the v17.0.1.40.0 audio fix), one wrong (testing, with old pre-fix code that replied "no puedo procesar audios").

The bug was the `active_db` lockout being misconfigured as `''` (empty string). The code in `_is_active_environment()` treats empty as "not configured → allow processing":

```python
if not active_db:
    return True  # Not configured = allow processing
```

The CLAUDE.md and AI_AGENT_MODULE.md documentation incorrectly stated that `''` locked testing — it did the opposite.

### Fix

- Set `ai_agent.active_db = 'DB_UEIPAB'` in the **testing** Odoo DB (via SQL + `docker restart odoo-dev-web` to flush `@ormcache`)
- Testing crons now see `DB_UEIPAB ≠ testing` → self-skip
- Updated CLAUDE.md and AI_AGENT_MODULE.md to document the correct lockout value and restart requirement

### Detection method

Symptoms appeared as two WA responses per customer message with contradictory content. The wrong messages had `api: true` in MassivaMóvil's `GET /api/get/wa.sent` log but were absent from the production Odoo DB — confirmed by checking the testing `ai_agent_message` table which held all the wrong responses.

---

## 2026-05-13 — Glenda Audio Fix: WA Voice Notes Now Transparently Transcribed (ueipab_ai_agent v17.0.1.40.0)

**Type:** Bug Fix | **Status:** Production ✅ | **Deployed:** 2026-05-13

### Root cause

MassivaMóvil returns WA's own auto-transcription in the `message` field alongside the audio URL (`.m4a`). The prior code condition `if att_type == 'audio' and not message_text:` skipped Whisper **and** left the body without any prefix, so Claude didn't know it was processing a voice note. When the customer asked directly about audio capability, Claude responded "actualmente no puedo procesar audio" — factually wrong.

### Fix — `ai_agent_conversation.py` (line ~322)

When `att_type == 'audio'`:
- **WA already transcribed** (`message_text` present): prefix the body with `[Audio transcrito]: ` so Claude knows the message came from a voice note. WA's transcription is used as-is (often higher quality than Whisper for WhatsApp voice notes).
- **No WA transcription** (pure audio URL): call Whisper as before, prefix result the same way; fall back to `[audio sin transcripción]` only on failure.

### Fix — `general_inquiry.py` MENSAJES DE AUDIO block

Updated system prompt: Glenda now knows she **can** process voice notes (they're transcribed before reaching her). If a customer asks "did you listen to my audio?", she confirms yes. The `[audio sin transcripción]` path is kept for the rare case transcription truly fails.

---

## 2026-05-13 — Glenda Auto Draft Payment + Pagos@ Processor (ueipab_ai_agent v17.0.1.39.0)

**Type:** Feature | **Status:** Production ✅ | **Deployed:** 2026-05-13

### WhatsApp receipt → draft account.payment

When a customer sends a payment screenshot via WhatsApp, Glenda now automatically creates a draft `account.payment` in Odoo and emails pagos@ a direct validation link.

**New methods on `ai_agent_conversation`:**
- `_extract_payment_receipt()` — upgraded to OpenAI **Structured Outputs** (`json_schema`); `monto` guaranteed float; `moneda`/`tipo_pago` enums; no markdown fence parsing needed
- `_check_duplicate_payment()` — blocks if same partner + last-4 ref digits found within 30 days; returns payment name for warning
- `_resolve_journal_for_payment()` — keyword match `banco` → journal_id via `ai_agent.payment_journal_map` (JSON param); 10 banks: venezuela(162/159), mercantil(161/160), plaza(163), banplus/provincial/bbva(164), bancamiga(165), cashea(171), zelle(158), bicentenario(162); fallback BDV VEB
- `_match_invoice_for_payment()` — VES→USD via BCV rate; exact ±2% or partial match (monto < residual); oldest-first
- `_create_draft_payment()` — `account.payment` state=draft; amount in payment currency (VEB or USD); full ref context string; `payment_method_line_id` from journal's first inbound line
- `_notify_pagos_payment_receipt()` — enhanced: Odoo deep link + BCV conversion + invoice match + duplicate/no-match block

**Config params (production):** `ai_agent.payment_journal_map` param id=71 | Currency ids: USD=1, VEB=2

### Freescout pagos@ email processor (`pagos_receipt_processor.py`)

New script monitors unassigned conversations in pagos@ mailbox (Freescout id=2). Same payment pipeline via XML-RPC.

**3-strategy extraction (cheapest first):**
- Regex — bank auto-notification emails (`Monto:`, `Fecha de Operación:`, `Entidad:` patterns) — **$0**
- GPT text — unstructured customer email body, structured outputs — **~$0.0001**
- GPT Vision — receipt image, structured outputs — **~$0.001**

**Freescout API attachment discovery:** Images in `_embedded.attachments[].fileUrl` (field is `fileUrl` not `url`) AND body `<img src>` regex. Both are public tokenized URLs (HTTP 200). `GET /api/conversations/{id}` returns full thread list with `_embedded.threads` and `_embedded.attachments`. Thread GET endpoint (`/conversations/{id}/threads`) returns 405 — use the conversation GET instead.

Posts Freescout internal note with Odoo link, prefixes subject `[GLENDA]`. Skips: internal senders (ueipab.edu.ve), assigned conversations, already-processed subjects. **Status:** Testing — no production cron yet.

---

## 2026-05-13 — Business Case: U.E. Colegio Andrés Bello — Adquisición Institucional

**Type:** Documentation | **Status:** Draft ✅

Initial business plan drafted for investor review — school acquisition opportunity.

**Files:**
- `documentation/CAB_BUSINESS_CASE_ACQUISITION.md` — full business case in Markdown
- `documentation/CAB_Plan_Negocios_Adquisicion_Mayo2026.docx` — formatted Word document
- Google Doc (live): `https://docs.google.com/document/d/16XYKOjwleft_ZyVLKYrgZCJizztf-4pG_v_C-rJVa-4`
- Data source: Google Sheets `1i4WQ9z86uNv4aFo5wE-RdX76g3xaZIjkGxC8R-FA1TY` (Matriz Costos 2026-2027)

**Key figures:**
- 207 alumnos · 43 empleados · Fundado 1978 (48 años)
- Ingresos brutos anuales ≈ USD 510,352 · EBITDA base ≈ USD 111,165
- Rango de inversión sugerido: USD 1,000,000 – 1,800,000
- ROI base: 8.6% – 11.1% · Período de recuperación: 9 – 12 años
- CEO retenido/a post-adquisición: USD 4,500/mes
- Tasa de cambio planificada: Bs. 788 / USD (sep-2026)

---

## 2026-05-13 — Freescout REST API Migration — Email Checkers Phase 3

**Type:** Infrastructure | **Status:** Production ✅

Migrated Freescout write operations in `scripts/ai_agent_email_checker.py` and `scripts/ai_agent_hr_email_checker.py` to the REST API.

**ai_agent_email_checker.py — `postprocess_freescout()`:**
- SQL `UPDATE conversations SET subject, status=3, closed_at, ...` → `PUT /api/conversations/{id}` `{subject, status:"closed", byUser}`
- SQL `INSERT INTO threads` + `UPDATE threads_count` → `POST /api/conversations/{id}/threads`
- SQL `SELECT subject` (idempotency guard) kept — already connected for `find_email_reply()` reads

**ai_agent_hr_email_checker.py — `post_freescout_note()`:**
- SQL `INSERT INTO threads` + `UPDATE conversations SET threads_count` → `POST /api/conversations/{id}/threads`
- SQL admin user lookup kept — used for `user` field in API note payload

Both scripts use the same `fs_api_add_note()` helper pattern. `find_hr_threads_with_attachments()` stays SQL (thread/attachment body search has no API equivalent).

---

## 2026-05-13 — Freescout REST API Migration — Resolution Bridge Phase 2

**Type:** Infrastructure | **Status:** Production ✅

Migrated primary Freescout write operations in `scripts/ai_agent_resolution_bridge.py` from direct MySQL to the Freescout REST API (API & Webhooks module, installed 2026-05-13).

**What changed:**
- `UPDATE conversations SET subject, status, user_id, folder_id, closed_at, ...` → `PUT /api/conversations/{id}`
- `INSERT INTO threads` (note) + `UPDATE threads_count` → `POST /api/conversations/{id}/threads`
- Customer reassignment (mailer-daemon → real customer) folded into API payload as `customerId`
- Folder assignment now auto-managed by API — `get_freescout_folder()` removed from main flow

**What stays SQL (no API equivalent):**
- `get_freescout_conversation()` — subject check + mailbox_id read
- `find_freescout_customer()` — email → customer lookup via `emails` JOIN `customers`
- `close_related_conversations()` — thread body search (`threads.body LIKE '%email%'`)

**API quirks discovered during smoke testing:**
- Status must be string (`"active"`, `"closed"`), not integer (1/3)
- `byUser` (int user_id) required alongside any status change in PUT
- Note thread field is `user` (int), NOT `userId` — API returns 400 otherwise
- Conversation URL uses DB `id` (primary key), not display `number` ✓
- PUT → 204 No Content; POST thread → 201 Created

**Config:** `/opt/odoo-dev/config/freescout_api.json` — `api_url`, `api_key`, `webhook_secret`

---

## 2026-05-13 — Contact Phone Normalization + Employee Form Validation (ueipab_hr_employee v17.0.1.3.0)

**Type:** Data quality + UX hardening | **Status:** Production ✅

**DB fix — 504 phone fields normalized on 324 partners:**
- Tags filtered: Representante, Representante PDVSA, Empleado (371 partners checked)
- Patterns fixed: `4XXXXXXXXXX` → `+584XXXXXXXXXX`, `584XXXXXXXXXX` → `+584XXXXXXXXXX`
- Email records: NOT modified
- 1 manual case remaining: CHENIANA NOGALES (prefix 422, unknown Venezuelan operator)

**Employee Private Info form (`/employee-info/<token>`) — v17.0.1.3.0:**
- `_validate_fields()`: server-side validation — Venezuelan phone must be `+58XXXXXXXXXX`, email must match `name@domain.tld`; invalid → form re-rendered with red inline error
- `_normalize_ve_phone()`: auto-normalizes valid phones on save (spaces/dashes/missing +58 all handled)
- `inp()` helper: `pattern` + `placeholder` attributes on phone/email inputs for browser-level hint
- JS auto-normalizer: strips formatting before submit so `04XX...` and `+58 4XX...` both become `+58XXXXXXXXXX`
- CSS: `.field-error` red border, `.field-error-msg` inline red text

---

## 2026-05-13 — Glenda Payment Receipt OCR (ueipab_ai_agent v17.0.1.38.0)

**Type:** Feature | **Status:** Production ✅ | **Cost:** ~$0.001/image

When a customer sends a payment screenshot (transferencia, pago móvil, Zelle, etc.) via WhatsApp, Glenda automatically detects it and extracts structured data via GPT-4o-mini Vision, then emails a formatted notification to `pagos@ueipab.edu.ve`.

**Pipeline:**
1. Image attachment arrives → `_detect_attachment_type()` → `'image'`
2. Claude Vision handles the conversation as normal (responds empathetically)
3. After Claude reply is sent → `_extract_payment_receipt(url)` called
4. GPT-4o-mini (`detail:high`) extracts: banco, monto, moneda, referencia, fecha, titular_origen, cuenta_destino, tipo_pago
5. If `is_receipt:true` → `_notify_pagos_payment_receipt()` sends structured HTML email to `pagos@ueipab.edu.ve`
6. Odoo chatter logged: `🧾 Comprobante detectado y enviado a pagos@`
7. Non-payment images → `is_receipt:false` → no action, no cost beyond the API call

**Test results (2026-05-13):**
- Plain blue image → `{"is_receipt":false}` ✓ (no false positive)
- Synthetic Banco de Venezuela pago móvil → all 8 fields extracted correctly ✓
  - banco: BANCO DE VENEZUELA · monto: 248760.50 · moneda: VES · referencia: 003847291065
  - fecha: 13/05/2026 · titular: José García · destino: J0800086171 · tipo: pago_movil

**Email to pagos@:** Subject `[Glenda] Comprobante de Pago — {phone} — {banco} {monto} {moneda}`, navy blue header, structured table, green footer asking to verify and apply payment.

---

## 2026-05-13 — Glenda Audio/Voice Note Support (ueipab_ai_agent v17.0.1.35.0)

**Type:** Feature | **Status:** Production ✅ — ACTIVE (OpenAI key set 2026-05-13, ir.config_parameter id=70)

Adds WhatsApp voice note / audio message transcription via OpenAI Whisper API.
Built in response to UX tester feedback (Maria Figuera ×2 — can't type, always sends audios).

**Pipeline:**
1. `_cron_poll_messages` receives audio attachment URL from MassivaMóvil (`_detect_attachment_type` classifies `.ogg/.opus/.m4a` as `'audio'`)
2. `_transcribe_audio(url)` — downloads audio, POSTs to `https://api.openai.com/v1/audio/transcriptions` with `model=whisper-1, language=es`
3. Transcription injected as `message_text` before Claude processes it; stored as message body in Odoo
4. Fallback: API fails or no key → Claude asks user to write instead

**Cost:** ~$0.006/min of audio (voice notes 5-30s → <$0.003 each). OpenAI key: `UEIPAB-Glenda-Whisper`, local backup at `config/openai_api.json`.

**System prompt:** `MENSAJES DE AUDIO` block — Claude treats transcribed text as normal; handles fallback gracefully.

**Production test (2026-05-13):** TTS-generated Spanish voice note transcribed with 100% accuracy in production DB_UEIPAB shell:
- Input: *"Hola buenas tardes, quería consultar sobre la mensualidad... Tengo dos hijos y me gustaría saber si hay algún descuento por hermanos."*
- Whisper output: identical (172 chars), Odoo log confirmed: `Audio transcribed (172 chars): Hola, buenas tardes...`

---

## 2026-05-13 — Glenda OpenAI Moderation Filter (ueipab_ai_agent v17.0.1.37.0)

**Type:** Safety feature | **Status:** Production ✅ | **Cost:** Free

Adds OpenAI Moderation API call (`omni-moderation-latest`) before every Claude invocation.

**Behaviour:**
- Clean message → proceeds normally to Claude (zero latency impact, ~10ms check)
- Flagged message → Glenda replies "No puedo procesar ese tipo de mensaje..." + logs category in Odoo chatter + skips Claude entirely (saves tokens)
- API failure → fail-open (message proceeds to Claude, no customer impact)

**Categories detected:** harassment, threats, sexual content, self-harm, hate speech, violence, and more.

**Test results (2026-05-13):**
- Normal parent inquiry → `flagged=False` ✓
- Abusive message with insults + threats → `flagged=True, categories=['harassment']` ✓
- Frustrated but legitimate complaint → `flagged=False` ✓ (no false positives on emotional language)

**Implementation:** `_check_moderation(text)` in `ai_agent_conversation.py`, hooked in `action_process_reply()` after message logging, before skill handler. Reuses `ai_agent.openai_api_key` param.

---

## 2026-05-13 — Glenda Cashea + Mora Policy Knowledge (ueipab_ai_agent v17.0.1.36.0)

**Type:** Knowledge update | **Status:** Production ✅

Addresses two remaining UX tester suggestions from Calibration Programme.

**Cashea (Jessica Bolívar + Luisa Abreu):**
- Added to `MEDIOS DE PAGO`: "sí aceptamos pagos vía Cashea"
- Glenda confirms acceptance and directs to `pagos@ueipab.edu.ve` to confirm link/process before paying
- Fires `ACTION:HANDOFF` to `billing` route

**Mora e impago policy (Luisa Abreu):**
- Added `POLÍTICA DE MORA E IMPAGO` block
- No formal automatic sanctions policy — each case handled individually by Pagos team
- Glenda responds with empathy, never threatens sanctions, always routes to `pagos@ueipab.edu.ve`
- Fires `ACTION:HANDOFF` to `billing` route

**All 4 calibration UX suggestions now implemented:**
1. ✅ Message conciseness / single farewell (v17.0.1.34.0)
2. ✅ Audio/voice note support (v17.0.1.35.0)
3. ✅ Cashea info (v17.0.1.36.0)
4. ✅ Mora policy (v17.0.1.36.0)

---

## 2026-05-13 — Glenda Message Conciseness Rules (ueipab_ai_agent v17.0.1.34.0)

**Type:** UX improvement | **Status:** Production ✅

Added `REGLAS DE COMUNICACIÓN` block to `general_inquiry` system prompt based on top
feedback theme from the Calibration Programme (4+ mentions from MAIRELSY MOTTA,
GLADYS BRITO CALZADILLA, NIDYA LIRA, Maria Figuera).

| Rule | Detail |
|---|---|
| **Single message per turn** | Consolidate entire response in one message — no consecutive messages on same topic |
| **Single farewell line** | On conversation close, reply with one brief closing line — no stacked goodbyes |
| **No follow-up after goodbye** | If customer says "gracias, hasta luego", respond with a short farewell only — do not add "¿puedo ayudarte en algo más?" |

**Deployment:** `general_inquiry.py` + `__manifest__.py` SCP'd to production, `docker restart ueipab17`.

**Remaining UX tester backlog:** Cashea payment info (needs policy confirmation), mora/impago policy (needs HR text), audio/voice note support (Phase 2, significant dev).

---

## 2026-05-12 — Glenda 2026-2027 Preliminary Tariff Update (ueipab_ai_agent v17.0.1.33.0)

**Type:** Knowledge update | **Status:** Production ✅

Replaced the projected $264,48 Sep 2026 tariffs with the official preliminary pricing
structure approved by management.

| Item | Details |
|------|---------|
| **2025-2026 vigente (hasta 31 ago)** | Mensualidad $197,38 (regular) · Pronto pago $162,39 (10 primeros días del mes) |
| **Promoción inscripción anticipada (hasta 31 jul)** | Inscripción $187,51 · Mensualidad septiembre $197,38 |
| **Nueva mensualidad desde 1 sep 2026** | $218,88 (regular) · $207,93 (pronto pago, 5% dto) — preliminar, sujeto a aprobación Comité Contraloría |
| **Sibling table updated** | 1° $218,88/$207,93 · 2° $207,94/$197,54 · 3° $205,55/$195,27 · 4°+ $203,56/$193,38 |
| **BCV example** | Updated from $197,38 to $218,88 in BCV conversion example in system prompt |
| **Test result** | Glenda responded correctly with all three tariff periods, promoted pronto pago savings ($10,95/mes), offered sibling discount quote, auto-triggered inscripcion flyer |
| **Deployment** | Files SCP'd to production, `docker restart ueipab17` |

---

## 2026-05-11 — Glenda Calibration Programme (ueipab_ai_agent v17.0.1.32.0)

**Type:** Feature | **Status:** Production ✅

Internal employee UX testing programme for Glenda. 20 employees enrolled (Round 1, closed).
Guide emails sent to 19 (YUDELYS BRITO pending personal WA). Deadline: 2026-05-30.

**New:** `ai.agent.feedback` model — stores improvement suggestions by category (flujo,
respuesta, idioma, asistencia, conocimiento, tecnico, otro) with state workflow
(pending → reviewed → implemented/rejected).

**New:** Calibration mode in `general_inquiry` skill — detects enrolled testers by WA
digits match against `glenda_calibracion_v1` ack records; adds transparent testing-mode
system prompt; `ACTION:LOG_FEEDBACK:category|suggestion` auto-creates feedback records.

**New:** Bonus tracker view — `hr.notice.acknowledgment` inherited with computed
`calibration_conversation_count`, `calibration_feedback_count`, `bonus_eligible`
(≥3 conversations + ≥1 suggestion).

**New menus:** AI Agent → Programa Calibración → Sugerencias / Seguimiento de Bono.

**WA number normalization:** All 20 enrolled employees standardized to `+58 XXX XXXXXXX`
on both `hr.notice.acknowledgment.wa_number` and `hr.employee.mobile_phone`.
4 employees corrected from institutional number to personal (private_info_v1 source).

**Day 1 status (2026-05-11):** 13/20 already contacted Glenda, 0 suggestions logged,
0/20 bonus-eligible. Most active: JOSEFINA RODRIGUEZ, Maria Figuera, NIDYA LIRA,
YARITZA BRUCES (2 convs each).

---

## 2026-05-11 — Representante Continuity Survey script (letter pending)

**Type:** Feature scaffold | **Script only — no module change**

`scripts/send_representante_communication.py` — companion to the PDVSA campaign script.
Targets `Representante` tag (id=25, 225 prod partners). Identical infrastructure
(`partner.communication.ack`, `/partner-ack/` routes, 3-button email design).

Five TODO constants at the top of the file must be filled before the script will run:
`LETTER_URL`, `BULLET_1–3`, `EMAIL_HEADLINE`. Hard guard exits cleanly until all are set.
`notice_key`: `representante_continuacion_2026_2027`.

---

## 2026-05-11 — PDVSA Campaign: SMTP From fix (`send_pdvsa_communication.py`)

**Type:** Bug fix | **Script only — no module change**

Gmail SMTP rejects (or silently drops) emails where `From:` is not the authenticated account.
Previous `email_from = votacion@ueipab.edu.ve` was not configured as a "Send As" alias → emails
were marked `state=sent` by Odoo but never delivered.

**Fix:** `email_from` changed to `soporte@ueipab.edu.ve` (authenticated SMTP account).
`Reply-To` stays `votacion@ueipab.edu.ve` so all replies land at the correct mailbox.
Display name `Colegio Andrés Bello` unchanged — recipients see the right name.

**Future option B:** Add `votacion@ueipab.edu.ve` as "Send As" alias in `soporte@` Gmail settings
→ then From can be changed back to `votacion@`.

---

## 2026-05-11 — PDVSA Continuity Campaign (ueipab_attendance_report v17.0.1.6.0)

**Type:** Feature | **Status:** Testing ✅ — Production deploy pending 2026-05-15

New `partner.communication.ack` model + email campaign system for customer-facing surveys/communications.

### Key components

- **Model:** `partner.communication.ack` — one record per partner per `notice_key`; fields: token (UUID), state (pending/continuing/leaving), partner snapshot, ack_date, ack_ip
- **Public routes:** `/partner-ack/<token>/si` (YES), `/partner-ack/<token>/no` (NO), `/partner-ack/<token>` (landing page with all 3 buttons)
- **ACK confirmation:** on every click → email to partner + CC `votacion@ueipab.edu.ve`
- **HR tracking:** Payroll → Reports → Comunicados a Representantes
- **Email design (v4):** decision-first layout — logo → question → 3 stacked full-width buttons (ghost "Ver comunicado" first, then YES navy, then NO gray) → deadline amber callout → 3-bullet summary → signature. Full letter referenced via Google Doc link, not pasted in body.
- **Send script:** `scripts/send_pdvsa_communication.py` (Odoo shell, idempotent, DRY_RUN default)
- **Sender:** `Colegio Andrés Bello <votacion@ueipab.edu.ve>`, reply-to + CC `votacion@`
- **Campaign:** `pdvsa_continuacion_2026_2027` — 71 partners in production, deadline 08-Jun-2026
- **Nginx:** `partner-ack` + `glenda-calibracion` added to dev proxy pattern

### Files added

- `models/partner_communication_ack.py`
- `controllers/partner_ack.py`
- `views/partner_communication_ack_views.xml`
- `scripts/send_pdvsa_communication.py`
- `documentation/PDVSA_CONTINUITY_CAMPAIGN.md`
- `documentation/PDVSA_DEPLOY_FRIDAY_20260515.md`

### Files modified

- `models/__init__.py`, `controllers/__init__.py` — new imports
- `security/ir.model.access.csv` — manager + user access for new model
- `views/menu.xml` — "Comunicados a Representantes" menu entry
- `__manifest__.py` — version bump 17.0.1.5.4 → 17.0.1.6.0, new view added
- `/etc/nginx/sites-available/dev.ueipab.edu.ve` — added `partner-ack|glenda-calibracion`

---

## 2026-05-11 — Liquidación V2 Forecast Report (ueipab_payroll_enhancements v17.0.1.68.2)

**Type:** Feature | **Environments:** Testing + Production

New budget-planning tool that estimates the total liquidation liability for all active V2 employees projected to any target date — without creating payslips.

### Key components

- **Wizard:** `liquidacion.v2.forecast.wizard` + `liquidacion.v2.forecast.line` (TransientModel) — Nómina → Reports → **Pronóstico Liquidación V2**
- **Report model:** `report.ueipab_payroll_enhancements.liq_v2_forecast` (AbstractModel, shortened name to avoid 63-char PG limit)
- **Employee filter:** `res.partner.category` tag "Empleado" (id=19 in production) — partner IDs resolved via raw SQL on `res_partner_res_partner_category_rel`; employees matched via `user_id → partner` OR `work_email` fallback (catches employees without Odoo user like LUIS RODRIGUEZ). Gives exactly **44 employees** in production.
- **As-of date:** defaults to 2026-07-31 (end of academic year). Seniority, progressive rates and service months all projected to that date.
- **Exchange rate:** auto-detects latest VEB rate via `res.currency.rate.company_rate`; manual override field.

### Formula logic (pure Python, no payslips)

All formulas replicate the production LIQUID_VE_V2 salary rules exactly:

| Rule | Formula |
|------|---------|
| Vacaciones | Progressive 15+1d/yr from `ueipab_original_hire_date` × (service_months/12) × daily |
| Prestaciones | (service_months/3) × 15d × integral daily |
| Antigüedad | 2d/month from original hire − already-paid months (via `ueipab_previous_liquidation_date`) |
| Intereses | 13% annual on average prestaciones balance |
| FAOV | −1% × Vacaciones only |
| INCES | $0 (Utilidades excluded) |

### Pre-paid exclusions (Bono Vac + Utilidades)

**Bono Vacacional and Utilidades are always pre-paid by UEIPAB**, so the forecast excludes them from the NET. They are computed (gross reference amounts stored) but zeroed out before totalling. Consequently:
- FAOV = 1% of Vacaciones only (not Vac+Bono+Util)
- INCES = $0

Both columns appear **struck-through grey** in PDF and Excel as informational reference only.

### Output formats

- **Screen:** embedded tree in wizard with optional/hideable columns
- **PDF:** colour-coded table — blue (benefits in NET), grey strikethrough (pre-paid reference), red (deductions), green/gold (NET USD/VEB). Footnote explains exclusions. 3-signature block.
- **Excel (.xlsx):** 18 columns, frozen panes, same colour grouping, strikethrough formatting on pre-paid columns, totals row.

### Production result (2026-05-11, as-of 2026-07-31)

- **44 employees** · **$74,363 total NET** · Rate Bs. 500.46/USD
- Previous total ($88,582) before excluding pre-paid Bono+Util — ~$14K difference = UEIPAB annual pre-paid obligations

### Files added

- `models/liquidacion_v2_forecast_wizard.py` — wizard, line model, `compute_forecast_for_contract()` helper
- `models/liquidacion_v2_forecast_report.py` — AbstractModel for PDF data
- `reports/liquidacion_v2_forecast_report.xml` — QWeb template + `ir.actions.report`
- `wizard/liquidacion_v2_forecast_wizard_view.xml` — form view + window action

### Files modified

- `models/__init__.py` — added two new imports
- `security/ir.model.access.csv` — added access rules for wizard + line models
- `views/payroll_reports_menu.xml` — added menu item (sequence=11)
- `__manifest__.py` — bumped to v17.0.1.68.2, added new data files

---

## 2026-05-11 — Employee Private Info Request System (ueipab_hr_employee v17.0.1.2.0)

**Type:** Feature | **Environments:** Testing + Production

Token-based self-service system for HR to collect and update employee private information. Employees receive a personalized email, click a link, confirm or edit 14 private fields on a public pre-filled form, and submit. HR receives a diff notification.

### Key components
- **Model:** `hr.employee.info.request` — one record per employee per campaign; token UUID, state pending/completed, sent_date, completed_date, completed_ip, JSON diff snapshot
- **Reminder tracking:** `reminder_count`, `reminder_last_date`, `days_pending` (computed). Daily cron auto-sends: 1st reminder at day 3, 2nd at day 7 (max 2 auto-reminders). Manual "Enviar Recordatorio" button on form.
- **Public form:** `/employee-info/<token>` — pre-filled, mobile-friendly, amber highlights for missing fields, 4 sections (Identificación, Contacto Personal, Información Personal, Emergencia, Dirección)
- **Email template:** Navy blue + UEIPAB logo + "📋 Fase 1" amber banner + pre-filled data table + CTA button. CC: `recursoshumanos@ueipab.edu.ve`. Testing id=88, Production id=59.
- **HR diff notification:** sent to `recursoshumanos@ueipab.edu.ve` on every form submission, shows old→new per field
- **HR tracking view:** Employees → Solicitudes de Datos; columns: employee, campaign, state badge, days pending, reminders, last reminder, completed date
- **Nginx:** `/employee-info` added to testing whitelist; production uses catch-all

### Fase 1 campaign — `private_info_v1` (2026-05-11)
- 44 employees from ENERO15 batch (excludes Gustavo Perdomo + 2× Administrador 3Dv)
- All 44 sent at 14:40 UTC; MARIA NIETO completed within 2 minutes
- Private address bulk-fill: 46/47 employees updated to El Tigre / Anzoátegui / 6050 / Venezuela via XML-RPC (all had empty private address fields)
- Note: initial 44 emails sent without CC; template fixed immediately after — reminders will CC HR

**Production template IDs:** email=59 | **Testing:** email=88
**Files:** `models/hr_employee_info_request.py`, `controllers/employee_info_controller.py`, `wizard/`, `data/employee_info_request_template.xml`, `views/hr_employee_info_request_views.xml`, `security/ir.model.access.csv`

---

## 2026-05-10 — Glenda Daily Executive Digest + Invoice Balance Query (ueipab_ai_agent v17.0.1.31.4)

**Type:** Feature | **Environments:** Testing + Production

### Invoice Balance Query — ACTION:QUERY_BALANCE

Glenda can now retrieve and send customers their outstanding invoice balance directly via WhatsApp.

**How it works:**
- If customer is identified by phone → balance pre-loaded in `get_context()` from `account.move` ORM query; Claude answers immediately and appends `ACTION:QUERY_BALANCE:FOUND`
- If customer unknown → Claude asks for cédula, customer provides it → Claude appends `ACTION:QUERY_BALANCE:V-XXXXXXXX`
- Handler: `_handle_balance_action()` → `_query_partner_balance()` → posted invoices with outstanding balance → `_format_balance_message()` with BCV VEB conversion
- Breakdown sent as separate WA message (logged in `ai.agent.message`)
- Security: only shows balance for identified partner

**Files changed:** `general_inquiry.py` (3 new methods + `get_context()` + `get_system_prompt()` + `process_ai_response()`), `ai_agent_conversation.py` (`balance_message` key handling)

### Daily Executive Digest — glenda_daily_digest.py

HTML email sent to `gustavo.perdomo@ueipab.edu.ve` daily at 07:00 VET with previous day's activity summary.

**5 sections:**
1. **KPI cards** — total/resolved/escalated/timeout/active conversations + resolution rate + WA sent/recv + Claude tokens + cost estimate
2. **By-skill table** — per-skill breakdown with avg turns and top topics
3. **Topic frequency** — 12-category keyword detection (inscripciones, saldo/deuda, PDVSA, BCV, etc.) from resolution summaries and escalation reasons — horizontal bar chart
4. **Escalations / unresolved** — table of what Glenda couldn't handle (input for future enhancement roadmap)
5. **Suspicious activity alerts** — same phone >3 convs/day (bot candidate), avg tokens/turn >600 (prompt injection probe), night activity 01:00-05:00 VET, conversations >18 turns

**Cron:** `/etc/cron.d/glenda_daily_digest` — `0 11 * * *` UTC (07:00 VET), sources `/root/.odoo_agent_env_prod`
**Manual run:** `python3 scripts/glenda_daily_digest.py --env production [--date YYYY-MM-DD] [--dry-run]`

---

## 2026-05-10 — Glenda BCV Rate Context (ueipab_ai_agent v17.0.1.31.3)

**Type:** Feature | **Environments:** Testing + Production

### Summary

Glenda (`general_inquiry` skill) can now answer BCV exchange rate questions and USD↔VEB conversion requests in real time, using a 30-minute synced rate context injected directly into her system prompt.

### Architecture

```
BCV MySQL (exchange_rates_bcv.bcv_rates, host localhost)
    ↓  scripts/sync_bcv_to_odoo.py  (cron every 30 min)
ir.config_parameter  ai_agent.bcv_rate_context  (JSON)
    ↓  general_inquiry.get_context()  (read at conversation load)
Claude system prompt  →  Glenda response
```

No runtime DB or HTTP calls from within the Odoo Docker container — the host-side cron pre-populates the param. Zero latency added to conversation processing.

### Files

| File | Change |
|------|--------|
| `scripts/sync_bcv_to_odoo.py` | New — queries BCV MySQL, pushes JSON to both Odoo envs via XML-RPC |
| `/etc/cron.d/sync_bcv_odoo` | New — runs sync every 30 min, sources `/root/.odoo_agent_env_prod` |
| `addons/ueipab_ai_agent/skills/general_inquiry.py` | `_get_bcv_context()` reads ICP param; `_build_bcv_block()` formats prompt block; `get_context()` adds `bcv` key; `get_system_prompt()` injects block |
| `addons/ueipab_ai_agent/__manifest__.py` | Bumped to 17.0.1.31.3 |

### JSON param shape

```json
{
  "current": {"rate": 499.8608, "date": "2026-05-08", "updated_at": "2026-05-10 03:00"},
  "history": [
    {"date": "2026-05-08", "rate": 499.8608, "min_rate": 499.8608, "max_rate": 499.8608},
    ...
  ]
}
```
History: last 30 days, one entry per day (AVG/MIN/MAX). Updated every 30 min.

### Glenda capabilities added

- ¿Cuál es la tasa BCV hoy? → exact rate with effective date
- ¿Cuánto son $197.38 en bolívares? → inline multiplication
- ¿Cuál era la tasa el [fecha]? → looks up history (last 30 days); outside range → directs to `bcv.gob.ve`
- Quotes mensualidades/aranceles in VEB at today's rate on request
- Graceful fallback if param missing: "no disponible, consulta bcv.gob.ve"

---

## 2026-05-10 — Glenda Calibration Programme + Instagram Stories (ueipab_attendance_report v17.0.1.5.2)

**Type:** Feature | **Environments:** Testing → Production

### Summary

Staff introduction campaign for Glenda AI Agent: 4 Instagram story slides + email template with per-employee WA-number ACK tracking for calibration programme bonus calculation.

### Instagram Stories (`scripts/create_glenda_stories.py`)

| Slide | Content |
|-------|---------|
| S1 | Bienvenida — flyer composite + WA badge + 6 capability teaser cards (2-col grid) + Claude AI credit |
| S2 | 5 capability cards (24/7, billing, payslip ACK, HR data, bounce resolution) |
| S3 | Calibration programme — 3 steps + who can participate + bono teaser |
| S4 | Bonus formula (Salario Base ÷ 21.75 per documented weekly session) + CTA |

Output: `/home/ftpuser/odoo-dev/glenda_story_s[1-4].png`

### ueipab_attendance_report v17.0.1.5.1 → v17.0.1.5.2

**Model `hr.notice.acknowledgment`:**
- New field `wa_number` (Char) — WhatsApp number confirmed by employee for Glenda calibration

**Controller `notice_ack.py`:**
- `_WA_FORM_KEYS` set: notice keys that trigger the 2-step WA form instead of one-click ACK
- GET `/notice-ack/<token>` for `glenda_calibracion_v1` → shows WA confirmation form pre-filled from `employee.mobile_phone`
- POST `/glenda-calibracion/<token>` → validates WA number (VE format normalisation), saves `wa_number` on ACK record, updates `employee.mobile_phone` if empty
- **Mismatch detection:** if submitted WA ≠ existing `mobile_phone` → auto-update employee + send HR alert email (old/new number, employee name, timestamp) to `recursoshumanos@ueipab.edu.ve`
- Success page shows amber notice when number was auto-updated

**Views:** `wa_number` column added to ACK list + form views

### Email template (mail.template id=86, testing)

- **Model:** `hr.notice.acknowledgment` (renders per-employee token)
- **Subject:** ¡Bienvenida Glenda! — Confirma tu participación en el Programa de Calibración
- **CC:** `recursoshumanos@ueipab.edu.ve` on every send
- **Body:** intro + 2nd paragraph (ciclo escolar 2026-2027 / ajuste mensualidad / competitividad salarial) + capabilities grid + 3-step programme + bonus formula + per-employee ACK button → `/notice-ack/<token>`
- Body stored via SQL (both `en_US` + `es_VE` JSONB keys)

### Production deployment

- 47 staff emails sent to `@ueipab.edu.ve` addresses (44 employees + gustavo.perdomo + alberto.perdomo + yelitza.chirinos as direct recipients); CC: recursoshumanos@ueipab.edu.ve
- `hr.notice.acknowledgment` records created for each employee (`notice_key=glenda_calibracion_v1`)
- HR tracks registrations at: Nómina → Reports → Notice Acknowledgments → filter `glenda_calibracion_v1`

---

## 2026-05-10 — Glenda AI Agent production deployment (GAP 0 → Phase D)

**Type:** Production Deployment | **Modules:** `ueipab_hr_employee` + `ueipab_bounce_log` + `ueipab_ai_agent` v17.0.1.31.2

### Summary

Glenda deployed to production (`DB_UEIPAB`). All prior testing work (v1.0–v1.31.2) now live. `dry_run=False`, `active_db=DB_UEIPAB`, all 6 host crons targeting production.

### Security hardening (GAP 0)

- Removed hardcoded production Odoo API key and Freescout password from `ai_agent_wa_health_monitor.py` and `daily_bounce_processor.py` — replaced with `os.environ.get()` + `RuntimeError` fail-fast
- Added `RuntimeError` fail-fast to all 6 bridge scripts for `TARGET_ENV=production` without env vars
- Created `/root/.odoo_agent_env_prod` (chmod 600) and `/var/www/dev/.odoo_agent_env_prod` (chmod 640, root:www-data)
- Updated all 5 `/etc/cron.d/ai_agent_*` files: source env file, `TARGET_ENV=production`
- Fixed `akdemia_api_sync.py` production block to use env vars; `customer_matching_wrapper.sh` sources env file
- Updated `.gitignore`: added `.odoo_agent_env_prod`, `google_sheets_credentials.json`

### Module installation (GAP 1 + GAP 2)

- DB backup: `/backup/DB_UEIPAB_20260510_pre_ai_agent.dump`
- `PyMuPDF (fitz)` installed in production container (was missing, blocked install)
- `__init__.py` updated: added `/etc/odoo` to config search paths (production container mount point for `/home/vision/ueipab17/config/`)
- Config params loaded manually via Odoo shell after install (post_init_hook searched wrong path)
- 6 skills + 7 crons created; 2 deferred (Timeouts, HR Collection)

### Cron switch (GAP 4 + GAP 10)

- All 5 host AI agent crons switched to production; testing locked (`active_db=''`)
- Akdemia pipeline: `customer_matching_wrapper.sh` now sources production credentials
- Dry-run verified all 5 bridge scripts against production before go-live

### Go-live (Phase D)

- `ai_agent.dry_run = False` set on production Odoo
- `ai_agent.claude_spend_limit_usd = 4.15` (90% of ~$4.61 Anthropic credit remaining after testing)
- Initial bounce load: 2 records created (dcontrerasperez82@gmail.com tier=not_found, lacruzde@pdvsa.com tier=flag)
- Poll cron running at 5 min interval; webhook deferred (poll sufficient for current volume)

### Post-deploy TODOs

- Enable "Check Conversation Timeouts" cron after 48h stable
- Phase 2: enable "Stagger HR Data Collection" cron
- Raise `claude_spend_limit_usd` on each Anthropic credit top-up
- Optional: add nginx `/ai-agent/` proxy on production server for <1s webhook responses

---

## 2026-05-10 — Odoo 17.0 base container update (both environments)

**Type:** Infrastructure | **Environments:** Testing + Production

### Summary

Both Odoo containers updated from `17.0-20251106` (testing) / `17.0-20250807` (production) to `17.0-20260504` — closing a 6–9 month upstream gap.

| Environment | Before | After | Gap closed |
|-------------|--------|-------|------------|
| Testing | `17.0-20251106` (`cdf3ad5c`) | `17.0-20260504` (`d66bb0d7`) | 6 months |
| Production | `17.0-20250807` (`2026212d`) | `17.0-20260504` (`d66bb0d7`) | 9 months |

### Upstream fixes now applied

| Module | Key fix |
|--------|---------|
| `mail` | Duplicate records on concurrent email processing (`a4d3386`) |
| `mail` | Ignore archived email blacklists (`3e70e71`) |
| `mail` | Sanitize `mail.catchall.domain.allowed` (`7324c39`) |
| `account` | Stop rounding discount on import (`7ebce9b`) |
| `account` | Allow branch users to create journal currency transactions (`05e9714`) |
| `web` | PERF: respect limit during onchange fetch (`14d3893`) |
| `web` | Fix translation button save on nested records (`9da5291`) |
| `web` | Realign x2many cache filtering in web_read (`0b2356d`) |
| `hr_attendance` | Checkout employee when archived (`ca8e687`) |
| `hr` | Clear bank account on employee duplication (`94e4f85`) |
| `hr_holidays` | Leave dual-approval fallback fix (`e834bf7`) |

### Procedure

1. Pre-update compatibility audit — all UEIPAB custom modules: no hard blockers (MEDIUM risk areas verified via smoke tests)
2. Testing DB backup: `testing_backup_before_odoo_update_20260510_082038.sql.gz`
3. `docker pull odoo:17.0` on both servers
4. `docker-compose down && docker-compose up -d` — testing first, production after validation
5. Module upgrade: `ueipab_payroll_enhancements -u` (registers wizard models in DB)
6. Full smoke test suite: 18/18 checks passed on testing, 11/11 on production

### Notes

- `ueipab_ai_agent` not installed in production — `ai.agent.conversation` missing there is expected
- Pre-existing transient vacuum error from `base_accounting_kit` (unrelated to update)
- Production had a stale container name conflict (`/ueipab17`) — resolved with `docker rm -f` before `docker-compose up -d`
- Both environments now on identical image digest: `sha256:f4d974041d580ef358ab2d7a49a67439252797a791b7799d3a3432da3ac92722`

---

## 2026-05-09 — Glenda institutional knowledge update (ueipab_ai_agent v17.0.1.31.2)

**Module:** `ueipab_ai_agent` v17.0.1.31.2 | **Status:** Testing

### Leadership & privacy policy (`general_inquiry.py`)

Two new sections added to `_INSTITUTIONAL_KNOWLEDGE`:

**AUTORIDADES INSTITUCIONALES ACTUALES**
- Director General: Prof. Arcides Arzola → soporte@ueipab.edu.ve
- Sub-directora (Media General y Bachillerato): Prof. Norka La Rosa → soporte@ueipab.edu.ve
- Sub-director (Inicial, Preescolar y Primaria): Prof. David Hernández → soporte@ueipab.edu.ve
- Fundadora histórica (1977): Carmen Violeta Mata de Perdomo

**POLÍTICA DE PRIVACIDAD INSTITUCIONAL**
- Glenda must NEVER reveal the name of the legal owner/shareholder.
- If asked "¿quién es el dueño?" or similar: redirect to academic authorities (Director/Sub-directors) + soporte@ueipab.edu.ve.
- The founder (Carmen Violeta Mata de Perdomo) may be mentioned in historical context.
- Guard also added in `get_system_prompt()` INSTRUCCIONES block.

**Trigger:** A tester asked Glenda "¿quién es el dueño del colegio?" and she responded with the business owner's name (Alberto Perdomo), which is confidential information. This update prevents that disclosure.

---

### Industry workers credit policy — Comunicado 08/05/2026 (`general_inquiry.py`)

Full content of the official May 8, 2026 communicado added to `_INSTITUTIONAL_KNOWLEDGE` and `get_system_prompt()`.

**`POLÍTICA FUERZA LABORAL INDUSTRIA`** block (replaces the old `POLÍTICA PDVSA / PETROPIAR` block):

| Topic | Detail |
|---|---|
| Scope | PDVSA, Petropiar, and **all other industry companies** |
| Policy change | 35% credit discount ceases September 1, 2026 |
| Nature of benefit | Always voluntary concession, not an acquired right |
| Reason | Operational cost obligations to staff and suppliers |
| **Confirmation deadline** | **08 June 2026 at 12:30 p.m.** — written notice to pagos@ueipab.edu.ve required. Silence = acceptance of new conditions |
| Casos Especiales | Individual review (no general exceptions) for: excellent academic record, national-medal athletes, active Sistema de Orquestas Juveniles musicians, or recognized outstanding skills |
| Tuition increase 2026-2027 | Projected 20–34% adjustment (pending Comité de Contraloría). Non-tuition costs (insurance, olympiads, textbooks, contests) billed separately |
| Local alliances | Almacén París, Comercial Caracas, Ferretería Veramar — discounts on uniforms and school supplies |

**Instruction block updates (`MANEJO ESPECIAL FUERZA LABORAL INDUSTRIA`):**
- New prospect from any industry company → policy explanation + billing handoff
- Existing distressed family → empathy + deadline reminder + Caso Especial hint + pdvsa_retention handoff
- Deadline question → exact date/time answer (08/06/2026 12:30 p.m.)
- Caso Especial question → eligibility criteria + pagos@ referral
- Tuition increase question → 20–34% projection + pagos@ referral

---

## 2026-05-08 — Notice Acknowledgment system + email template fixes

**Module:** `ueipab_attendance_report` v17.0.1.5.0 | **Status:** Testing validated

### hr.notice.acknowledgment — new model

Generic acknowledgment tracking for any institutional communication:

| Field | Type | Notes |
|-------|------|-------|
| `notice_key` | Char | Machine key e.g. `attendance_guide_v1` |
| `notice_label` | Char | Human-readable title |
| `employee_id` | Many2one | `hr.employee` |
| `token` | Char | UUID auto-generated on create |
| `state` | Selection | `pending` / `acknowledged` |
| `sent_date` | Datetime | Auto-set on create |
| `ack_date` | Datetime | Set by controller on click |
| `ack_ip` | Char | IP at time of click |
| `days_pending` | Integer | Computed, non-stored |

**Public controller:** `/notice-ack/<token>` — `auth='public'`, no login required. Records `state=acknowledged`, `ack_date`, `ack_ip`. Returns styled HTML pages: success / already-done / invalid token.

**Views:** tree (badge status, decoration), form (Manual Acknowledge + Reset buttons), search (Pending / Acknowledged filters, Group by Notice / Status / Employee).

**Menu:** Payroll → Reports → Notice Acknowledgments (sequence 95).

**Security:** `hr_payroll_community_manager` = CRUD, `hr_payroll_user` = read-only.

### Email template (id=84 testing) — updated to hr.notice.acknowledgment model

- Model changed from `hr.employee` to `hr.notice.acknowledgment`
- Employee name: `<t t-out="object.employee_id.name"/>` via QWeb
- Green ACK button: `<a t-att-href="object._get_ack_url()">` — unique URL per send
- CC: `recursoshumanos@ueipab.edu.ve` on every send
- `email_to`: `{{ object.employee_id.work_email }}`
- Send flow: create `hr.notice.acknowledgment` record → `send_mail(ack.id)` → email to employee

### Infrastructure fixes

- **nginx** (`/etc/nginx/sites-available/dev.ueipab.edu.ve`): added `attendance-ack`, `attendance-fix`, `attendance-correction`, `notice-ack` to the Odoo proxy location regex so public routes reach Odoo on port 8019
- **odoo.conf** `dbfilter`: changed from `^(DB_UEIPAB|testing|openeducat_demo)$` to `^testing$` — Odoo now auto-selects the `testing` DB for public (cookieless) requests, enabling `/notice-ack/` and `/attendance-ack/` routes to function
- **`web.base.url`**: updated from `http://dev.ueipab.edu.ve:8019` to `https://dev.ueipab.edu.ve` — all generated links (ACK buttons, attendance report links) now use the correct HTTPS URL

### asistencia_story_s2.png — card overflow fix

Three contingency card heights were too small, causing text and note bars to overflow outside their boundaries:

| Card | Old height | New height | Root cause |
|------|-----------|-----------|------------|
| Odoo Dashboard | 195px | 250px | Note bar ended at y+230, outside 195px |
| Docentes | 210px | 278px | Note bar ended at y+262, outside 210px |
| Admin & Mant. | 210px | 278px | Note bar ended at y+262, outside 210px |

Added `?v=2` cache-buster to `asistencia_story_s2.png` URL in both testing (id=84) and production (id=58) templates to force email clients to re-fetch the corrected image.

### Production template (id=58) — CC and s2 fix applied live

Both the CC (`recursoshumanos@ueipab.edu.ve`) and the `?v=2` cache-buster were applied to production template id=58 via XML-RPC write with explicit `lang` context for both `en_US` and `es_VE` JSONB keys.

---

## 2026-05-08 — Gestión de Control de Asistencia — Guía Visual para Empleados

**Tipo:** Asset operacional + actualización conocimiento Glenda | **Estado:** Testing validado, listo para producción

### Componentes

**1. Instagram Stories — 4 slides PNG (1080×1920 px)**
Script: `scripts/create_attendance_story.py` | Output: `/home/ftpuser/odoo-dev/` → `/var/www/dev/flyers/`

| Slide | Contenido |
|---|---|
| S1 | Jerarquía del sistema: Kiosko (obligatorio) + 3 contingencias |
| S2 | Detalle de los 3 métodos de contingencia con pasos |
| S3 | Preview del reporte quincenal por email + leyenda de íconos |
| S4 | 4 pasos de acción + alerta política 1° junio 2026 |

Jerarquía de registro: Kiosko (obligatorio) → Dashboard Odoo Check In/Out (contingencia digital) → Control de Asistencias (contingencia docentes) → WiFi UEIPAB ≥2h (contingencia admin/mant).

**2. Email Template `mail.template` — Testing id=83**
- Nombre: `Gestión de Control de Asistencia — Guía Visual para Empleados`
- Modelo: `hr.employee` | From: `recursoshumanos@ueipab.edu.ve`
- Carousel horizontal con las 4 stories + resumen + alerta junio 2026
- Script: `scripts/setup_attendance_email_template.py`
- **Nota técnica:** `body_html` es JSONB multilingual (`render_engine='qweb'`). Siempre actualizar via SQL directo con AMBAS claves `en_US` y `es_VE`. El sistema usa `es_VE`; solo actualizar `en_US` deja el ORM leyendo la versión antigua.

**3. Glenda (`general_inquiry.py`) — conocimiento actualizado**
- Kiosko como método principal obligatorio
- Dashboard Odoo Check In/Out como contingencia digital #1
- Control de Asistencias y WiFi reenmarcados como contingencia automática
- 3 nuevas FAQs sobre uso del Dashboard, impacto en nómina desde junio, qué pasa sin ningún registro
- Lógica de Glenda: Kiosko → Dashboard Odoo → Control/WiFi → enlace corrección

---

## 2026-05-08 — Payroll Disbursement Detail: 4 employee date columns (v1.67.6)

**Module:** `ueipab_payroll_enhancements` | **Deployed:** Testing + Production

Added 4 employee contract date columns to the Payroll Disbursement Detail report (both PDF and Excel output), inserted after `VAT ID` and before `Cuenta`:

| Column header | Source field | Notes |
|---|---|---|
| Ing. Original | `contract_id.ueipab_original_hire_date` | Original hire date (rehire antigüedad continuity) |
| Ini. Contrato | `contract_id.date_start` | Last contract start date |
| Ult. Liq. | `contract_id.ueipab_previous_liquidation_date` | Date of last liquidation settlement |
| Ult. Vac. | `contract_id.ueipab_vacation_paid_until` | Vacations paid through this date |

Dates display as `DD/MM/YYYY`; shows `-` (PDF) or blank (Excel) when field is empty on contract.
PDF column widths rebalanced to fit within landscape width. Excel column indexes shifted +4 for all financial columns.

**Files changed:** `__manifest__.py` (v1.67.5 → v1.67.6), `reports/payroll_disbursement_detail_report.xml`, `models/payroll_disbursement_wizard.py`

---

## 2026-05-07 — Mikrotik Hotspot digest always sent to HR

Fixed `sync_mikrotik_attendance.py` to send the daily HTML summary email to `recursoshumanos@ueipab.edu.ve` on every live run — previously only sent when at least one record was created. HR now receives both digests (control_asistencias + Mikrotik) every weekday as cron confirmation.

---

## 2026-05-07 — Mikrotik Hotspot → Odoo Attendance Bridge (Phase 1, Production)

**New script:** `scripts/sync_mikrotik_attendance.py` — daily cron (18:35 VET) that reads active WiFi sessions from Mikrotik hAP ac³ hotspot and creates `hr.attendance` records for staff present on-site. Runs AFTER control_asistencias sync — only fills gaps.

### Architecture
- Source: `/ip hotspot active print detail` via SSH (paramiko, 172.28.10.10, odooapi)
- Mapping: `wifi_hotspot_users` table (payroll_db) + dynamic generation via `username_helper.py` → 94 usernames for 47 employees
- Two usernames per employee: laptop (`gperdomo`) + cellphone (`celgperdomo`)
- Odoo write: XML-RPC (same credentials as control_asistencias sync)
- Email: HTML summary to recursoshumanos@ueipab.edu.ve

### Confidence criteria
- `uptime >= 120 min` (device connected for significant portion of day)
- `login_time = poll_time - uptime` must be before 14:00 VET
- Excludes: `invitado`, `laptop*`, unregistered users

### Priority
control_asistencias record exists → Mikrotik skipped for that employee. Only fills gaps (admin, maintenance, directors).

### Fixes applied
- `jhernandez` / `celjhernandez` in wifi_hotspot_users had typo email (`ueaipab` → `ueipab`)
- `aarcides` / `celaarcides` (ARCIDES ARZOLA) added with non-standard username
- wifi_hotspot_users: 14 → 16 explicit registrations

### Cron
Phase 1 (22:30 UTC) → control_asistencias; Phase 2 (22:35 UTC) → Mikrotik hotspot. Both in `/etc/cron.d/sync_control_asistencia`.

---

## 2026-05-07 — Control Asistencia → Odoo Attendance Bridge (Testing)

**New script:** `scripts/sync_control_asistencia.py` — daily cron that reads teacher activity from the `control_asistencias` Flask/MySQL app and auto-creates `hr.attendance` records in Odoo for teachers who conducted class. No biometric system required.

### How it works
1. Queries `asistencia_estudiante` grouped by `(id_usuario, fecha)` — any teacher who submitted student attendance records = was physically present at school
2. Matches teachers to Odoo employees by `email` (control_asistencias `usuario.email` = Odoo `hr.employee.work_email`)
3. For each matched teacher with no existing Odoo attendance for that day → inserts clean record: `07:00–13:30 VET` (11:00–17:30 UTC), 6.5h
4. Skips if record already exists (idempotent)
5. Sends HTML summary email to `recursoshumanos@ueipab.edu.ve`

### Key facts
- control_asistencias DB: `mysql://control_asist@localhost/control_asistencias`
- Tested 2026-05-07: 19 teachers detected, 18 matched to Odoo, 18 records created
- FLORMAR HERNANDEZ was the only ⚠ no-match in testing (temp email swap for testing purposes — matches correctly in production)
- Idempotency confirmed: re-run skips all existing records

### Cron installed
`/etc/cron.d/sync_control_asistencia` — weekdays 22:30 UTC (18:30 VET), currently `--env testing`

### Production deployment: LIVE 2026-05-07
- XML-RPC backend implemented for production (psycopg2 only for testing)
- API key created for admin uid=2 in DB_UEIPAB (`res_users_apikeys` id=3)
- Backfill May 4–7 school days completed (6 new records created, rest skipped/overlapped)
- Overlap handling: ORM constraint caught gracefully → counted as skip, existing record kept
- Cron updated to `--env production`, runs weekdays 22:30 UTC (18:30 VET)
- Summary email queued as `state=outgoing` → delivered by Odoo mail cron within 1 min

---

## 2026-05-07 — ueipab_attendance_report v17.0.1.4.0 — Resend Report Button + Wizard Resend Mode

**Enhancement:** HR can now resend attendance report emails from two places — the report form and the generation wizard.

### Enhancement 1 — Report form view
- **"Enviar Correo"** (primary, blue) shown only when `state == 'draft'`
- **"📧 Reenviar Correo"** (secondary, grey) shown for `sent` and `acknowledged` states
- Both call the same `action_send_email()` — resending resets state to `sent` for non-historical reports so HR can track re-acknowledgment

### Enhancement 2 — Wizard resend mode
- New **"Solo reenviar reportes existentes (sin generar nuevos)"** checkbox in the wizard
- When checked: yellow info banner appears, `send_email` checkbox hides, "Generar Reportes" button becomes **"📧 Reenviar Reportes"**
- `action_resend_reports()`: finds existing `hr.attendance.report` records for the selected period + employees and calls `_send_emails()` on them — no new records created
- Works with both single-quincena and range modes
- Returns filtered list view of resent reports

### Deployed
- Testing: 2026-05-07 — validated with LUISA ELENA ABREU (temp email swap)
- Production: 2026-05-07 — synced + upgraded DB_UEIPAB + restarted

---

## 2026-05-07 — Payslip Ack — Manual confirmation + reminder (production)

- **5 payslips manually acknowledged** via Odoo shell: ANDRES MORALES (SLIP/580, SLIP/673, SLIP/700) and PABLO NAVARRO (SLIP/672, SLIP/693). `is_acknowledged=True`, `acknowledged_ip='Manual - HR'`, chatter note added per payslip.
- **1 reminder sent** to RAMON BELLO (SLIP/655, ABRIL15) → `ramon.bello@ueipab.edu.ve` (reminder #4).
- Production status: **584 / 585 acknowledged** (99.8%). Only SLIP/655 RAMON BELLO pending.

---

## 2026-05-06 — ueipab_attendance_report v17.0.1.3.4 — Self-Service Attendance Correction

**New feature:** Employees can self-report attendance incidencias via a public form; HR approves in one click.

### Full correction flow
1. Employee clicks **"Solicitar Corrección de Asistencia"** button in their report email (visible when `absent_days > 0`)
2. Public form at `/attendance-fix/<token>` — no login: date dropdown (past only), AM/PM time pickers, 8 LOTTT/LOPCYMAT motivos, optional file attachment (PDF/JPG/PNG, max 5MB)
3. HR receives notification email with direct **"Revisar Solicitud en Odoo"** button → `/attendance-correction/<id>` (login-safe redirect)
4. HR opens `Nómina → Reportes → Solicitudes de Corrección` → pending queue highlighted in yellow
5. HR clicks **✅ Aprobar** → attendance record created via SQL (bypasses overlap constraint), employee notified by email, form reloads to show Aprobado state
6. HR clicks **📧 Reenviar Reporte al Empleado** → employee gets updated report (corrected ✅) with ACK button
7. Employee clicks **Confirmar Recepción** → ACK registered

### Technical details
- New model `hr.attendance.correction` (pending/approved/rejected, attachment_ids M2M, token)
- New controller `/attendance-fix/<token>` (public) + `/attendance-correction/<id>` (auth='user', login-safe redirect)
- 3 email templates: HR notification, employee approval, employee rejection
- `action_approve()`: SQL INSERT to `hr_attendance` (bypasses overlap), sends approval email, reloads form via `next` action
- Mail server `from_filter` widened to `ueipab.edu.ve` domain — HR emails send from `recursoshumanos@ueipab.edu.ve`
- UX fixes: AM/PM dropdowns, LOTTT motivo select + JS dynamic label, file upload widget, attachments inline below motivo in Odoo form

### LOTTT/LOPCYMAT predefined motivos
Corte de energía eléctrica · Consulta/emergencia médica (Art. 49) · Reposo médico · Duelo familiar (Art. 49) · Citación judicial · Matrimonio (Art. 49) · Calamidad doméstica · Otro motivo (free text)

### Production note — after upgrade set mail server from_filter
```bash
docker exec ueipab17 /usr/bin/odoo shell -d DB_UEIPAB --no-http <<'EOF'
server = env['ir.mail_server'].search([], limit=1)
server.from_filter = 'ueipab.edu.ve'
env.cr.commit()
print("Done:", server.from_filter)
EOF
```

---

## 2026-05-06 — ueipab_attendance_report v17.0.1.2.0 — Special Schedule Support

**Enhancement:** Maintenance/security staff with non-standard rotating schedules handled correctly.

### Problem solved
Without this feature: ANDRES MORALES (3 days/week rotation) would show **8 false ❌ absences per quincena**. SERGIO MANEIRO's **18 weekend shifts** were invisible (shown as `─ No hábil`).

### What changed
- New `STATUS_CFG` entry `'dayoff'` — light blue-gray, shown for special employees on weekdays with no attendance (not a penalty)
- Weekend attendance **now visible** for special employees (`ok`/`missing_exit` with actual times)
- `absent_days` always 0 for special employees — no false penalties
- `complete_days` counts ALL days including weekends for special employees
- `get_status_info()` returns `⭐ Horario especial` informational banner instead of ok/warning/danger
- `is_special_schedule` computed field on `hr.attendance.report` — exposed to QWeb
- Email template: `dayoff` row ("Día libre"), conditional summary box (no absent row), legend updated
- New `_get_special_schedule_employees()` reads `attendance_report.special_schedule_employees` system param (comma-separated IDs)

### Configuration (production)
After module install, set via Settings > Technical > Parameters:
```
Key:   attendance_report.special_schedule_employees
Value: 571,606,610
```
| ID | Employee | Role |
|----|----------|------|
| 571 | ANDRES MORALES | Mantenimiento |
| 606 | PABLO NAVARRO | Mantenimiento |
| 610 | SERGIO MANEIRO | Seguridad |

### Director analysis (validated in testing)
Synced ARCIDES ARZOLA (572), DAVID HERNANDEZ (576), NORKA LA ROSA (605).
**Directors follow standard Mon-Fri, zero weekend work** → no special schedule needed, report handles them correctly. Feb 2026 Q1: DAVID 10/10 present, NORKA 9/10, ARCIDES 8/10 (2 absences flagged for HR review).

### Sync scripts
- `scripts/sync_maintenance_attendance.py` — ANDRES, PABLO, SERGIO (385 records)
- Directors synced inline (340 records); work_email unchanged for all — no test emails

---

## 2026-05-06 — ueipab_attendance_report v17.0.1.1.0 — Holiday Support

**Enhancement:** Official Venezuelan national holidays are now excluded from absent-day counts.

### What changed
- New `STATUS_CFG` entry `'holiday'` — light-blue row (📅), shown when a weekday has no attendance AND is a configured public holiday
- `_get_holiday_dates()` reads `attendance_report.holidays` system parameter (JSON array `[{"date":"YYYY-MM-DD","name":"..."}]`)
- `get_attendance_days()` marks unworked holidays as `'holiday'` instead of `'absent'`; if attendance IS recorded on a holiday, actual data takes precedence
- `workday_count` now excludes holidays (employees are no longer penalized for official days off)
- New `holiday_days` computed field — appears in summary box only when `> 0`
- Email template: holiday row spans the three time columns and shows the holiday name in italics; legend updated; summary box shows "Feriados oficiales: 📅 N"
- Form view HTML table: holiday row uses colspan=3 with holiday name; legend updated
- New `data/holidays_config.xml` — 12 holidays loaded as `noupdate="1"` system parameter

### Holidays configured (2025-2026 academic year)
| Date | Holiday |
|------|---------|
| Oct 12, 2025 | Día de la Resistencia Indígena |
| Dec 25, 2025 | Navidad |
| Jan 1, 2026 | Año Nuevo |
| Feb 16-17, 2026 | Carnaval |
| Apr 2-3, 2026 | Jueves y Viernes Santos |
| Apr 19, 2026 | Declaración de Independencia |
| May 1, 2026 | Día del Trabajador |
| Jun 24, 2026 | Batalla de Carabobo |
| Jul 5, 2026 | Día de la Independencia |
| Jul 24, 2026 | Natalicio de Simón Bolívar |

**Note:** HR can add MPPE-specific pedagogical days via Settings > Technical > Parameters > `attendance_report.holidays` without losing them on upgrades (`noupdate="1"`).

### Verified in testing
- Dec 2025 Q2 (NIDYA LIRA): Dec 25 detected as Navidad → `holiday_days=1`, `workday_count=11`
- Jan 2026 Q1: Jan 1 detected as Año Nuevo → `holiday_days=1`, `workday_count=10`
- Apr 2026 Q1: Apr 2+3 detected as Semana Santa → `holiday_days=2`, `workday_count=9`
- Oct 12 (Sunday) correctly handled as weekend (not double-counted)

### Receso Navideño added (same date, separate commit c3cd9ad)
18 weekdays Dec 15–Jan 11 added as "Receso Navideño" (MPPE official: recess Dec 15, classes resume Jan 12).
Dec 25 stays "Navidad", Jan 1 stays "Año Nuevo". Total holidays in config: **30 entries**.
Result: Dec Q2 → `workdays=0 absent=0`; Jan Q1 → `holidays=7 workdays=4`.

### Production deployment note
`attendance_report.holidays` **auto-created** by module install (30 entries from `holidays_config.xml`, `noupdate="1"`).

---

## 2026-05-06 — ueipab_attendance_report v17.0.1.0.0 — READY FOR PRODUCTION

**New standalone module** — zero changes to `ueipab_payroll_enhancements`.
**Status:** Validated in testing with NIDYA LIRA (108 real production attendance records). Awaiting production maintenance window.

### Post-validation fix (same date)
- **Danger banner message** — Updated to Opción 1 professional tone: "Su registro actual presenta un total de N incidencias (...). Le recordamos que las inasistencias no justificadas o que presenten inconsistencias sin informar podrían generar descuentos automáticos. Este nuevo mecanismo de control entrará en vigor de manera efectiva a partir del 1 de junio de 2026."

### Production deployment checklist
| Step | Action |
|------|--------|
| A | `scp -r addons/ueipab_attendance_report root@10.124.0.3:/home/vision/ueipab17/addons/` |
| B | `docker exec ueipab17 /usr/bin/odoo -d DB_UEIPAB -i ueipab_attendance_report --stop-after-init` |
| C | `docker restart ueipab17` |
| D | Open Payroll → Reports → Reporte de Asistencia Quincenal |
| E | Mode: Rango de meses · Oct 2025 → current month · Todos los empleados · ✓ Enviar correo |
| F | Verify: Oct 2025–Apr 2026 → state=Confirmado (auto-ack, informational email) |
| G | Verify: current quincena → state=Enviado (ACK button in email) |

**Note:** No DB_UEIPAB schema risk — new module, no changes to existing tables.

### Features delivered
| # | Feature | Detail |
|---|---------|--------|
| 1 | `hr.attendance.report` model | Per-employee quincenal attendance snapshot with ack_token, state (draft/sent/acknowledged), summary stats, VET UTC-4 timezone handling |
| 2 | Wizard — single quincena | Year/month/quincena picker, dates auto-computed, employee 3-mode filter (all/department/manual), live counter |
| 3 | Wizard — bulk range mode | Select month range → generates Q1+Q2 for every month up to today; designed for production backfill Oct 2025 onward |
| 4 | HTML table preview | Day-by-day attendance table rendered in Odoo form view (`_build_html_table`) |
| 5 | QWeb email template | No attachment, inline body: week tables, status banner (ok/warning/danger), legend, ACK button |
| 6 | ACK controller | `/attendance-ack/<token>` public route — records ack_date + IP, three confirmation pages |
| 7 | `is_historical` auto-ack | Periods before current month: auto-acknowledged on `create()`, email shows informational footer instead of ACK button — prevents HR headaches on backfill sends |
| 8 | Menu | Payroll → Reports → Reporte de Asistencia Quincenal + Reportes Generados (Asistencia) |

### Key design decisions
- `is_historical` cutoff = first day of current month (self-updating, no magic number)
- `_send_emails()` does not downgrade `acknowledged → sent` for historical records
- `noupdate` removed from template XML — body reloads on every upgrade (dev phase)
- Year fields as `Char` to prevent locale "2,026" formatting
- Radio button groups use `col="1"` for proper left-aligned layout

### Test data
- NIDYA LIRA: 108 attendance records synced from production via `scripts/sync_nidya_attendance.py`
- Work email set to `gustavo.perdomo@ueipab.edu.ve` for testing
- Discount policy effective date in danger banner: **1 de junio de 2026**

---

## 2026-05-06 — LO module sync: testing → production (no version bump)

**Production-only DB fix. No code change.**

| Item | Fix |
|---|---|
| Payslip Email (id=37) | Loan block was appended **after** closing `</div>` — invisible in emails. Replaced full body with testing version: block now inside deductions table, uses `object.get_line_amount()` for both `VE_LOAN_DED_V2` + `LIQUID_LOAN_DED_V2`, correct `'{:,.2f}'` format. `es_VE` translation added. |
| Adelanto Prestaciones (id=50) | Body synced to match testing id=71 (was 224 bytes different). Missing `es_VE` translation added. |
| `VE_TOTAL_DED_V2` (id=19) | Deploy script had appended the loan line leaving two `result =` assignments. Removed duplicate first line. |
| `LIQUID_NET_V2` (id=34) | Same issue — removed duplicate first `result = (...)` block. |

**Script:** `scripts/sync_lo_to_production.py`

---

## v1.66.5 — 2026-05-05 — Backdated loan approval JE date fix

**Files:** `hr_loan_extension.py`, `__manifest__.py`

| Change | Detail |
|---|---|
| `_create_advance_journal_entry()` date fix | When `loan.date` is in a past calendar month, use `today` as the JE date instead. Prevents PAY1 sequence/date mismatch error when approving historical advances. `loan.date` stays unchanged as the disbursement record. |

**Root cause:** PAY1 enforces chronological sequence continuity. If loan date is February 2026 but PAY1 is already at `PAY1/2026/04/xxxx`, Odoo rejects the entry with "Date doesn't match sequence number". HR workaround was to change loan date before approving — now automatic.

---

## v1.66.4 — 2026-05-05 — Option B conservative + batch cancel + payslip cancel fix

**Files:** `hr_loan_extension.py`, `hr_payslip.py`, `hr_payslip_run.py`, `__manifest__.py`

| Change | Detail |
|---|---|
| Option B — conservative | `action_compute_sheet()` only adds LO inputs when the payslip has **zero** LO inputs. If any LO input already exists HR is managing them manually — no interference. Handles "loan approved after batch generation" without re-adding deliberately deleted inputs. |
| Batch cancel → cancels draft payslips | `action_cancel()` filter changed from `state not in ('cancel','draft')` to `state != 'cancel'`. Draft payslips now correctly cancelled with their batch. |
| `action_payslip_cancel()` override | For `done` payslips: resets posted JE to draft via `button_draft()`, cancels via `button_cancel()`, then sets `state='cancel'`. Draft/verify payslips bypass JE handling. |

> **v1.66.2–v1.66.3** were intermediate steps: v1.66.2 added additive-only Option B; v1.66.3 attempted an `act_window` display workaround. Both superseded by v1.66.4.

---

## v1.66.1 — 2026-05-05 — Batch cancel includes draft payslips

**Files:** `hr_payslip.py`, `hr_payslip_run.py`, `__manifest__.py`

| Change | Detail |
|---|---|
| Filter fix | `action_cancel()` was filtering `state not in ('cancel','draft')` — draft payslips silently survived batch cancellation. Fixed to `state != 'cancel'`. |
| JE cancel on done payslips | `action_payslip_cancel()` override: posted journal entry reset to draft + cancelled before setting payslip state. |

---

## v1.66.0 — 2026-05-05 — Multiple Loans per Employee

**Files:** `hr_loan_extension.py`, `liquidacion_breakdown_report.py`, `setup_loan_rules.py`, `__manifest__.py`

| Change | Detail |
|---|---|
| No loan constraint | `HrLoan.create()` bypasses ohrms_loan one-loan-per-employee check via MRO (`super(ohrms_cls, self)`). Unlimited concurrent loans allowed (Option A). |
| `get_inputs()` rewrite | One LO input per active matching loan. Finds earliest unpaid installment with `date ≤ payslip.date_to` — handles skipped periods. Removes ohrms_loan last-wins bug. HR can zero any LO input to skip that loan this period. |
| `action_payslip_done()` rewrite | Uses `loan_line_id` on each input directly. Reverts `paid=True` for zero-amount LO inputs (HR skip). Writes `payslip_id` back for paid ones. |
| Salary rule formula | `VE_LOAN_DED_V2` and `LIQUID_LOAN_DED_V2` now: `slip = payslip.dict; result = -sum(l.amount for l in slip.input_line_ids if l.code == 'LO')`. Sums all LO inputs; avoids `inputs.LO` last-wins limitation. Updated in testing DB and in `setup_loan_rules.py` (idempotent). |
| Report multiple loans | `liquidacion_breakdown_report.py`: removed `limit=1`, shows all active liquidación loan names, sums total loan amount. |

---

## HR Analyses

### 2026-05-01 - Decreto Ingreso Mínimo Integral $240 — Análisis de Impacto Salarial

**Ad-hoc analysis — no module change. PDF ejecutivo generado para equipo de Finanzas.**

| Item | Detalle |
|---|---|
| **Decreto** | Ingreso Mínimo Integral sube a $240 USD efectivo 30/04/2026 (retroactivo) |
| **Composición** | Bono de Guerra Económica $199.73 + Cestaticket $40.00 + Salario base $0.27 |
| **Anterior** | ~$190 USD (+26.3% de incremento) |
| **Empleados analizados** | 44 (excluyendo Alberto Perdomo, María Jiménez, Gustavo Perdomo) |
| **No conformes** | LUIS RODRIGUEZ ($191.37, gap +$48.63) · NIDYA LIRA ($228.67, gap +$11.33) |
| **Ajuste mensual requerido** | $59.96 (anualizado: $719.52) |
| **Banda de riesgo $240–$300** | 9 empleados — MARIELA PRADO y ZARETH FARIAS con solo $10.03 de margen |
| **Cestaticket** | Valor actual $40.00 coincide exactamente con el decreto — sin cambio requerido |
| **Acción** | Incrementar `ueipab_bonus_v2`: LUIS RODRIGUEZ $55.69→$104.32 · NIDYA LIRA $83.44→$94.77 |
| **PDF** | `/home/ftpuser/odoo-dev/Analisis_Impacto_Salarial_Mayo2026.pdf` (2 páginas) |
| **Docs** | [SALARIO_MINIMO_DECRETO_MAYO2026.md](SALARIO_MINIMO_DECRETO_MAYO2026.md) |

---

## Production Deployments

### 2026-05-05 — Backdated loan JE date fix (ueipab_payroll_enhancements v1.66.5)

**Deployed to production DB_UEIPAB.**

| Item | Details |
|------|---------|
| **Module version** | 17.0.1.66.5 (upgraded from 17.0.1.66.4) |
| **Fix** | `_create_advance_journal_entry()` now uses `today` when loan date is in a past month |
| **Trigger** | HEYDI RON's second loan (LO/0004) — date 2026-03-02 rejected by PAY1 sequence at 2026/04 |
| **Workaround applied** | HR changed loan date to 2026-05-01 before approving (manual fix, still valid) |

---

### 2026-05-05 — HR Loan System (ueipab_payroll_enhancements v1.66.4)

**Deployed to production DB_UEIPAB.**

| Item | Details |
|------|---------|
| **Module version** | 17.0.1.66.4 (upgraded from 17.0.1.65.0) |
| **ohrms_loan** | Already installed (17.0.1.0.0) — no change |
| **ohrms_loan_accounting** | Already installed (17.0.1.0.0) — no change |
| **Salary rules updated** | `VE_LOAN_DED_V2` id=38, `LIQUID_LOAN_DED_V2` id=39 — formula updated to multi-loan sum via `setup_loan_rules.py` |
| **Templates patched** | id=37 (Payslip Email), id=50 (Adelanto Prestaciones) — loan block inserted; id=52 (Adelanto Salario) already existed. Note: initial deploy had loan block outside HTML — corrected 2026-05-06 via `sync_lo_to_production.py`. |
| **PAY1 pre-check** | 0 `LOAN/` contamination entries — clean |
| **DB backup** | `/home/vision/backups/DB_UEIPAB_before_v1.66.4_20260504_2236.sql.gz` (18MB) |
| **Features deployed** | Multiple loans per employee, batch cancel fix, Option B, `action_payslip_cancel()` with JE handling |

---

### 2026-04-22 - Relación de Liquidación PDF Title Selector (ueipab_payroll_enhancements v1.62.7)

**Deployed to production DB_UEIPAB. Files: `__manifest__.py`, `models/liquidacion_breakdown_wizard.py`, `models/liquidacion_breakdown_report.py`, `wizard/liquidacion_breakdown_wizard_view.xml`, `reports/liquidacion_breakdown_report.xml`, `reports/report_actions.xml`, `controllers/liquidacion_breakdown_xlsx.py`.**

| Item | Details |
|------|---------|
| **Feature** | New "Título del Documento PDF" radio selector in Relación de Liquidación wizard |
| **Options** | `Relación de Liquidación` (default) / `Adelanto Prestaciones Sociales` |
| **PDF header** | Title, subtitle (`Fecha Liquidación:` / `Fecha Adelanto:`), and declaration text all adapt to selection |
| **Declaration text** | Adelanto mode: "...por concepto de adelanto de prestaciones sociales." |
| **PDF filename** | `Relacion_Liquidacion_{EMPLOYEE}_{YYYYMMDD}.pdf` or `Adelanto_Prestaciones_{EMPLOYEE}_{YYYYMMDD}.pdf` |
| **XLSX filename** | Same naming logic applied to XLSX export |
| **Technical note** | Odoo 17 `print_report_name` only exposes `object`+`time` — no context. When `data=` is passed to `report_action`, docids are not in the URL path so `print_report_name` is never evaluated. Fixed via custom PDF controller (`/liquidacion/breakdown/pdf/<wizard_id>`) mirroring the existing XLSX controller pattern |
| **Version** | `17.0.1.62.7` |

---

### 2026-04-19 - Email Template Sync: Subject + Color Fixes (both envs)

**Synced testing (id=71) and production (id=50) templates to identical state.**

| Fix | Detail |
|---|---|
| Subject | `📋 LIQUIDACIÓN V2 │...` → `📋 ADELANTO PRESTACIONES │...` (production) |
| Red colors | `#c0392b` (×5) + `#7b1a1a` (×1) → navy blue `#2471a3` / `#1a2c5b` (both envs) |
| Legal box bg | `#fdf6f0` (orange tint) → `#f0f4fa` (light blue) (production) |
| Result | Both templates fully navy blue, subject identical, bodies in sync |

---

### 2026-04-18 - Adelanto de Prestaciones Sociales Email Template (ueipab_payroll_enhancements v1.62.2)

**Deployed to production DB_UEIPAB. Template id=50. Files deployed: hr_payslip.py, payslip_acknowledgment.py, __manifest__.py, mail_template_payslip.xml. Body applied via direct SQL (psycopg2). Production Odoo restarted.**

---

## Testing Deployments

### 2026-05-04 - HR Loan Production Deployment Scripts Prepared

| Item | Details |
|---|---|
| **`setup_loan_rules.py`** | Idempotent Odoo shell script — creates `VE_LOAN_DED_V2` + `LIQUID_LOAN_DED_V2`, links to structures, creates LO input types, patches `VE_TOTAL_DED_V2` and `LIQUID_NET_V2` formulas |
| **`deploy_loan_templates_prod.py`** | Standalone psycopg2 script — creates "Adelanto de Salario – Notificación" template (new), patches Payslip Email id=37 and Adelanto Prestaciones id=50 with loan blocks |
| **Production IDs confirmed** | PAY1 journal=170, acc_receivable=890, acc_banco=876, acc_prestaciones=1017, Payslip Email tpl=37, Adelanto Prestaciones tpl=50 |
| **PAY1 clean** | No `LOAN/` contamination entries confirmed in production |

---

### 2026-05-04 - HR Loan Bug Fixes (ueipab_payroll_enhancements v1.65.0)

| Item | Details |
|---|---|
| **`total_net_amount` fix** | `_compute_total_net_amount` on `hr.payslip.run` now includes `LIQUID_NET_V2` — liquidation-only batches were showing Bs. 0 as total net |
| **Relación de Liquidación sign fix** | Loan deduction `amount_formatted` was using `abs()` causing the deduction to display as positive, inconsistent with other deductions in the report |
| **Known issue documented** | Creating `LIQUID_VE_V2` payslips via batch does not auto-populate LO input (struct_id is taken from contract, not payslip). Workaround: create liquidation payslips individually |
| **Version** | `17.0.1.65.0` |

---

### 2026-04-19 - Payslip Ack Reminder via Glenda (ueipab_ai_agent v1.31.0)

**New `payslip_ack_reminder` skill + Tab 2 in "Recolección de Datos" wizard.**

| Item | Details |
|------|---------|
| **Skill** | `payslip_ack_reminder` — source model `hr.payslip`, max_turns=4, timeout=48h |
| **Wizard** | Tab 2 "Conformidades Pendientes" in existing wizard — lists `done` payslips with `is_acknowledged=False` |
| **Message** | Greeting with payslip number, period, net VEB, acknowledgment portal URL |
| **Auto-resolve** | CRON every 30 min checks `is_acknowledged` — auto-resolves conversation when True |
| **Stagger CRON** | New `_cron_start_ack_reminders()` — 30 min, respects capacity (max_active=10) |
| **LIQUID_VE_V2** | Greeting uses "adelanto de prestaciones sociales" instead of "comprobante de pago" |
| **Duplicate guard** | Employees with existing active WA reminder shown as muted, deselected by default |
| **New model** | `hr.data.collection.create.ack.line` (TransientModel for wizard Tab 2) |
| **Module version** | 17.0.1.31.0 |
| **Docs** | [PAYSLIP_ACK_REMINDER_GLENDA.md](PAYSLIP_ACK_REMINDER_GLENDA.md) |

**Files changed:** `skills/payslip_ack_reminder.py` (new), `wizard/create_collection_wizard.py`, `wizard/create_collection_wizard_view.xml`, `skills/__init__.py`, `data/skills_data.xml`, `data/cron.xml`, `models/ai_agent_conversation.py`, `security/ir.model.access.csv`, `__manifest__.py`

---

### 2026-04-18 - Adelanto de Prestaciones Sociales Email Template (ueipab_payroll_enhancements v1.62.2)

**New email template for LIQUID_VE_V2 payslips with legal agreement body and structure-aware ack landing page.**

| Item | Details |
|------|---------|
| **Template name** | `Adelanto de Prestaciones Sociales` (DB id=71 testing) |
| **Structure** | `LIQUID_VE_V2` only |
| **Color scheme** | Navy blue gradient (`#1a2c5b → #2471a3`) — distinct from red liquidación template |
| **Body** | Four legal clauses (PRIMERO–CUARTO) with company/employee data, period dates, net VEB amount, signing date |
| **Amounts** | All in VEB via `get_liq_veb()` / `get_liq_net_veb()` helpers |
| **Key fields** | `date_from/date_to` for period, `ueipab_original_hire_date` for hire date, `get_next_period_start()` for day after period end |
| **Signing date** | Uses email send date (today) via `get_today_day/month_es/year()` helpers — not `date_to` |
| **Hardcoded rep** | `GUSTAVO PERDOMO`, `Representante Legal`, `V15128008` |
| **Ack button** | "Enviar conformidad digital para recibir mi pago" |
| **PDF attachment** | Disabled during body refinement — re-enable via `action_report_liquidacion_breakdown` ref in XML |
| **Landing page** | Branches on `struct_id.code == 'LIQUID_VE_V2'` — adelanto-specific title/subtitle/button; all other structures see generic text |
| **New helpers in hr_payslip.py** | `get_liq_veb(code)`, `get_liq_net_veb()`, `get_next_period_start()`, `get_original_hire_date_fmt()`, `get_today_day()`, `get_today_month_es()`, `get_today_year()` |
| **Business flow** | Batch stays DRAFT → email sent → employee reviews and acknowledges → HR confirms receipt → batch confirmed/closed |
| **Template body** | Managed via direct SQL (`jsonb_set`) — ORM `Html` sanitizer strips custom method calls |
| **Version** | `17.0.1.62.2` |

### 2026-04-18 - Farewell Message Fix After Resolved Conversation (ueipab_ai_agent v1.30.2, testing only)

**Fixed: post-handoff farewell messages ("Gracias", "saludos") silently dropped.**

| Item | Details |
|------|---------|
| **Root cause** | `_get_or_create_general_inquiry_conversation()` 24h cooldown blocked ALL terminal states equally. When a customer sent a farewell after a resolved handoff, the guard found the resolved conv within 24h and returned `None` — message dropped, no reply |
| **Example** | Gustavo received 5-student quotation at 00:34, replied "Gracias saludos" shortly after → Glenda never acknowledged it |
| **Fix** | Cooldown now distinguishes terminal states: `timeout`/`failed` → still blocked (unresponsive or broken); `resolved` → **allow new conversation** so Glenda can give a brief, warm acknowledgment |
| **Behavior after fix** | Customer who says "Gracias" after a handoff gets a natural closing reply from Glenda instead of silence |
| **Version** | `17.0.1.30.2` |
| **Deployed** | Testing 2026-04-18 |

### 2026-04-18 - Annual Extras in Quotation (ueipab_ai_agent v1.30.1, testing only)

**Extended quotation engine to include one-time annual costs and full first-month total.**

| Item | Details |
|------|---------|
| **Annual one-time costs** | Seguro escolar $15 + Enciclopedia de Inglés $30 + Olimpiadas Recreativas $10 = **$55/alumno** (no sibling discount, full price per student) |
| **Bachillerato extra** | +$36 Enciclopedia digital bachillerato per bachillerato-level student. Glenda asks if any student is in bachillerato before quoting |
| **Optional costs excluded** | Competencia Kurios ($10) and Competencia MOA inglés ($25) are conditional (only if selected by school) — NOT included in standard quote |
| **Quote format** | 4 sections: (1) mensualidad per child with sibling discount, (2) inscripción total, (3) costos anuales total, (4) TOTAL PRIMER MES = inscripción + extras + mensualidad (regular and pronto pago) |
| **Example 2 students** | Primer mes regular $1.154,70 / con pronto pago $1.109,23 |
| **Version** | `17.0.1.30.1` |
| **Deployed** | Testing 2026-04-18 |

### 2026-04-18 - Multi-Student Quotation Engine (ueipab_ai_agent v1.30.0, testing only)

**Glenda can now generate full enrollment quotations for families with multiple children.**

| Item | Details |
|------|---------|
| **Sibling discounts** | 1st child: full price · 2nd: 5% off mensualidad · 3rd: 6% · 4th+: 7%. Inscripción at full price per child. Discounts stack with pronto pago (applied on already-discounted mensualidad) |
| **Pre-calculated table** | Per-child amounts embedded in knowledge: 1st $264,48 (PP $241,16) · 2nd $251,26 (PP $229,11) · 3rd $248,61 (PP $226,69) · 4th+ $245,97 (PP $224,28) — **superseded by v17.0.1.33.0** |
| **Quote flow** | If student count not stated, Glenda asks first. Presents per-child breakdown + total mensual (regular and pronto pago) + total inscripción |
| **Handoff** | After quote, hands off to `billing` with structured summary: N alumnos, total mensualidad, total PP, total inscripción |
| **Email subject** | Quotation emails automatically get subject `[Glenda] Cotización solicitada` (detected from summary keyword "cotización") |
| **Version** | `17.0.1.30.0` |
| **Deployed** | Testing 2026-04-18 |

### 2026-04-17 - Forecast Tarifas 2026-2027 Sep (ueipab_ai_agent v1.29.9, testing only)

**Added upcoming September 2026 projected pricing to Glenda's institutional knowledge.**

| Item | Details |
|------|---------|
| **New knowledge** | Proyected rates effective September 1, 2026 (start of 2026-2027 school year): Inscripción $264,48 · Mensualidad $264,48 · Pronto pago $241,16 (8,816% discount, first 10 days of month) — **superseded by official preliminary rates in v17.0.1.33.0** |
| **Current rates retained** | $197,38 inscripción / mensualidad, pronto pago $162,39 — labeled "vigente hasta agosto 2026" |
| **Glenda behavior** | Answers correctly for current OR upcoming rates depending on what the customer asks. If asked whether price will increase: confirms Sep 1 adjustment without alarming. Recommends pagos@ to confirm for specific cases |
| **Version** | `17.0.1.29.9` |
| **Deployed** | Testing 2026-04-17 |

### 2026-04-17 - General Inquiry Timeout Fix (ueipab_ai_agent v1.29.8, testing only)

**Fixed three bugs that caused `general_inquiry` conversations to stay permanently stuck in `waiting` state.**

| Item | Details |
|------|---------|
| **Bug 1 — Missing `get_reminder_message`** | `general_inquiry` skill never implemented this method. `_send_reminder()` called it unconditionally → `AttributeError` every time the cron tried to send a 24h follow-up. Crash prevented `reminder_count` from ever incrementing, so `action_timeout()` was never reached. Conversations stuck forever |
| **Root cause confirmed** | Cron logged `ERROR: Call from cron AI Agent: Check Conversation Timeouts ... failed` every hour since a general_inquiry conv entered waiting state. Conv 100 stayed `waiting` from 2026-04-03 to 2026-04-17 (14 days) instead of timing out after 72h |
| **Fix 1** | Added `get_reminder_message()` to `GeneralInquirySkill`. Reminder 1: gentle follow-up ("¿Pude ayudarte?"). Reminder 2: friendly closing ("Si necesitas información en otro momento...") |
| **Bug 2 — No error isolation in timeout cron** | `_cron_check_timeouts` had no `try/except` per conversation. One bad conversation crashed the ENTIRE cron run for all skills, leaving other waiting conversations also unprocessed |
| **Fix 2** | Wrapped each conversation's `_send_reminder()` / `action_timeout()` call in `try/except` with savepoint. One failure now logs an error and continues to the next conversation |
| **Bug 3 — max_turns=10 too low for general_inquiry** | Conversations can accumulate turns across unrelated sessions if timeout never fires. 10 turns exhausted by a mix of old (Apr 3) and new (Apr 17) interactions. The PDVSA question (turn 10) got no reply |
| **Fix 3** | `max_turns` raised from 10 → 25 for `general_inquiry` skill. Updated directly in DB (record has `noupdate="1"`) |
| **Cascade effect** | Conv 100 (14-day-old stale conv) appended Apr 17 enrollment inquiry to itself. PDVSA question at turn 10 got no reply. Customer went unanswered |
| **Version** | `17.0.1.29.8` |
| **Deployed** | Testing 2026-04-17 |

### 2026-04-17 - Batch Date Logic Validator (v1.61.0, testing only)

**New feature: automatic date consistency check on payslip batches.**

| Item | Details |
|------|---------|
| **Problem** | Batches could be created/saved with wrong dates (e.g. MARZO31-7 had April dates) with no warning until the error was noticed manually |
| **Feature** | New "Check Date Logic" button on batch form runs 4 checks: (1) overlap with existing confirmed payslips, (2) gap from expected next period, (3) quincena alignment for V2 structures, (4) batch name vs date month mismatch |
| **UX** | Issues shown in modal wizard with severity (Blocker/Warning/Info). User can fix dates or acknowledge and proceed |
| **Auto-trigger** | Check runs automatically after "Sync Dates to Payslips" — shows wizard instead of success notification if issues found |
| **Override** | `date_check_acknowledged` flag on batch. Resets automatically whenever batch dates change |
| **New files** | `wizard/payslip_batch_date_check_wizard.py`, `wizard/payslip_batch_date_check_wizard_view.xml` |
| **Version** | `17.0.1.61.0` |
| **Deployed** | Testing 2026-04-17 |

### 2026-04-17 - Glenda 2026-2027 Knowledge Update + PDVSA Policy (ueipab_ai_agent v1.29.7, testing only)

**Updated `general_inquiry` skill with 2026-2027 enrollment costs and new PDVSA/Petropiar policy.**

| Item | Details |
|------|---------|
| **Year updated** | `_INSTITUTIONAL_KNOWLEDGE` now reflects año escolar 2026-2027 |
| **New costs** | Inscripción $197,38 · Seguro escolar $15 (was $10) · Enciclopedia de Inglés $30 (replaces Guía de inglés $15) · Olimpiadas Recreativas $10 · Enciclopedia digital bachillerato $36 · Competencia Kurios $10 (si seleccionado) · Competencia MOA inglés $25 (si seleccionado) |
| **Logística** | Encuentros Regionales/Nacionales: traslados a cargo de los padres |
| **PDVSA policy** | New "POLÍTICA PDVSA / PETROPIAR 2026-2027" section: benefit of 35% credit advance **discontinued**. New prospects: 100% upfront at BCV rate. Existing enrolled families expressing distress: empathetic handling + urgent retention alert |
| **Scenario A** | New PDVSA prospect → inform discontinuation, billing handoff |
| **Scenario B** | Existing 2025-2026 family expressing hardship → empathetic calm, invite Director meeting, urgent `pdvsa_retention` route email to `pagos@ueipab.edu.ve` with ⚠️ subject |
| **New route** | `pdvsa_retention` added to valid handoff routes. On-resolve sends urgent alert: `[URGENTE - Glenda] Familia PDVSA — Riesgo de no renovación — {name}` |
| **Version** | `17.0.1.29.7` |
| **Deployed** | Testing 2026-04-17 |

### 2026-04-17 - Credit Guard False-Positive Fix (ueipab_ai_agent v1.29.6, testing only)

**Eliminated false-positive credit alert emails caused by transient MassivaMóvil API timeouts.**

| Item | Details |
|------|---------|
| **Problem** | Credit Guard fail-safe treated any API error (including 15s read timeout) as depleted credits, immediately activating the kill switch and sending an alert email — even when credits were fine |
| **Root Cause** | `_cron_check_credits()` had no retry or confirmation logic — one failure = immediate alert |
| **Fix** | Added consecutive-failure counter (`ai_agent.credits_fail_count`). Kill switch only activates after N consecutive failures (configurable via `ai_agent.credits_fail_threshold`, default 2). Any clean check resets the counter to 0 |
| **Alert email** | Now includes confirmation count: "Confirmado tras 2 chequeos consecutivos fallidos (umbral: 2). No es una alerta transitoria." |
| **New params** | `ai_agent.credits_fail_threshold` (default `2`), `ai_agent.credits_fail_count` (internal counter) |
| **Version** | `17.0.1.29.6` |
| **Deployed** | Testing 2026-04-17 |

---

## Production Deployments

### 2026-04-08 - LIQUID_ANTIGUEDAD_V2 Bug Fix (DB-only, both envs)

**Fixed incorrect antigüedad calculation for terminated+rehired employees.**

| Item | Details |
|------|---------|
| **Problem** | Employees with `previous_liquidation_date < contract.date_start` (terminated + rehired with a gap) had their antigüedad computed from `original_hire_date` without deducting the prior paid period — effectively paying decades of full seniority instead of only the current contract period |
| **Root Cause** | Validation `previous_liquidation >= contract.date_start` was too strict. For rehired employees, the prior liquidation naturally falls before the new contract start, so the check always failed and fell back to full history |
| **Fix** | Changed to `previous_liquidation > original_hire AND net_months > 0` — correctly computes net antigüedad regardless of rehire gap |
| **Affected rule** | `LIQUID_ANTIGUEDAD_V2` — prod id=29, test id=59 |
| **Script updated** | `scripts/create_production_salary_structures.py` |
| **Deployed** | Testing 2026-04-08, Production 2026-04-08 (direct DB update, no module upgrade needed) |
| **Impact audit** | Only 1 confirmed V2 liquidation in production (SLIP/313 STEFANY ROMERO) — not affected. Open issue: SLIP/447 JOSEFINA RODRIGUEZ (draft) — see [resolution doc](JOSEFINA_RODRIGUEZ_OVERPAYMENT_RESOLUTION.md) |

### 2026-04-14 - Disbursement Report V1 Fallback Fix (v1.61.5)

**Fixed crash when generating Payroll Disbursement Report for payslips with missing or no-V2 contract.**

| Item | Details |
|------|---------|
| **Problem** | `AttributeError: 'hr.contract' object has no attribute 'ueipab_deduction_base'` when downloading the report |
| **Root Cause** | `ueipab_deduction_base` was intentionally removed from `ueipab_hr_contract` v2.0.0 (2025-11-24, commit `e953099`) but two V1 fallback references were left in `payroll_disbursement_wizard.py` and `payroll_disbursement_detail_report.xml`. Triggered by MAIRELSY MOTTA's payslip having no contract (expired contract not renewed in time) |
| **Fix** | Replaced V1 `else` branch in both files with safe fallback: `salary = wage`, `bonus = 0.0`. Only fires for edge cases (missing contract or `ueipab_salary_v2` not set) — all V2 employees unaffected |
| **Files** | `models/payroll_disbursement_wizard.py`, `reports/payroll_disbursement_detail_report.xml` |
| **Version** | `17.0.1.61.5` |
| **Deployed** | Testing + Production 2026-04-14 |

### 2026-04-08 - Ack Reminder Email CC Fix (v1.61.4)

**Added CC to `recursoshumanos@ueipab.edu.ve` on acknowledgment reminder emails.**

| Item | Details |
|------|---------|
| **Problem** | Reminder emails sent to employees had no CC — HR had no visibility |
| **Root Cause** | `email_cc` field missing from `email_template_ack_reminder.xml` |
| **Fix** | Added `email_cc` field + changed template to `noupdate="0"` so upgrades apply it. Reset `ir_model_data.noupdate=false` in testing DB before re-upgrade |
| **File** | `data/email_template_ack_reminder.xml` |
| **Version** | `17.0.1.61.4` |
| **Deployed** | Testing 2026-04-08 — Production pending |

### 2026-04-08 - Ack Reminder Wizard Layout Fix (v1.61.3)

**Fixed "📊 Resumen de Resultados" step not fully expanding in the reminder wizard.**

| Item | Details |
|------|---------|
| **Problem** | Step 2 (done state) results panel was constrained — not full width |
| **Root Cause** | `<notebook>` for results was wrapped inside a `<group>` element, which applies Odoo's 2-column constrained layout. Step 1 notebook was placed directly in the form (full width), but step 2 was not |
| **Fix** | Removed `<group>` wrapper, applied `invisible="state != 'done'"` directly on `<notebook>` — same pattern as step 1 |
| **File** | `wizard/ack_reminder_wizard_view.xml` |
| **Version** | `17.0.1.61.3` |
| **Deployed** | Testing + Production 2026-04-08 |

### 2026-04-07 - Advance Payment Email Template Fix (Testing + Production, DB-only)

**Fixed "Payslip Email - Advance Payment - Employee Delivery" showing half the correct advance amount.**

| Item | Details |
|------|---------|
| **Problem** | Email showed `advance_amt = net_wage × (advance_pct/100)` — double-reducing an amount already reduced by salary rules. E.g. GUSTAVO PERDOMO (50% advance, net=$88.46): email showed Bs. 20,988.63 instead of Bs. 41,977.26 |
| **Root Cause (template)** | `advance_amt` t-set used old formula. `full_salary` t-set was missing so the "neto total" reference line also showed wrong value |
| **Root Cause (why prior fix failed)** | In Odoo 17, `body_html` is stored as JSONB `{"en_US":"...", "es_VE":"..."}`. Prior fix ran with `lang=False` which updates a neutral fallback Python reads — but does NOT update the `en_US` key used by the UI at send time. The email was rendered using the unfixed `en_US` key |
| **Fix** | Explicitly iterate `['en_US', 'es_VE']` with `tpl.with_context(lang=lang)` to write each JSONB key directly. Updated `fix_advance_payment_template.py` accordingly |
| **Testing** | Template id=65, both `en_US` and `es_VE` keys fixed. Verified: Bs. 41,977.26 ✓ |
| **Production** | Template id=44, `en_US` key fixed (was missed by prior SQL fix). `es_VE` was already correct. Verified via render test ✓ |
| **Correct formula** | `advance_amt = net_wage` (already the advance), `full_salary = net_wage × (100/advance_pct)` for reference line |

---

### 2026-04-07 - PAY1 Sequence Conflict — Permanent Auto-fix (`ueipab_payroll_enhancements` v1.61.2)

**Implemented two-layer permanent prevention of PAY1 sequence/date mismatch errors.**

| Item | Details |
|------|---------|
| **Problem** | When the PAY1 journal sequence advances into a new month (e.g. April), payslips with `date_to` still in the prior month (e.g. March 31) fail validation: `"The Date (03/31/2026) doesn't match the sequence number PAY1/2026/04/xxxx"` |
| **Layer 1 — Early Warning** | `_collect_date_issues()` (Check 5) detects the sequence/date mismatch before the user clicks Validate. The date check wizard displays an **"Auto-fix Accounting Dates"** button that sets `slip.date` on all draft payslips to the first day of the sequence month. |
| **Layer 2 — Safety Net** | `action_validate_payslips()` override auto-detects any remaining conflict just before confirming payslips and silently sets `slip.date` if needed. Logs the adjustment via Python logger. No popup shown. |
| **Detection method** | Queries `account_move` for the latest posted entry in the payslip journal; extracts year/month from name pattern `PAY1/YYYY/MM/NNNN`. Compares against batch `date_end`. |
| **Files** | `models/hr_payslip_run.py` (+3 methods), `wizard/payslip_batch_date_check_wizard.py` (+`seq_fix_date` field, +`action_fix_accounting_dates`), `wizard/payslip_batch_date_check_wizard_view.xml` (info banner + button) |
| **Version** | `17.0.1.61.2` |

---

### 2026-04-07 - MARZO31-G3 Batch Validation Fix — PAY1 Sequence/Date Mismatch (Production operational fix)

**Fixed validation error preventing confirmation of DAVID HERNANDEZ payslip in MARZO31-G3 (batch id=43).**

| Item | Details |
|------|---------|
| **Error** | `"The Date (03/31/2026) doesn't match the sequence number PAY1/2026/04/0025"` |
| **Root Cause** | Same pattern as MARZO31-15 (2026-04-06): PAY1 sequence locked in April 2026, payslip `date=NULL` falls back to `date_to=2026-03-31` → sequence mismatch |
| **Fix** | Permanent fix (v1.61.2) handles this automatically at validate time |

---

### 2026-04-06 - MARZO31-15 Batch Validation Fix — PAY1 Sequence/Date Mismatch (Production operational fix)

**Fixed validation error preventing confirmation of payslip batch MARZO31-15 (id=42, 19 employees).**

| Item | Details |
|------|---------|
| **Error** | `"The Date (03/31/2026) doesn't match the sequence number of the related Journal Entry (PAY1/2026/04/0006)"` |
| **Root Cause** | PAY1 journal sequence had already advanced to April (`04`) because a prior April-period payslip (ISMARY ARCILA `PAY1/2026/04/0001`) was posted with a March 31 accounting date, pushing the sequence counter into April. All subsequent entries get `PAY1/2026/04/*` sequence numbers. Odoo 17 validates that the entry date month matches the sequence month — March 31 vs April sequence = rejected. |
| **Fix** | Set `date` (accounting date) field to `2026-04-01` on all 19 draft payslips via Odoo shell. `hr_payroll_account_community` uses `slip.date or slip.date_to` for the journal entry date — with `date=NULL` it fell back to `date_to` (2026-03-31). |
| **Action** | `env['hr.payslip'].browse([batch_42_slip_ids]).write({'date': date(2026, 4, 1)})` |

**Result:** 19 journal entries posted as `PAY1/2026/04/0006` → `PAY1/2026/04/0024`, all dated 2026-04-01. Batch closed successfully.

**Accounting Impact:**

| Account | Debit | Credit |
|---------|-------|--------|
| `5.1.01.10.001` Nómina (Docentes) | 3,013.85 | 29.20 |
| `1.1.01.02.001` Banco Venezuela | 29.20 | 3,013.85 |
| **Net payroll expense / bank outflow** | **2,984.65** | **2,984.65** |

**Period note:** These 19 entries (payroll period 2026-03-16→31) post to **April's accounting period** (date=2026-04-01), not March. All other MARZO31 batches posted on 2026-03-31. Finance team informed: March P&L understated by USD 2,984.65; April overstated by same amount. No system correction needed unless March books require restatement.

**Root cause pattern — how to avoid in future:**
> When posting April-period payslips with a March 31 accounting date, Odoo's PAY1 sequence advances to April. Any remaining March-dated payslips then fail with this mismatch. Solution: always post out-of-period payslips with an accounting date that matches the current sequence month, or confirm all March payslips before confirming any April-period ones.

---

### 2026-04-06 - Batch Email Wizard Confirm Step Filter Fix (`ueipab_payroll_enhancements` view patch)

**Fixed confirm step showing all employees instead of only selected ones.**

| Item | Details |
|------|---------|
| **Problem** | Step 2 "Selected Employees" section displayed all employees regardless of selection state |
| **Root Cause** | `domain` on One2many field in Odoo 17 form views does not filter displayed records — only restricts new record creation |
| **Fix** | Added computed `Many2many` field `selected_ids` filtered server-side; confirm block uses `selected_ids` instead of `selection_ids` with broken domain |
| **Files** | `wizard/batch_email_wizard.py` (+computed field), `wizard/batch_email_wizard_view.xml` (field swap) |
| **Deployed** | Both testing and production |

---

### 2026-04-06 - Batch Email Wizard `boolean_toggle` Fix (`ueipab_payroll_enhancements` v60.1 view patch)

**Fixed `RPC_ERROR` when unchecking individual employees in the Send Emails wizard.**

| Item | Details |
|------|---------|
| **Problem** | Clicking any individual checkbox in the employee selection list inside the "Send Emails (with Progress)" wizard threw a Validation Error: `wizard_id` missing on `hr.payslip.batch.email.selection` |
| **Root Cause** | `boolean_toggle` widget fires an immediate `webSave` on the child record, sending only the changed field — ORM rejected because `wizard_id` (`required=True`) was absent from the auto-save payload |
| **Fix** | Removed `widget="boolean_toggle"` from `selected` field in selection tree; standard checkbox saves on row blur / form submit, which includes full context |
| **File** | `wizard/batch_email_wizard_view.xml` — 1-line change |
| **Deployed** | View-only patch applied directly; production manifest version unchanged (60.1) |

**Workaround that worked before fix:** Use "Select All" / "Deselect All" / "Select With Email Only" bulk buttons.

---

### 2026-02-08 - Contact Data Sync Fix (Bounce Log + Partner Emails)

**Fixed cross-reference inconsistencies between Odoo, Freescout bounces, Customers sheet, and Akdemia.**

**Category A — 7 not-found bounce logs linked to correct partners:**
- Linked bounce logs #30, #32, #33, #46, #54, #56, #58 to their matching partners
- Updated `action_tier` from `not_found` to `flag` (temporary) or `clean` (permanent)
- Appended bounced emails to partner email fields (multi-email `;` pattern)
- Contacts: DAIRILYS CHAURAN, ANTONIO MARTINEZ, MARIA APONTE, DOALBERT NUÑEZ, FRANCIA LORETO, CASTO GONZALEZ, GLORIA MILLAN

**Category B — MIGUEL MARIN #3663:**
- Added `susanaquijada102@gmail.com` as secondary email in Odoo (mother's email from Akdemia)
- Updated Customers Google Sheet row 128 to include both emails

**Category C — SORELIS MAITA #3669:**
- Flagged for manual mobile lookup (no phone/mobile in any data source)
- Glenda cannot WhatsApp without mobile number

**Category D — Perdomo duplicates cleanup:**
- Deleted 3 irrelevant bounce logs (#27, #28, #29) — staff, not Representante
- Archived 2 duplicate partners (#3612 Alberto J Perdomo, #3676 Gustavo Perdomo)
- Added `perdomo.gustavo@gmail.com` as secondary email on real user #7

**Category E — 8 orphan bounces:** No action (no match in any data source)

**Verification:** 37 bounce logs total, 29 linked to partners, 8 orphans as expected.

**Scripts:** `scripts/contact_data_sync_fix.py`, `scripts/contact_sync_comparison.py`

---

### 2026-01-10 - LIQUID_VE_V2 Accounting Configuration Fix

**Fixed payslip confirmation error for Liquidación Venezolana V2:**

| Item | Details |
|------|---------|
| **Problem** | SLIP/313 (STEFANY ROMERO) could not be confirmed: "choose Debit and Credit account for at least one salary rule" |
| **Root Cause** | `LIQUID_VE_V2` structure had no accounting accounts configured on any salary rules |
| **Solution** | Configured `LIQUID_NET_V2` rule with debit/credit accounts |
| **Affected Structure** | LIQUID_VE_V2 (Liquidación Venezolana V2) |

**Accounts Configured:**

| Rule | Debit Account | Credit Account |
|------|---------------|----------------|
| LIQUID_NET_V2 | 5.1.01.10.010 (Prestaciones sociales) | 2.1.01.10.005 (Provisión Prestaciones Sociales) |

**Environment Comparison:**
- **Testing:** All 14 rules have accounting configured (more comprehensive)
- **Production:** Only NET rule configured (minimum required - follows design pattern)

**Note:** Per Odoo payroll accounting design, only NET/deduction rules need accounting. Earnings rules should NOT post to accounting.

---

### 2026-01-08 - Salary Rules & Email Template Fix for Remainder Batches

**Fixed salary rules not applying percentage to remainder batches:**

| Item | Details |
|------|---------|
| **Problem** | Remainder batches (is_remainder_batch=True) computed at 100% instead of 50% |
| **Root Cause** | Salary rules only checked `is_advance_payment`, not `is_remainder_batch` |
| **Solution** | Updated condition to check both flags |
| **Rules Fixed** | VE_SALARY_V2, VE_EXTRABONUS_V2, VE_BONUS_V2 |

**Salary Rule Fix:**
```python
# Before (only advance batches got percentage)
if payslip.payslip_run_id and payslip.payslip_run_id.is_advance_payment:

# After (both advance AND remainder batches get percentage)
if payslip.payslip_run_id and (payslip.payslip_run_id.is_advance_payment or payslip.payslip_run_id.is_remainder_batch):
```

**Email Template Updated (ID 45 prod / ID 66 testing):**
- Removed percentage multiplication (salary rules now handle it)
- Uses `net_wage` directly: `<t t-set="rest_usd" t-value="object.net_wage or 0.0"/>`
- Removed "Tasa de Cambio Actual" section

**Synced:** Both production and testing environments updated

### 2026-01-07 - Payslip Batch Delete Fix (NewId Sorting Error)

**Fixed TypeError when deleting payslips from batch UI:**

| Item | Details |
|------|---------|
| **Problem** | Deleting payslip from batch view caused `TypeError: '<' not supported between instances of 'NewId' and 'NewId'` |
| **Root Cause** | `_compute_exchange_rate` sorted payslips by `s.id`, but during onchange operations unsaved records have `NewId` objects that can't be compared |
| **Solution** | Filter to only saved records (with integer IDs) before sorting, with fallback for unsaved slips |
| **File Changed** | `hr_payslip_run.py` line 180 |
| **Version** | 17.0.1.51.2 |

**Fix Applied:**
```python
# Before (broken)
first_slip = batch.slip_ids.sorted(lambda s: s.id)[0]

# After (fixed)
real_slips = batch.slip_ids.filtered(lambda s: isinstance(s.id, int))
if real_slips:
    first_slip = real_slips.sorted(lambda s: s.id)[0]
else:
    first_slip = batch.slip_ids[0]  # Fallback for unsaved slips
```

### 2025-11-27 - Password Reset URL Fix (dbfilter)

**Fixed invitation/password reset email links returning 404:**

| Item | Details |
|------|---------|
| **Problem** | Users clicking password reset links got "Not Found" error |
| **Root Cause** | `dbfilter = ^(DB_UEIPAB\|testing)$` allowed multiple DBs, preventing auto-session |
| **Solution** | Changed to `dbfilter = ^DB_UEIPAB$` (single database) |
| **File Changed** | `/etc/odoo/odoo.conf` in `ueipab17` container |
| **Impact** | 30 pending invitation tokens now work directly |

**Diagnosis:**
- Route `/web/reset_password` uses `auth='public'` + `website=True`
- Without active session, Odoo couldn't determine which database to use
- Single-database filter enables automatic session creation

### 2025-11-27 - Payslip Acknowledgment System + Email Fix

**Payslip Acknowledgment System deployed to production:**

| Change | Details |
|--------|---------|
| ueipab_payroll_enhancements | Upgraded v1.41.0 → v1.43.0 |
| Acknowledgment Fields | access_token, is_acknowledged, acknowledged_date, acknowledged_ip |
| Portal Routes | /payslip/acknowledge/<id>/<token> for employee confirmation |
| Access Tokens | Generated for 49 existing payslips |
| Email Template | "Payslip Compact Report" subject Jinja2 conditional fixed |

**Email Subject Fix:**
- **Old (broken):** `{{ (' │ Lote: ' + object.payslip_run_id.name) if object.payslip_run_id else '' }}`
- **New (working):** `{{' │ Lote: ' + object.payslip_run_id.name if object.payslip_run_id else ''}}`

**Payslip Data Cleanup:**
- Cancelled 5 confirmed payslips (reversed accounting moves)
- Deleted 49 payslips via ORM unlink()
- Deleted 2 test batches
- Reset sequence to 1 (next = SLIP/001)

### 2025-11-26 - SSO Rate Change + Otras Deducciones

| Change | Details |
|--------|---------|
| VE_SSO_DED_V2 | Rate changed from 4.5% → 4% |
| VE_OTHER_DED_V2 | New salary rule created (seq 105) |
| VE_TOTAL_DED_V2 | Updated to include other deductions |
| Contract Field | `ueipab_other_deductions` added |
| Email Template | "Payslip Email - Employee Delivery" created |
| Compact Report | SSO label updated to 4% |

### 2025-11-25 - Production Migration Complete

- All 44 production contracts assigned to "Salarios Venezuela UEIPAB V2"
- ARI rates compared: 43/44 match, 1 discrepancy (ARCIDES ARZOLA)
- V1 fields removed, V2 fields active
- 47 users had excessive permissions removed

---

## Feature Version History

### Payslip Acknowledgment System (v1.42.0-v1.43.0)

**Purpose:** Token-based portal for employees to acknowledge payslip receipt.

**Fields Added:**
- `access_token` - UUID for secure portal access
- `is_acknowledged` - True when employee confirms
- `acknowledged_date` - When confirmation occurred
- `acknowledged_ip` - IP address of confirmation
- `acknowledged_user_agent` - Browser/device info

**Routes:**
- GET `/payslip/acknowledge/<id>/<token>` - Landing page
- POST `/payslip/acknowledge/<id>/<token>/confirm` - Process confirmation

**Session Requirement:** Routes use `auth='public'` which requires database session.

### Batch Email Template Selector (v1.33.0-v1.34.0)

**v1.34.0 (2025-11-24):**
- Fixed `total_net_amount` computed field to include `VE_NET_V2` code
- Changed `exchange_rate` to computed field auto-populated from VEB rates

**v1.33.0 (2025-11-24):**
- Added template selector with 3 templates
- Fixed "Payslip Compact Report" QWeb syntax
- Fixed "Aguinaldos Email" with Christmas theme

### Comprobante de Pago Compacto (v1.40.0-v1.41.0)

**v1.41.0 (2025-11-26):**
- ARI Deduction now shows actual rate from contract
- Before: `VE_ARI_DED_V2 - ARI Variable %`
- After: `Retención impuestos AR-I X%`

**v1.40.0 (2025-11-25):**
- Added payslip's `exchange_rate_used` as default for VEB display
- 4-priority system: Custom → Rate date → Payslip rate → Latest

### Relación de Liquidación Report (v1.19.0-v1.26.0)

**v1.26.0 (2025-11-21):** Auto-latest rate as default for VEB
**v1.25.4 (2025-11-20):** XLSX layout matches PDF exactly
**v1.25.3 (2025-11-20):** Antigüedad displays for ALL employees
**v1.25.2 (2025-11-19):** XLSX export uses wizard's exchange rate
**v1.24.0 (2025-11-18):** Added payslip number to header
**v1.21.0 (2025-11-18):** Improved interest formula display
**v1.20.0 (2025-11-18):** Accrual-based interest calculation
**v1.19.0-1.19.8 (2025-11-17):** Exchange rate override, formatting, layout

### Acuerdo Finiquito Laboral (v1.18.0-v1.25.1)

**v1.25.1 (2025-11-18):** Fixed rate_date parameter handling
**v1.25.0 (2025-11-18):** Added exchange rate override UI
**v1.23.0 (2025-11-18):** Exchange rate override support
**v1.18.2:** DOCX export with python-docx
**v1.18.0:** Initial release with PDF export

### Prestaciones Interest Report (v1.20.0-v1.22.0)

**v1.22.0 (2025-11-18):** Exchange rate consistency fix using `company_rate`
**v1.20.0 (2025-11-18):** Accrual-based interest calculation

### Payslip Email Delivery (hr_payslip_monthly_report v17.0.1.2)

**v17.0.1.2 (2025-11-22):**
- Fixed "Send Mail" button disappearing after cancel
- Added "Reset Send Status" button for recovery

---

## Bug Fixes & Critical Fixes

### V2 Antigüedad Validation Fix (2025-11-21)

**Bug:** Invalid `previous_liquidation_date` causing overpayments
- Dates before contract start created negative "already paid" periods
- Example: SLIP/853 paid $195.08 instead of $100.40 (94% error!)

**Fix:** Added validation `if previous_liquidation and previous_liquidation >= contract.date_start:`
**Impact:** Prevents 20.7% overpayment on affected liquidations

### V2 Vacation/Bono Fix (2025-11-17)

- Fixed double deduction bug where NET was incorrectly $0.00
- New field: `ueipab_vacation_prepaid_amount` for actual prepaid amounts
- School year: Sep 1 - Aug 31

### INCES Deduction Scope Fix (2025-11-18)

**Observation:** INCES should only apply to Utilidades (profit sharing)
**Fix:** Updated LIQUID_INCES_V2 formula to exclude Vacaciones and Bono Vacacional

### Container Issues (2025-11-19)

**Empty Database Pollution:**
- Problem: Database "ueipab" exists but not initialized
- Fix: `DROP DATABASE ueipab;`

**WebSocket Port Mismatch:**
- Problem: Config uses deprecated `longpolling_port = 8078`
- Fix: Update to `gevent_port = 8072`

---

## Technical Learnings

### Accrual-Based Currency Conversion (2025-11-18)

```python
# WRONG - Re-converts total accumulated USD each month
accumulated_usd = 0.0
for month in months:
    accumulated_usd += month_amount_usd
    accumulated_veb = convert(accumulated_usd, month_rate)  # WRONG!

# CORRECT - Convert each month's amount once, accumulate VEB
accumulated_veb = 0.0
for month in months:
    month_veb = convert(month_amount_usd, month_rate)
    accumulated_veb += month_veb  # Proper accrual
```

### Exchange Rate Override for Interest

**Decision:** Interest calculation should IGNORE exchange rate override

**Rationale:**
- Interest accumulated over months at historical rates
- Different from other benefits (computed once at liquidation)
- Both reports must match for employee understanding

---

## AR-I Portal (v17.0.1.0.0)

**Module Structure:**
```
ueipab_ari_portal/
├── models/
│   ├── hr_employee_ari.py    # Main AR-I model (81 fields)
│   ├── ari_excel_generator.py # SENIAT template filler
│   └── hr_contract.py        # Contract extension
├── controllers/portal.py     # Portal routes
├── views/                    # XML views
├── wizard/ari_reject_wizard.py
├── security/                 # Access rules
├── data/                     # Cron, email templates
└── static/templates/         # SENIAT Excel template
```

**Tax Calculation Example:**
```
Annual Income: 50,000.00 (5,555.56 UT @ 9.00 Bs/UT)
Desgravamen Único: 774.00 UT
Taxable Income: 4,781.56 UT
Estimated Tax: 811.65 UT
Personal Rebate: 10.00 UT
Tax to Withhold: 801.65 UT
Withholding %: 14.43%
```

---

## Smart Invoice Confirmation Script (2025-11-27)

**Business Rules:**
| Scenario | Unit Price | Credit Applied |
|----------|------------|----------------|
| Credit ≥ $34.99 | $162.39 (discount) | Yes |
| Credit < $34.99 | $197.38 (regular) | Yes |
| No credit | $197.38 (regular) | No |

**Usage:**
```bash
# Dry run
docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http \
  < /opt/odoo-dev/scripts/smart_invoice_confirmation.py
```

---

## V1 to V2 Migration

**V1 Fields Removed:**
- `ueipab_salary_base`, `ueipab_bonus_regular`, `ueipab_extra_bonus`
- `ueipab_deduction_base`, `ueipab_monthly_salary`, `ueipab_salary_notes`

**V2 Fields Active:**
- `ueipab_salary_v2`, `ueipab_extrabonus_v2`, `ueipab_bonus_v2`, `cesta_ticket_usd`
- `ueipab_ari_withholding_rate`, `ueipab_ari_last_update`
- `ueipab_original_hire_date`, `ueipab_previous_liquidation_date`
- `ueipab_vacation_paid_until`, `ueipab_vacation_prepaid_amount`
- `ueipab_other_deductions`

---

**Last Updated:** 2026-05-18

---

## 2026-05-27 — SLIP/801 RAMON BELLO — Pro-rated payslip for terminated employee (MAYO31)

**Context:** RAMON BELLO's contract (id=117) ended 2026-05-22 and was in `close` state when the MAYO31 batch (May 16–31) was computed. Odoo's `_get_contract()` filters out `close` contracts → `contract_id = False` → zero lines computed on the slip.

**Fix applied via XML-RPC on production:**
1. Temporarily set contract state → `open`
2. Scaled `ueipab_salary_v2` ($187.31 → $87.41) and `ueipab_bonus_v2` ($233.32 → $108.88) using factor `14/30` so that the V2 rule's `/2` yields the correct 7/30 pro-ration
3. Ran `action_compute_sheet()` on payslip id=852
4. Manually wrote `contract_id = 117` (not set automatically by compute)
5. Restored original contract values and state → `close`
6. Adjusted `VE_CESTA_TICKET_V2` from $20.00 → $9.33 (7/15 days), updated `VE_GROSS_V2` and `VE_NET_V2`

**Final SLIP/801 values (USD):** Salary $43.71 · Bonus $54.44 · Cesta $9.33 · Gross $107.48 · Deductions -$1.58 · **Net $105.90**

**Pattern documented in CLAUDE.md** → Key Technical Patterns → "Closed-Contract Payslip".

---

## 2026-05-18 — Distintivo Escolar Email Campaign

**Feature #65** — Almacenes París official uniform badge provider announced via email.

- **Template:** HTML with school logo, provider card, price badge, clickable WA/Email/IG buttons, Glenda Telegram CTA
- **From:** soporte@ueipab.edu.ve | **Reply-To:** pagos@ueipab.edu.ve
- **Recipients:** 322 unique — 178 ACTIVE + 6 PIPELINE families (279 parent emails) + 45 employees
- **Sent:** 2026-05-18 ~14:06 VET from production | **Result:** 322 sent, 0 failed
- **Glenda knowledge:** `_INSTITUTIONAL_KNOWLEDGE` updated with provider, contact links, local advisor Sra. Johanna Hernández (WA https://wa.me/584248340051)

## 2026-05-18 — AI Agent v1.49.x — Bot Detection + List Actions + Telegram Invite Fix

- **Bot detection Tier-1:** speed check (<2s gap) + rate limit (>30 inbound/24h) → auto-silence with chatter note
- **List actions:** Cerrar Manualmente / Silenciar / Activar Respuestas on `ai.agent.conversation`
- **`silent` field:** suppresses replies, reminders, cron timeouts; reversible
- **Telegram invite fix:** `not agent_message_ids.filtered(outbound)` — first reply now correctly fires
- **Telegram invite:** direct `https://t.me/GlendaUeipabBot` hyperlink included
