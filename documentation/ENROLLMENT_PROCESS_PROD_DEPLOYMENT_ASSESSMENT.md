# Enrollment Master Business Process — Production Deployment Assessment

**Date:** 2026-06-25 · **Author:** assessment from direct code/infra inspection · **Target:** `DB_UEIPAB` (prod)
**Scope:** Deploy the entire enrollment master business process to production: **onboarding** (`enrollment.journey`), **withdrawal/egreso** (`enrollment.withdrawal`), **Phase 1b Akdemia student import** + cron cache, the **continuity-survey** S0 gate, and the **Academic Annual Report** page that funnels into it.

---

## 0. Verdict

**🟡 CONDITIONALLY READY.** The module is functionally complete and tested in `testing`. There are **no architectural blockers**, but **4 must-do items** before flipping prod on (all small/config-level), plus a handful of recommended checks. Estimated effort: ~half a day including smoke tests. The single most important gate is **#B1 (report host/URL)** and **#B3 (config params)**.

---

## 1. Component readiness matrix

| Component | State | Prod-ready? | Notes |
|-----------|-------|-------------|-------|
| `enrollment.journey` (9-step onboarding + S0 gate) | v0.11.2 testing | ✅ code | depends only on `ueipab_sales` (already in prod) |
| `enrollment.withdrawal` (5-step egreso, auto-create on decline) | v0.11.2 testing | ✅ code | Phase 5 Gmail auto-suspend is manual-v1 (acceptable) |
| Phase 1b Akdemia import (live→snapshot, preview wizard) | v0.11.2 testing | ✅ code | needs `akdemia.api_key` param in prod |
| Akdemia cron cache (`akdemia_api_sync.py` Phase 2b) | done | ⚠️ infra | already targets prod in `ODOO_CONFIGS`; needs prod creds in cron env |
| Continuity survey (S0 confirm/decline) | committed | ✅ code | part of `enrollment.journey` |
| Annual Report static page | live on **dev** nginx | ⚠️ infra | **must be reachable on a prod-stable host** (see B1) |
| QWeb contract PDF + QR (`CSE-2627`) | testing | ✅ code | QR uses `web.base.url` → auto-correct per env |

---

## 2. 🔴 Blockers (must fix before go-live)

### B1 — Annual Report host / public reachability
The report is served from `/var/www/dev/reporte-anual-2025-2026/` on the **dev** droplet (`dev.ueipab.edu.ve`). Parent-facing blast links point here.
- **Decision needed:** keep parents pointed at `dev.ueipab.edu.ve` (works today, but couples a customer-facing asset to the dev box), **or** publish the page on the prod host and repoint.
- **Now configurable:** `REPORT_URL` is no longer hardcoded — set `ir.config_parameter` **`enrollment.report_url`** in `DB_UEIPAB` to the chosen public URL (falls back to the dev URL if unset).
- If moving to prod host: copy `web/reporte-anual-2025-2026/index.html` + `/flyers/` assets (incl. `ceo-profile-pic.jpeg`, partner logos) to the prod webroot and add the nginx alias block (mirror the dev one).

### B2 — Prod module deploy via the separate repo
Prod addons (`/home/vision/ueipab17/addons`) is a **separate git repo** (`3DVision-CA/ueipab17-cm`), NOT this dev repo. `git pull` will NOT carry these commits.
- **Action:** `scp` the whole `ueipab_enrollment_journey/` dir to prod (back up any existing copy first), then
  `docker exec ueipab17 odoo -i ueipab_enrollment_journey -d DB_UEIPAB --stop-after-init` (first install → `-i`, later upgrades → `-u`), then `docker restart ueipab17`, then verify `installed_version == 17.0.0.11.2` via XML-RPC.

### B3 — Prod config parameters (none exist yet in `DB_UEIPAB`)
Set these `ir.config_parameter` keys in prod before first use:
| Key | Value | Why |
|-----|-------|-----|
| `akdemia.api_key` | (the real Bearer token) | import fails with `UserError` without it |
| `akdemia.base_url` | `https://api-staging.akdemia.com` | confirmed real for both envs; leave default unless a prod URL is issued |
| `enrollment.report_url` | chosen public report URL (see B1) | blast CTA target |
| `web.base.url` | prod Odoo URL (already set in prod) | journey/contract/QR links — **verify it is correct & `web.base.url.freeze=True`** |
| `akdemia.min_cache_guardians` | `50` (default) | sanity floor; lower only if prod has <50 families |

