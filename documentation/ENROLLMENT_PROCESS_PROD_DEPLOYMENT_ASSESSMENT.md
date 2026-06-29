# Enrollment Master Business Process — Production Deployment Assessment

> ## ✅ DEPLOYED TO PRODUCTION — 2026-06-29
> The full stack is live in `DB_UEIPAB`. `ueipab_sales` **17.0.1.2.5** (`-u`) + `ueipab_enrollment_journey` **17.0.0.14.0** (fresh `-i`), both `installed` & verified; `enrollment.quote.version` present; 0 journeys (clean). Config params + `web.base.url.freeze=True` set. Annual Report + 16 assets served from the prod host (`/var/www/reporte-anual-2025-2026/` + `/var/www/flyers/`, nginx alias, HTTP 200). Prod-independent **cache-only** Akdemia cron installed (`/etc/cron.d/akdemia_cache_refresh`, 06:30 VET, `--skip-odoo --skip-sheets`; test run published 322 guardians). See **§13 Deployment log** below.
> - **B5 needed no proxy change** — prod nginx already forwards `X-Forwarded-For`/`X-Real-IP` + `Host $http_host`; no route whitelist (catch-all serves all enrollment routes).
> - **⚠️ B6 legal gate STILL OPEN** — the T&C e-sig + anticipo clauses are now in the LIVE prod PDFs, but **counsel sign-off is NOT obtained**. Deploy is safe (nothing auto-sends to parents). **No parent-facing blast until counsel signs off; pilot/validation to `gustavo.perdomo@` only.**
> - **Pilot deferred** (user will validate the flow in the prod UI).

**Date:** 2026-06-25 · **Updated:** 2026-06-29 (**DEPLOYED**; prior refresh 2026-06-28 to v0.13.2→v0.14.0) · **Author:** assessment from direct code/infra inspection · **Target:** `DB_UEIPAB` (prod)
**Scope:** Deploy the entire enrollment master business process to production: **onboarding** (`enrollment.journey`), **withdrawal/egreso** (`enrollment.withdrawal`), **Phase 1b Akdemia student import** + cron cache, the **continuity-survey** S0 gate, the **auto-quote on S0 'Sí' → quote send/accept/revision + version control** lifecycle (incl. the new `enrollment.quote.version` model + Tier-2 electronic acceptance), the **T&C legal clauses** (e-signature + fractioned-invoicing/anticipos) embedded in both PDFs, and the **Academic Annual Report** page that funnels into it.

> **⚠️ 2026-06-28 refresh:** the original assessment was written against **v0.11.2**. Three feature waves landed since — **v0.12.x** (auto-quote on S0 'Sí'), **v0.13.x** (quote accept/revision + version control + electronic-acceptance T&C clauses), and **v0.14.0** (in-person assist + enrollment checklist for walk-in families). This revision updates every version target (→ **17.0.0.14.0** / `ueipab_sales` → **17.0.1.2.5**), adds the new model + public routes, and adds two infra gaps (nginx `X-Forwarded-For`, route-prefix) and a legal sign-off gate. *(v0.14.0 in-person is backend-only — no new public routes or nginx impact; reuses the same model/token/QR/audit log.)*

---

## 0. Verdict

**🟡 CONDITIONALLY READY.** The module is functionally complete and tested in `testing`. There are **no architectural blockers**, but the must-do list has grown to **6 items** before flipping prod on (config + 2 nginx + 1 legal), plus recommended checks. Estimated effort: ~half a day including smoke tests. The most important gates are **#B1 (report host/URL)**, **#B3 (config params)**, **#B5 (nginx `X-Forwarded-For` for e-sig IP capture)**, and **#B6 (counsel sign-off on the T&C clauses)**.

---

## 1. Component readiness matrix

