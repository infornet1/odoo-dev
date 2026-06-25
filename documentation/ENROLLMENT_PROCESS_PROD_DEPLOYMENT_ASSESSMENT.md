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