### B4 — Cron cache publish to prod needs prod credentials
`akdemia_api_sync.py` Phase 2b publishes `akdemia.students_json` to **every** env in `ODOO_CONFIGS`, but the prod entry needs `ODOO_PASSWORD`/prod creds in the cron environment (the script raises if `TARGET_ENV=production` without it). Confirm the cron wrapper sources the prod env file, OR run the publish from a context that has prod creds. Until then, the prod import button still works **live** (cache is an optimization, not a dependency).

---

## 3. 🟢 Non-blockers / already handled
- **Dependency:** only `ueipab_sales` (in prod since 2026-06-11). ✅
- **No demo/seed data** in `data/` — the testing demo journey (id=1) is a hand-created record, NOT module data, so it will **not** be carried into prod. ✅
- **Contract sequence** (`sequence_enrollment_contract`) is created on install; prod gets its own counter. ✅
- **Hardcoded notification emails** (`soporte@`, `pagos@`, `josefina.rodriguez@`, `lorena.reyes@`, `alejandra.lopez@`, `arcides.arzola@`) are real `@ueipab.edu.ve` addresses — verify each exists/receives in prod (they are used as To/CC on S0 + withdrawal notifications). ✅ likely fine.
- **`web.base.url`-based URLs** (journey page, contract QR, withdrawal backend links) auto-resolve per env. ✅
- **Security:** `group_enrollment_support` + access rules for all 4 models incl. the new import-preview transient. ✅

---

## 4. Recommended pre-flight checks (prod, read-only first)
1. **Outbound mail:** S0 blast + withdrawal notifications send real email. Confirm prod mail server + that `soporte@`/`pagos@` inboxes are monitored. Do a **dry/test S0 send to gustavo.perdomo@** before any parent blast (per test-routing rule).
2. **Akdemia match rate:** run the import on **one** known prod journey and confirm `partner.vat` ↔ Akdemia guardian cédula match works against real prod partners (VAT format `VXXXXXXXX`).
3. **Graduating-senior edge case** (`_next_grade("5° Año")` → "6° Año") — confirm with CEO whether 5° Año families are included before mass-sharing journey links.
4. **`ai_agent.dry_run`** — the WA escalation button (`action_send_wa`) honors it; confirm desired state in prod.

---

## 5. Deploy runbook (ordered)
1. **Backup** prod addons copy of any prior module + a `DB_UEIPAB` DB backup.
2. `scp` `ueipab_enrollment_journey/` → prod `/home/vision/ueipab17/addons/`.
3. `docker exec ueipab17 odoo -i ueipab_enrollment_journey -d DB_UEIPAB --stop-after-init` → `docker restart ueipab17`.
4. Verify `installed_version` = `17.0.0.11.2` (XML-RPC).
5. Set the **B3** config params.
6. Resolve **B1** (report URL/host) + set `enrollment.report_url`.
7. Resolve **B4** (cron prod creds) — or defer (live import still works).
8. Run **§4** pre-flight checks.
9. Pilot: one journey end-to-end (import → S0 → contract PDF → withdrawal on decline) before any blast.

---

## 6. Smoke tests (post-deploy, prod)
- Open `/enrollment-journey/<token>` for a pilot family → page renders, correct students/grades.
- Import button → preview wizard shows real Akdemia students → confirm → lines created.
- Print contract → `CSE-2627-0001` + QR resolves to `/verify-contract/<token>`.
- Decline S0 → `enrollment.withdrawal` auto-created + internal email to `pagos@` with backend link.
- Report page loads on the chosen host; CTA `?j=<journey>` routes back to the journey.

---

## 7. Rollback
- Module: reinstall the backed-up prior addon dir (or uninstall `ueipab_enrollment_journey` if it was never in prod) + `docker restart ueipab17`. Since no other module depends on it, uninstall is clean.
- Config params: delete the keys added in B3.
- Report: revert nginx alias / repoint `enrollment.report_url`.
- DB: restore the pre-deploy `DB_UEIPAB` backup if data was touched.

---

## 8. Open decisions for the CEO
1. **Report host** — stay on `dev.ueipab.edu.ve` or move to a prod-stable URL? (drives B1)
2. **Graduating 5° Año** — include in the wizard or exclude?
3. **Launch sequencing** — report public announce + journey blast wave timing (option b previously agreed).
4. **Withdrawal Gmail suspension** — keep manual v1 or build the Admin SDK auto-suspend (Phase 5) before go-live? (manual is acceptable to launch.)

---

**Bottom line:** the code is prod-grade and tested; what remains is **infra + config wiring**, not engineering. Clear B1–B4, run the pre-flight + pilot, and the full master process can go live.