| Component | State | Prod-ready? | Notes |
|-----------|-------|-------------|-------|
| `enrollment.journey` (9-step onboarding + S0 gate) | v0.13.2 testing | ✅ code | depends only on `ueipab_sales` (already in prod) |
| `enrollment.withdrawal` (5-step egreso, auto-create on decline) | v0.13.2 testing | ✅ code | Phase 5 Gmail auto-suspend is manual-v1 (acceptable) |
| Phase 1b Akdemia import (live→snapshot, preview wizard) | v0.13.2 testing | ✅ code | needs `akdemia.api_key` param in prod |
| Akdemia cron cache (`akdemia_api_sync.py` Phase 2b) | done | ⚠️ infra | already targets prod in `ODOO_CONFIGS`; needs prod creds in cron env |
| Continuity survey (S0 confirm/decline) | committed | ✅ code | part of `enrollment.journey` |
| **Auto-quote on S0 'Sí'** (`_ensure_quote`) | v0.12.0+ testing | ✅ code | **confirming S0 creates a real `sale.order` in prod** — idempotent, one per journey; needs `ueipab_sales` quote engine (in prod) |
| **Quote send / accept / revision + version control** | v0.13.0 testing | ✅ code | **new model `enrollment.quote.version`** (immutable log + frozen PDF + SHA-256); Tier-2 e-acceptance captures IP/UTC/SHA-256 → **depends on nginx `X-Forwarded-For` (B5)** |
| **T&C legal clauses** (e-sig + anticipos) in both PDFs | v0.13.2 / `ueipab_sales` 1.2.5 testing | ⚠️ legal | code ready; **pending counsel sign-off (B6)** before parent-facing use |
| Annual Report static page | live on **dev** nginx | ⚠️ infra | **must be reachable on a prod-stable host** (see B1) |
| QWeb contract PDF + QR (`CSE-2627`) | testing | ✅ code | QR uses `web.base.url` → auto-correct per env; needs `ueipab_sales` ≥ 1.2.2 QR path |

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
  `docker exec ueipab17 odoo -i ueipab_enrollment_journey -d DB_UEIPAB --stop-after-init` (first install → `-i`, later upgrades → `-u`), then `docker restart ueipab17`, then verify `installed_version == 17.0.0.14.0` via XML-RPC.

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

### B5 — Prod nginx must forward client IP **and** the route prefix must cover the new sub-paths  *(NEW — added with v0.13.x)*
The quote lifecycle added public routes and a Tier-2 electronic-acceptance flow that records the parent's IP as legal evidence.
- **Client IP:** `_client_ip()` reads `X-Forwarded-For` → `X-Real-IP` → `remote_addr`. Behind nginx, `remote_addr` is `127.0.0.1`. **If the prod vhost does not set `proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;` (and ideally `X-Real-IP $remote_addr;`), every accepted quote stores IP `127.0.0.1`** — defeating the e-signature evidence (Art. 8(3) metadata). Add these headers to the prod `location /` block.
- **Route prefix:** the new public routes are **sub-paths** of `/enrollment-journey`:
  `…/<token>/confirm`, `…/<token>/decline`, `…/<token>/cotizacion.pdf`, `…/<token>/quote/accept`, `…/<token>/quote/revision`, plus `ueipab_sales` `/verify-quote/<token>` and `/verify-contract/<token>`.
  The prod nginx whitelist for `/enrollment-journey` **must be a prefix match** (`location /enrollment-journey`), not exact — and `/verify-quote` + `/verify-contract` need their own allow entries.
- **POST→303 redirect:** `/confirm`, `/quote/accept`, `/quote/revision` POST then 303-redirect. The dev S0 'Sí' 404 was a port-stripping bug fixed with `Host $http_host`. Prod (`https://odoo.ueipab.edu.ve` :443, no port to strip) likely works, but **verify the redirect lands on https with the path intact** — don't assume.

### B6 — Legal sign-off on the embedded T&C clauses  *(NEW — added with v0.13.2)*
Both PDFs now embed **electronic-signature** clauses (Acuerdo Cl.10 / Contrato Cl.11) and **fractioned-invoicing / anticipo** clauses (Acuerdo Cl.11 / Contrato Cl.12). These ship to real parents on deploy. Status: **pending counsel pass** (the Art. 16 *"las partes disponen"* wording is load-bearing). **Obtain counsel sign-off before any parent-facing send.** See `TC_ELECTRONIC_SIGNATURE_ENHANCEMENT.md` + `ELECTRONIC_SIGNATURES_VENEZUELA_LAW.md`.

---

