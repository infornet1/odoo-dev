# Akdemia Data Pipeline

**Status:** Testing | **Type:** Script + Cron | **Revived:** 2026-02-11

Daily automated extraction of student/parent data from Akdemia student management system, with email change detection to auto-resolve AI agent conversations.

## Infrastructure

| Component | Location | Status |
|-----------|----------|--------|
| Akdemia Scraper | `/var/www/dev/odoo_api_bridge/customer_matching/integrations/akdemia_scraper.py` | Playwright-based, fixed 2026-02-11 |
| Daily Orchestrator | `/var/www/dev/odoo_api_bridge/scripts/customer_matching_daily.py` | **Created 2026-02-11** |
| Cron Wrapper | `/var/www/dev/odoo_api_bridge/scripts/customer_matching_wrapper.sh` | Configured, daily 6AM VET |
| Cron Job | `/etc/cron.d/customer_matching` | Active (trailing newline fixed) |
| Downloads Dir | `/var/www/dev/odoo_api_bridge/akdemia_downloads/` | Active |
| Historical XLS | `customer_matching/data/xls_uploads/2025/09/` | 10+ files from Sep 2025 |

## Akdemia Scraper Details

- **Platform:** `https://edge.akdemia.com` (Playwright headless Chromium)
- **Credentials:** `gustavo.perdomo@ueipab.edu.ve` (hardcoded in scraper)
- **Output:** Excel file `akdemia_students_{period}_{date}.xls` (122 cols, A-DR)
- **Data:** Student name, cedula, grade, section, parent name/email/phone, authorized reps, payment status, balance
- **Report flow (updated 2026-02-11):** Generar -> async -> notification when done -> download from `/notifications`
- **Scraper fixes (2026-02-11):** 3 education level checkboxes (`.js-select-all-checkbox`), `#authorized_guardians_information` toggle, notification-based async download
- **XLS structure:** 227 rows, 122 cols (A-DR), headers at row index 2, metadata rows 0-1
- **Wrapper e2e tested 2026-02-12:** Full pipeline (scrape -> sync) completes in ~30s, exit code 0

## Daily Orchestrator

**Script:** `/var/www/dev/odoo_api_bridge/scripts/customer_matching_daily.py`

Thin orchestrator:
1. **Phase 1:** Scrape Akdemia (Playwright) -> download fresh XLS
2. **Phase 2:** Call `akdemia_email_sync.py` as subprocess with `--file <downloaded_xls>`

**Usage:**
```bash
python3 customer_matching_daily.py                # dry run (scrape + sync preview)
python3 customer_matching_daily.py --live          # apply real changes
python3 customer_matching_daily.py --skip-scrape   # use latest existing XLS
python3 customer_matching_daily.py --skip-sheets   # skip Google Sheets update
python3 customer_matching_daily.py --skip-odoo     # skip Odoo bounce log sync
```

**Exit codes:** 0=success, 1=scraper failed, 2=email sync failed

## Akdemia2526 Sheet Structure

- **Spreadsheet:** `1Oi3Zw1OLFPVuHMe9rJ7cXKSD7_itHRF0bL4oBkKBPzA` (Customer Database Odoo)
- **Tab:** `Akdemia2526` (227 rows, headers in row 3)
- **Key email columns:** AU = `Correo electronico de Representante` (parent 1), BX = same (parent 2)
- **Key name columns:** AB/AE = parent 1 name/surname, BE/BH = parent 2 name/surname
- **Key cedula columns:** AH = parent 1 cedula, BK = parent 2 cedula
- **Data starts:** Row 4 (rows 1-2 are school name/year)

## Akdemia Email Sync Script (Implemented 2026-02-08)

**Script:** `scripts/akdemia_email_sync.py`
**Safety:** `DRY_RUN=True`, `TARGET_ENV=testing` by default. Use `--live` to apply.

Daily pipeline after Akdemia scrape -- closes the loop when tech support updates an email in Akdemia without Glenda knowing:

1. **Phase 1:** Get XLS (`--file` manual, or latest from downloads/historical dir)
2. **Phase 2:** Parse XLS -> parent email map by cedula (287 parents, 3 parent sets per student)
3. **Phase 3:** Compare with unresolved `mail.bounce.log` records (match `partner.vat` -> Akdemia cedula)
4. **Phase 4:** Auto-resolve: `action_apply_new_email()` on bounce log + `action_resolve()` on AI conversation + update `mailing.contact` by email match
5. **Phase 5:** Update Akdemia2526 Google Sheet tab with fresh XLS data

**Dry run results (Sep 2025 XLS):** 14 email changes detected (PDVSA domains -> gmail/hotmail)

**Usage:**
```bash
python3 scripts/akdemia_email_sync.py                    # dry run
python3 scripts/akdemia_email_sync.py --live              # apply changes
python3 scripts/akdemia_email_sync.py --file /path.xls    # specific file
python3 scripts/akdemia_email_sync.py --skip-sheets       # skip Google Sheets
```

## Bounce Log Resolution Paths (6 total)

- PATH A: Glenda WhatsApp -> customer gives new email
- PATH B: Email verification checker -> customer replies to verification email
- PATH C: Akdemia sync -> tech support updated email in Akdemia (XLS download)
- PATH D: Manual -> staff clicks "Restaurar" or "Aplicar Nuevo" in Odoo
- PATH E: Escalation -> customer asks off-topic, Freescout ticket created, conversation continues
- PATH F: Akdemia Auto-Resolve -> bounced email not in Akdemia but valid alternative exists for same cedula

## Mailing Contact Sync (v1.2.0)

**Gap discovered 2026-02-08:** Bounce resolution updated `res.partner.email` but NOT `mailing.contact`. Production has 350 mailing contacts across 3 lists (Toda la comunidad=239, Grupo1=110, Newsletter=1). 28 of 37 bounced emails exist in `mailing.contact` -- campaigns would re-bounce to stale emails.

**Fix (3 parts):**
- **Part A (Module):** `ueipab_bounce_log` `_resolve_record()` now searches `mailing.contact` by bounced email and updates/removes as needed
- **Part B (Script):** `akdemia_email_sync.py` also updates `mailing.contact` via XML-RPC during resolution
- **Part C (Testing sync):** Import production mailing lists/contacts into testing for parity

**CRITICAL:** Never touch `todalacomunidad@ueipab.edu.ve` -- that email holds all `@ueipab.edu.ve` institutional users, not parents.

## Production Mailing Lists

| List | ID | Contacts | Purpose |
|------|----|----------|---------|
| Toda la comunidad | 2 | 239 | All parent emails for school campaigns |
| Grupo1 | 3 | 110 | Subset of parents (specific grade group) |
| Newsletter | 1 | 1 | General newsletter |