---

## 9. Deploy kit (built 2026-06-25) + read-only prod probe

**Scripts (run by the operator — harness blocks Claude from prod writes):**
- `scripts/deploy_enrollment_journey_prod.sh -i|-u` — backup (outside addons_path) → scp → install/upgrade (captures odoo's real exit code) → restart → poll-for-boot → assert `state=installed` AND `installed_version==17.0.0.11.2`. Uses `sshpass -e` (no password in process table). Hardened per the deploy-kit review (8 findings applied).
- `scripts/prod_post_deploy_enrollment_journey.py [--live] [--allow-dev-report]` — sets `akdemia.api_key` (from `AKDEMIA_API_KEY` env), `akdemia.base_url`, `akdemia.min_cache_guardians`, `enrollment.report_url`; **refuses `--live` if report URL still points at dev** unless `--allow-dev-report`. Read-only verification of deps/fields/sequence/group/mail.

**Read-only prod probe (2026-06-25, via XML-RPC — NO hard blockers):**
| Check | Result |
|-------|--------|
| `ueipab_sales` dependency | ✅ installed, 17.0.1.2.1 |
| `ueipab_enrollment_journey` | ✅ cleanly absent (not yet deployed) |
| `web.base.url` | ✅ `https://odoo.ueipab.edu.ve` (https prod, not dev) |
| `ir.mail_server` | ✅ 1 configured |
| `res.partner` with VAT | ⚠️ 753 / 972 (~77.5%) — ~219 parents lack the Akdemia match key (cédula); not a code blocker, limits import coverage until backfilled |
| `enrollment.journey` records | ✅ model absent → 0 pre-existing |
| Company id=1 | `Instituto Privado Andrés Bello CA` |

## 10. Go / No-Go gates (all must be GREEN before any parent-facing blast)
1. Module `state=installed`, `installed_version==17.0.0.11.2`, `ueipab_sales` installed.
2. Config params set: `akdemia.api_key` (non-empty), `akdemia.base_url`, `min_cache_guardians=50`, `enrollment.report_url` = chosen public URL.
3. `web.base.url` correct + `web.base.url.freeze=True`.
4. Outbound mail proven: a real test S0 email arrived at `gustavo.perdomo@`; `soporte@`/`pagos@` + CC addresses monitored.
5. `enrollment.report_url` loads with assets + CTA round-trips to `/enrollment-journey/<token>`.
6. Akdemia import proven on a real pilot family (correct vat↔cédula match + next-grade roll; no `akdemia.api_key` UserError).
7. Contract prints `CSE-2627-0001` + QR; `/verify-contract/<token>` resolves on prod.
8. Decline S0 → `enrollment.withdrawal` auto-created + internal notice to `pagos@` with working backend link.
9. Full pilot GREEN with **zero real-parent emails** (pilot contact = `gustavo.perdomo@`); `ai_agent.dry_run` at intended state; 5° Año inclusion decided.

## 11. Smoke test (pilot ONE family, contact = gustavo.perdomo@)
0. Create one `enrollment.journey` for a real family whose `partner.vat` is a valid Akdemia guardian cédula; note id/token.
1. Open `/enrollment-journey/<token>` → 9-step timeline renders with correct students/grades.
2. Import button → preview wizard lists real Akdemia students (vat↔cédula).
3. Confirm → student lines created (next-year grades, no dupes).
4. Send S0 (to gustavo.perdomo@) → click CONFIRM → gate flips, advances past Block 1.
5. Print contract → `CSE-2627-0001` + QR on all pages → `/verify-contract/<token>` resolves on prod.
6. Second pilot → click DECLINE → `enrollment.withdrawal` auto-created + internal notice to `pagos@` with backend link.
7. Open `enrollment.report_url?j=<journey>` → loads with assets → CTA routes back to the journey.

## 12. Rollback (ordered)
1. Halt any in-flight blast.
2. Restore `…/ueipab17_addon_backups/ueipab_enrollment_journey.bak-<TS>` (or **uninstall** if fresh install — clean, only `ueipab_sales` depends-on-it the other way).
3. Delete config params (`akdemia.*`, `enrollment.report_url`); leave `web.base.url`.
4. Revert nginx alias / repoint report URL (skip if using the dev-hosted page).
5. DB restore only if data beyond the pilot was created (prefer surgical delete of pilot journeys/withdrawals).
6. `docker restart ueipab17`; wait for boot.
7. Verify via XML-RPC: module uninstalled (or prior version) + removed params return empty.