## 3. 🟢 Non-blockers / already handled
- **Dependency:** only `ueipab_sales` (in prod since 2026-06-11). ✅
- **No demo/seed data** in `data/` — the testing demo journey (id=1) is a hand-created record, NOT module data, so it will **not** be carried into prod. ✅
- **Contract sequence** (`sequence_enrollment_contract`) is created on install; prod gets its own counter. ✅
- **Hardcoded notification emails** (`soporte@`, `pagos@`, `josefina.rodriguez@`, `lorena.reyes@`, `alejandra.lopez@`, `arcides.arzola@`) are real `@ueipab.edu.ve` addresses — verify each exists/receives in prod (they are used as To/CC on S0 + withdrawal notifications). ✅ likely fine.
- **`web.base.url`-based URLs** (journey page, contract QR, withdrawal backend links) auto-resolve per env. ✅
- **Security:** `group_enrollment_support` + access rules for all **5** models incl. the import-preview transient **and the new `enrollment.quote.version` audit-log model** (`access_enrollment_quote_version_support` + `_user` in `ir.model.access.csv`). ✅
- **Quote lifecycle data:** no new config params, no demo data; `enrollment.quote.version` table is created on upgrade. Frozen quote PDFs are stored as `ir.attachment` (binary) per accepted/issued version — normal Odoo storage, no filestore special-casing. ✅

---

## 4. Recommended pre-flight checks (prod, read-only first)
1. **Outbound mail:** S0 blast + withdrawal notifications send real email. Confirm prod mail server + that `soporte@`/`pagos@` inboxes are monitored. Do a **dry/test S0 send to gustavo.perdomo@** before any parent blast (per test-routing rule).
2. **Akdemia match rate:** run the import on **one** known prod journey and confirm `partner.vat` ↔ Akdemia guardian cédula match works against real prod partners (VAT format `VXXXXXXXX`).
3. **Graduating-senior edge case** (`_next_grade("5° Año")` → "6° Año") — confirm with CEO whether 5° Año families are included before mass-sharing journey links.
4. **`ai_agent.dry_run`** — the WA escalation button (`action_send_wa`) honors it; confirm desired state in prod.
5. **Auto-quote side-effect** — confirming S0 'Sí' creates a real `sale.order` via `create_ai_quote`. On the pilot, confirm the order is created **draft** (`quote_state='draft'`), priced at the correct llamado, sized to enrolling-student count, and that the customer-email suppression on AI quotes still holds (no stray customer mail). 
6. **E-signature IP capture** — after B5, on the pilot accept, verify `enrollment.quote.version.accept_ip` is the **real client IP, not 127.0.0.1**, and `accept_timestamp_utc` + `pdf_sha256` + `tyc_accepted` are populated.

---

## 5. Deploy runbook (ordered)
1. **Backup** prod addons copy of any prior module + a `DB_UEIPAB` DB backup.
2. `scp` **both** `ueipab_sales/` (1.2.5) and `ueipab_enrollment_journey/` (0.13.2) → prod `/home/vision/ueipab17/addons/` (back up the existing `ueipab_sales` first).
3. **Upgrade `ueipab_sales` first** (it carries the QR path + the Acuerdo T&C clauses): `docker exec ueipab17 odoo -u ueipab_sales -d DB_UEIPAB --stop-after-init`. Then **install enrollment**: `docker exec ueipab17 odoo -i ueipab_enrollment_journey -d DB_UEIPAB --stop-after-init` → `docker restart ueipab17`.
4. Verify via XML-RPC: `ueipab_sales installed_version == 17.0.1.2.5` **and** `ueipab_enrollment_journey installed_version == 17.0.0.14.0`; confirm model `enrollment.quote.version` exists.
5. Set the **B3** config params.
6. Resolve **B1** (report URL/host) + set `enrollment.report_url`.
7. **Resolve B5** — add `proxy_set_header X-Forwarded-For`/`X-Real-IP` to the prod vhost; confirm `/enrollment-journey` is a **prefix** allow + add `/verify-quote` + `/verify-contract`; `nginx -t` + reload.
8. Resolve **B4** (cron prod creds) — or defer (live import still works).
9. **Resolve B6** — obtain counsel sign-off on the T&C clauses **before** any parent-facing send.
10. Run **§4** pre-flight checks.
11. Pilot: one journey end-to-end (import → S0 'Sí' → **auto-quote → send → accept (verify real IP) / revision → re-issue** → contract PDF → withdrawal on decline) before any blast.

---

## 6. Smoke tests (post-deploy, prod)
- Open `/enrollment-journey/<token>` for a pilot family → page renders, correct students/grades.
- Import button → preview wizard shows real Akdemia students → confirm → lines created.
- **Confirm S0 'Sí' → auto-quote**: a draft `sale.order` is created (correct llamado/price/student count), `quote_state='draft'`, **no customer email leaks**.
- **Quote download gate**: before "Enviar cotización", `…/cotizacion.pdf` returns 404; after send, it returns the frozen PDF (200).
- **Accept**: tick T&C + "Acepto" → `enrollment.quote.version` marked accepted with **real IP (not 127.0.0.1)**, UTC ts, SHA-256, `tyc_accepted`; step 1 auto-done.
- **Revision**: "Solicitar revisión" → escalation email to **soporte@ CC pagos@**; "Re-emitir" issues v2 with the **same token + QR**.
- Print contract → `CSE-2627-0001` + QR resolves to `/verify-contract/<token>`; Acuerdo PDF carries Cl.10/Cl.11; contract PDF carries Cl.11/Cl.12.
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
- `scripts/deploy_enrollment_journey_prod.sh -i|-u` — backup (outside addons_path) → scp → install/upgrade (captures odoo's real exit code) → restart → poll-for-boot → assert `state=installed` AND `installed_version==17.0.0.14.0`. Uses `sshpass -e` (no password in process table). Hardened per the deploy-kit review (8 findings applied).
- `scripts/prod_post_deploy_enrollment_journey.py [--live] [--allow-dev-report]` — sets `akdemia.api_key` (from `AKDEMIA_API_KEY` env), `akdemia.base_url`, `akdemia.min_cache_guardians`, `enrollment.report_url`; **refuses `--live` if report URL still points at dev** unless `--allow-dev-report`. Read-only verification of deps/fields/sequence/group/mail.

**⚠️ Deploy-kit gaps to close before running (2026-06-28):**
- `deploy_enrollment_journey_prod.sh` reads `EXPECTED_VER` **dynamically from the manifest** → it auto-asserts `17.0.0.14.0`, no edit needed. ✅
- **But it only handles `ueipab_enrollment_journey`** and its pre-flight merely checks `ueipab_sales` is *present* — it does **not** upgrade `ueipab_sales` to 1.2.5 nor assert its version. **`ueipab_sales` must be scp'd + `-u` upgraded manually (runbook step 3) before the enrollment install.** Recommend tightening the pre-flight to assert `ueipab_sales installed_version >= 17.0.1.2.5`.
- Neither script touches **nginx (B5)** — the `X-Forwarded-For` / route-prefix changes are a manual operator step.

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
1. `ueipab_enrollment_journey` `state=installed`, `installed_version==17.0.0.14.0`; **`ueipab_sales` `installed_version==17.0.1.2.5`**; model `enrollment.quote.version` exists.
2. Config params set: `akdemia.api_key` (non-empty), `akdemia.base_url`, `min_cache_guardians=50`, `enrollment.report_url` = chosen public URL.
3. `web.base.url` correct + `web.base.url.freeze=True`.
4. **(B5) nginx:** `X-Forwarded-For`/`X-Real-IP` forwarded; `/enrollment-journey` is a **prefix** allow; `/verify-quote` + `/verify-contract` allowed; a POST→303 (e.g. `/confirm`) lands on https with path intact.
5. **(B6) Legal:** counsel sign-off obtained on the e-sig (Cl.10/Cl.11) + anticipo (Cl.11/Cl.12) T&C clauses.
6. Outbound mail proven: a real test S0 email arrived at `gustavo.perdomo@`; quote-sent / accepted / revision-escalation mails route correctly; `soporte@`/`pagos@` + CC addresses monitored.
7. `enrollment.report_url` loads with assets + CTA round-trips to `/enrollment-journey/<token>`.
8. Akdemia import proven on a real pilot family (correct vat↔cédula match + next-grade roll; no `akdemia.api_key` UserError).
9. **Quote lifecycle proven:** S0 'Sí' → draft auto-quote (no customer mail leak); download 404 before send / 200 after; **accept records real IP (≠127.0.0.1)** + UTC + SHA-256 + T&C; revision escalates to soporte@/pagos@; re-issue keeps same token+QR.
10. Contract prints `CSE-2627-0001` + QR; `/verify-contract/<token>` resolves on prod; both PDFs carry the new clauses.
11. Decline S0 → `enrollment.withdrawal` auto-created + internal notice to `pagos@` with working backend link.
12. Full pilot GREEN with **zero real-parent emails** (pilot contact = `gustavo.perdomo@`); `ai_agent.dry_run` at intended state; 5° Año inclusion decided.

## 11. Smoke test (pilot ONE family, contact = gustavo.perdomo@)
0. Create one `enrollment.journey` for a real family whose `partner.vat` is a valid Akdemia guardian cédula; note id/token.
1. Open `/enrollment-journey/<token>` → 9-step timeline renders with correct students/grades.
2. Import button → preview wizard lists real Akdemia students (vat↔cédula).
3. Confirm → student lines created (next-year grades, no dupes).
4. Send S0 (to gustavo.perdomo@) → click CONFIRM → gate flips; **auto-quote draft `sale.order` created** (correct llamado/price/count, no customer mail).
5. Staff **"Enviar cotización"** → parent page shows download + Acepto/Solicitar revisión; `…/cotizacion.pdf` now 200 (was 404 pre-send).
6. Click **Acepto** (tick T&C) → `enrollment.quote.version` accepted with **real client IP**, UTC ts, SHA-256, `tyc_accepted`; step 1 auto-done. (Optionally test **Solicitar revisión** → soporte@/pagos@ escalation → **Re-emitir** v2, same token+QR.)
7. Print contract → `CSE-2627-0001` + QR on all pages → `/verify-contract/<token>` resolves on prod; Acuerdo carries Cl.10/Cl.11, contract carries Cl.11/Cl.12.
8. Second pilot → click DECLINE → `enrollment.withdrawal` auto-created + internal notice to `pagos@` with backend link.
9. Open `enrollment.report_url?j=<journey>` → loads with assets → CTA routes back to the journey.

## 12. Rollback (ordered)
1. Halt any in-flight blast.
2. Restore `…/ueipab17_addon_backups/ueipab_enrollment_journey.bak-<TS>` (or **uninstall** if fresh install — clean, only `ueipab_sales` depends-on-it the other way).
3. Delete config params (`akdemia.*`, `enrollment.report_url`); leave `web.base.url`.
4. Revert nginx alias / repoint report URL (skip if using the dev-hosted page).
5. DB restore only if data beyond the pilot was created (prefer surgical delete of pilot journeys/withdrawals).
6. `docker restart ueipab17`; wait for boot.
7. Verify via XML-RPC: module uninstalled (or prior version) + removed params return empty.

## Appendix A — ENV DELTA (testing vs production, probed 2026-06-26)

Live read-only probe of both environments (testing via dev-container `odoo shell`; prod via XML-RPC, no writes). Snapshot of the enrollment stack as it stood the day before any prod deploy.

### A.1 Module / code layer

| Item | Testing (`testing`) | Production (`DB_UEIPAB`) | Verdict |
|---|---|---|---|
| `ueipab_enrollment_journey` | ✅ installed **17.0.0.14.0** | ❌ **not installed** (absent) | Not deployed — expected, testing-only |
| `enrollment.journey` | ✅ present (9-step, 60+ fields) | ❌ absent | gap |
| `enrollment.journey.student` | ✅ incl. `source`, `staff_edited` | ❌ absent | gap |
| `enrollment.withdrawal` | ✅ 5-step egreso | ❌ absent | gap |
| `enrollment.student.import.preview` | ✅ diff-preview wizard | ❌ absent | gap |
| `enrollment.quote.version` *(new v0.13.0)* | ✅ immutable quote audit log (frozen PDF + SHA-256 + accept IP/UTC/T&C) | ❌ absent | gap |
| `ueipab_sales` (dependency) | **17.0.1.2.5** *(was 1.2.2 at probe 2026-06-26; +1.2.3/.4/.5 since)* | **17.0.1.2.1** | ⚠️ **prod 4 patches behind** |
| `ueipab_ai_agent` | 17.0.1.59.8 | 17.0.1.59.8 | ✅ in sync |

⚠️ **`ueipab_sales` drift is enrollment-relevant.** Prod (1.2.1) is missing: the **QR verification seal on all PDF pages** (1.2.2), the **Acuerdo title change** (1.2.3), and the **e-signature Cl.10 + anticipo Cl.11 T&C clauses** (1.2.4/1.2.5). The enrollment contract PDF shares the QR-seal path **and** the Acuerdo PDF the enrollment quote renders is produced by `ueipab_sales`. → **bump prod `ueipab_sales` to 1.2.5 before/with the enrollment deploy**, else the contract QR may not render on all pages and the quote will lack the new legal clauses.

> **Note:** the table below was probed **2026-06-26** (pre-v0.13.x). The module/code rows above are refreshed to **2026-06-28**; the config/report rows (A.2–A.3) were not re-probed and remain as of 2026-06-26 — re-verify at deploy time.

### A.2 Config / params layer

| Param | Testing | Production | Note |
|---|---|---|---|
| `akdemia.api_key` | ❌ not set | ❌ not set | even testing relies on cron's own key — param-read import path would `UserError` |
| `akdemia.base_url` | ❌ not set (code default) | ❌ not set | code default `api-staging` |
| `akdemia.min_cache_guardians` | ❌ not set (default 50) | ❌ not set | code default fine |
| `akdemia.students_json` (cron cache) | ✅ **322 guardians** | ✅ **322 guardians** | ✅ cron already publishes to **both** envs |
| `enrollment.report_url` | ❌ not set | ❌ not set | falls back to dev URL (B1) |
| `web.base.url` | `http://dev.ueipab.edu.ve:8019` | `https://odoo.ueipab.edu.ve` | correct per env |

- The Akdemia student cache (`akdemia.students_json`, **322 guardians**) is **already syncing into prod** — the data backbone is live in prod even though the module isn't. Eases the deploy (B4 partially satisfied).
- `akdemia.api_key` is **unset in testing too** — confirm whether testing's import runs off the cron-published cache (`use_cache`) vs a live fetch before relying on a live-fetch path in the prod pilot.

### A.3 Annual report layer

| Item | Status |
|---|---|
| Report page | `web/reporte-anual-2025-2026/index.html` (34 KB) |
| Hosted on | **dev only** — `https://dev.ueipab.edu.ve/reporte-anual-2025-2026/` → **HTTP 200** ✅ |
| CEO photo | `/var/www/dev/flyers/ceo-profile-pic.jpeg` (188 KB) ✅ |
| Prod host | ❌ not served from a prod host; `enrollment.report_url` unset both envs |

Static page, **live on dev today**, not on a prod host → this is the **B1** decision (dev-interim vs move to prod).

### A.4 Reconcile-before-deploy (refreshed 2026-06-28)
1. Bump prod **`ueipab_sales` 1.2.1 → 1.2.5** (QR seal + Acuerdo title + e-sig Cl.10 + anticipo Cl.11). Upgrade with `-u` **before** the enrollment install.
2. Install **`ueipab_enrollment_journey` 0.13.2** (`-i`, first install) — brings the `enrollment.quote.version` model + quote lifecycle + Contrato Cl.11/Cl.12.
3. Set **`akdemia.api_key`** in prod (+ confirm testing import is live vs cache-only).
4. Decide **B1** report host (dev-interim vs prod).
5. **(B5) nginx** — add `X-Forwarded-For`/`X-Real-IP`; `/enrollment-journey` prefix allow + `/verify-quote` + `/verify-contract`.
6. **(B6) Legal** — counsel sign-off on the T&C clauses before any parent-facing send.

**Already aligned in prod:** `ai_agent` 59.8 · 322-guardian Akdemia cache · `web.base.url`. **Prod is clean** — no enrollment models, no demo residue, no half-deploy.

---

## 13. Deployment log — 2026-06-29 (EXECUTED)

Executed via a 6-agent read-only recon (nginx/report/cron/modules/params/legal) followed by sequential prod mutations, each with a verification gate.

| Step | Action | Result |
|------|--------|--------|
| B2a / B6 | scp + `docker exec … odoo -u ueipab_sales` | `ueipab_sales` **17.0.1.2.5** installed (exit 0, XML-RPC verified) — carries QR seal + Acuerdo title + e-sig Cl.10 + anticipo Cl.11 into live PDFs |
| B2b | `deploy_enrollment_journey_prod.sh -i` (piped `DEPLOY`) | `ueipab_enrollment_journey` **17.0.0.14.0** installed (exit 0, verified); models `enrollment.{journey,journey.student,withdrawal,quote.version,student.import.preview}` present; group + contract sequence present; 1 mail server; **0 journeys** |
| B3 | `prod_post_deploy_enrollment_journey.py` path + XML-RPC | `akdemia.api_key`, `akdemia.base_url=api-staging`, `akdemia.min_cache_guardians=50`, `enrollment.report_url=https://odoo.ueipab.edu.ve/reporte-anual-2025-2026/`, **`web.base.url.freeze=True`** |
| B1 | copy report + 16 assets to prod webroot; URLs rewritten dev→odoo; nginx alias before `/mora-policy/` | report **HTTP 200** (correct title), `/flyers/ceo-profile-pic.jpeg` **200**, partner logo **200**; `nginx -t` clean + reload |
| B5 | (verify only — **no proxy change**) | XFF/X-Real-IP + `Host $http_host` already set; no whitelist; `/enrollment-journey`, `/verify-quote`, `/verify-contract` all reach Odoo (404 on fake token = routed) |
| B4 | `/opt/akdemia/{scripts/akdemia_api_sync.py,scripts/akdemia_cache_refresh.sh}` + `/etc/akdemia_env_prod` (600) + `/etc/cron.d/akdemia_cache_refresh` (06:30 VET) | cache-only (`--skip-odoo --skip-sheets`); prod has system `requests`+`dotenv` (no venv); **test run published 322 guardians** |

**Rollback artifacts (prod):** `…/ueipab17_addon_backups/ueipab_sales.bak-20260629_064613`, `ueipab_enrollment_journey.bak-20260629_064804`; nginx `…/odoo.ueipab.edu.ve.bak-20260629_065323`.

**Still open after deploy:**
- **B6 legal counsel sign-off** — required before any parent-facing send (clauses are live in PDFs; nothing auto-sends to parents).
- **Pilot** — deferred to manual UI validation. NB: the integration user (uid=2) lacks `group_enrollment_support`, so script-driven enrollment writes require granting that group (or a superuser shell) — a deliberate, separate authorization.
- **Restore Roberto Vera's testing email/mobile** in `testing` after S0 testing (originals: `yamelsancheztellechesa@gmail.com` / `+58 414 0832852`).

### 13.1 Dedicated sender `inscripcion@` (v0.15.0, 2026-06-29)

To keep the S0 blast (and the whole funnel) **out of the soporte@ support queue**, `ueipab_enrollment_journey` **0.15.0** makes the sender addresses config-driven (`_enroll_addr()` ← `ir.config_parameter`). Deploy 0.15.0 (scp + `-u`), then wire prod with **`scripts/wire_enrollment_inscripcion.py --live`** (SMTP app password via env `INSCRIPCION_SMTP_PASS`):
- params `enrollment.notify_from` = `Colegio Andrés Bello - Inscripción <inscripcion@ueipab.edu.ve>`, `enrollment.reply_to` / `enrollment.contact` / `enrollment.escalation_to` = `inscripcion@ueipab.edu.ve` (leave `internal_to`→pagos@ and `blast_cc`→'' = no CC at their code defaults);
- a dedicated `ir.mail_server` (smtp.gmail.com:587 STARTTLS, user `inscripcion@`, `from_filter=inscripcion@`) so only enrollment mail uses it, no From rewrite.

✅ **DONE in prod 2026-06-29:** enrollment 0.15.0 deployed (`-u`), `wire_enrollment_inscripcion.py --live` set the params + created `ir.mail_server` id=2, and a prod send-test From the new sender → `gustavo.perdomo@` arrived (`state=sent`). Also verified in testing. **Optional:** add `inscripcion@` as a Freescout admissions mailbox for reply triage. Still gated by **B6** before any real parent blast.
