# Enrollment Journey Wizard — 2026-2027 Academic Period

**Status:** DESIGN (analysis phase) | **Created:** 2026-06-12 | **Owner:** Gustavo Perdomo
**Style reference:** https://odoo.ueipab.edu.ve/mora-policy/ (`/var/www/mora/index.html` — Poppins, navy `#1a2c5b` / gold `#f0c400` / teal palette, `.timeline` vertical component)

---

## 1. Concept

A customer-facing **web timeline page** where each parent (Representante) can see, in real time, where their family stands in the 2026-2027 enrollment process — and what comes next. Internally it is a **macro follow-up wizard**: each of the 6 steps is *cleared* by the responsible team (hybrid: manual clearance by Customer Support + soft automatic green validations where Odoo/Google data can confirm it), and the customer's page reflects progress instantly.

**Glenda is always present** on the page as a floating AI assistant bubble — one click away for any question about the enrollment process.

```
Parent opens /enrollment-journey/<token>
┌──────────────────────────────────────────────┐
│  🏫 Proceso de Inscripción 2026-2027          │
│  Familia: PEREZ — 2 estudiantes               │
│                                              │
│  ✅ 1. Cotización confirmada                  │
│  ✅ 2. Acuerdo firmado                        │
│  🔵 3. Registro Akdemia          ← estás aquí │
│  ⚪ 4. Cuenta de correo @ueipab               │
│  ⚪ 5. Google Classroom                       │
│  ⚪ 6. Contrato educativo final               │
│                                              │
│                      [🤖 Glenda — pregúntame] │
└──────────────────────────────────────────────┘
```

---

## 2. The 6 Steps — owners, soft checks, clearance rules

| # | Step (customer-facing label) | Cleared by | Soft auto-validation (green check source) | Manual clearance |
|---|------------------------------|-----------|--------------------------------------------|------------------|
| 1 | **Cotización confirmada** — Sales order confirmed | Auto | `sale.order.state == 'sale'` (the family's enrollment quote, `ueipab_sales` engine) | Override allowed |
| 2 | **Acuerdo de Inscripción firmado** — customer signs off the quotation | Support | Phase 1: portal signature is OFF (`require_signature=False`, read-only portal). Soft check available later via `sale.order.signed_on` if we enable Odoo portal signature. Today the artifact = printed/PDF Acuerdo v1.2.1 with initials on the T&C annex | ✅ Support confirms signed Acuerdo received (upload scan optional) |
| 3 | **Registro Akdemia completo** — parent finished all Akdemia platform steps | Support | Future: akdemia_scraper cross-check (student appears active in scraped 2026-2027 data) | ✅ Support confirms after verifying in Akdemia |
| 4 | **Cuenta de correo @ueipab.edu.ve** — Google account updated to correct OU, or new account created | IT/Support | `school.student_directory_json` (sync_google_directory.py, 224 accts, cron 07:00 VET): student email exists → green. OU correctness = manual | ✅ IT confirms OU move / new account |
| 5 | **Google Classroom** — student enrolled per grade/class (each teacher has own Classroom) | IT/Academic | Future: Google Classroom API roster check per course. Phase 1: none | ✅ Academic coordinator confirms |
| 6 | **Contrato educativo final firmado** — signed once the quotation payment schedule is fully paid | Finance/Support | Payment plan invoices all paid: every posted `account.move` linked to the order has `amount_residual == 0` AND no remaining unposted tranche → green "payment complete". Contract doc generated via odoo_api_bridge | ✅ Support confirms signed contract on file |

**Step-state model (per step):** `pending` ⚪ → `in_progress` 🔵 → `done_auto` ✅ (soft check passed) / `done_manual` ✅ (cleared by staff) / `blocked` 🔴 (with reason shown to customer in soft language).

**Rule:** soft checks paint the green light, but a staff member can always override (force-clear or re-open). The customer page never shows internal notes — only friendly status + "next step" guidance.

---

## 3. Existing assets discovered (analysis 2026-06-12)

### 3.1 mora-policy page (style donor)
- Static HTML at `/var/www/mora/index.html` on **prod** (copy in `/var/www/dev/mora/`), served by nginx:
  `location /mora-policy/ { alias /var/www/mora/; try_files $uri $uri/ /mora-policy/index.html; }` in `/etc/nginx/sites-available/odoo.ueipab.edu.ve` (line 51).
- Self-contained CSS: Poppins font, CSS vars (`--navy #1a2c5b`, `--gold #f0c400`, `--teal #1fb8c0`, `--light #f0f4fa`), sticky navbar with circular logo, hero with SVG pattern, **`.timeline` vertical component (line ~170 / markup ~418)** — exactly the visual language to reuse.

### 3.2 Final educational contract (Step 6) — odoo_api_bridge
Explored `/var/www/dev/odoo_api_bridge/` (note: underscore, not hyphen):
- **`create_multiple_contracts.py`** — copies Google Docs template **`1LuML0ud3R8t5n4paVc6OLlv-LiZ9-_7LtoYoZWHwPGo`** once per student via Drive API (service account creds `/var/www/dev/bcv/credentials.json`, domain `pagos@ueipab.edu.ve`), fills placeholders, stores `google_doc_id`/`google_doc_url` + `template_id` + `academic_year` in MariaDB `payroll_db` (`customer_matches`/`customer_students` + contracts table).
- **`enhanced_contract_generator.py`** — enriched data layer: profession + marital status from Akdemia sheets, dynamic pricing by payment date, academic-period display (`2526` → `2025-2026`). Uses `customer_contract_data` view.
- Supporting: `update_existing_google_docs.py`, `fresh_google_docs_regeneration.py`, `reset_customer_contracts.py`.
- ⚠️ Built for 2025-2026 with MariaDB customer matching. For 2026-2027 the source of truth is the **Odoo sale.order** (quote engine) — contract generation should be re-pointed at Odoo partner/order data, keeping the Google Docs template-copy mechanism. Template content itself needs review/refresh for 2026-2027 (new rates, T&C alignment with Acuerdo v1.2.1 annex).

### 3.3 Reusable Odoo patterns (this repo)
- **Token public pages:** `/notice-ack/<token>`, `/ari-guide/<token>`, `/attendance-fix/<token>` — same `auth='public'` + per-partner token pattern → `/enrollment-journey/<token>`.
- **Quote engine:** `ueipab_sales` v1.2.1 — `sale.order` already carries family, students count, llamado, payment plan; Acuerdo PDF with T&C annex.
- **Google directory cache:** `school.student_directory_json` (Step 4 soft check) — already synced daily.
- **Payment plan:** "Generar Plan de Pagos" creates draft invoices; posted ones carry `amount_residual` (Step 6 soft check).
- **Glenda:** Telegram `@GlendaUeipabBot` (deep links `t.me/GlendaUeipabBot?start=...`), WA (paused), identity ring for unknown contacts.

---

## 4. Architecture (recommended)

**Option A — Odoo module page (RECOMMENDED):** new model + public controller inside `ueipab_sales` (or small `ueipab_enrollment_journey` module).
- Customer page: `/enrollment-journey/<token>` (`auth='public'`), rendered with mora-policy-style self-contained HTML (no website module dependency — same approach as `/ari-guide`).
- Staff UI: Odoo backend list/kanban — one record per family/order, 6 step columns, one-click clear buttons with audit trail (who/when).
- Soft checks: computed fields refreshed by a 15-min cron + on-demand recompute button.
- Why: state lives where the data lives (sale.order, invoices, partner), staff already work in Odoo, token infra exists, zero new servers.

**Option B — static page + odoo_api_bridge Flask API:** rejected — splits state across MariaDB+Odoo, duplicates auth, support team would need a second UI.

### 4.1 Data model sketch

```
enrollment.journey
  partner_id        m2o res.partner (Representante)   required
  order_id          m2o sale.order (enrollment quote)
  access_token      char (indexed, like notice-ack)
  academic_year     char default '2026-2027'
  step1_state..step6_state   selection(pending/in_progress/done_auto/done_manual/blocked)
  step{N}_cleared_by   m2o res.users   step{N}_cleared_at  datetime
  step{N}_note      char (internal)
  current_step      computed int (first non-done)
  progress_pct      computed
enrollment.journey.log   (audit: journey_id, step, old→new, user, ts)
```

### 4.2 Page composition (customer view)
1. Navbar + hero (mora-policy clone, "Inscripción 2026-2027" badge).
2. Greeting card: family name, students (names + grades from order lines), llamado/promo deadline.
3. **Vertical timeline** — 6 nodes; done = green check + date; current = pulsing blue "estás aquí" + clear instructions for what *the parent* must do (e.g. Step 3: Akdemia link + steps); pending = grey; blocked = soft amber message "estamos procesando…".
4. Per-step action links where relevant: Acuerdo PDF download (2), Akdemia portal (3), Akdemia password reset (3), student email shown (4), contract doc link when ready (6).
5. Footer: pagos@ / soporte@ contacts.

### 4.3 Glenda floating bubble (always visible)
- **Phase 1 (zero new backend):** fixed-position round avatar bottom-right on every journey page. Click → slide-up card: "Hola, soy Glenda 🤖 — pregúntame sobre tu inscripción" with two buttons: **Telegram** deep link `t.me/GlendaUeipabBot?start=ENROLL_<token>` and **WhatsApp** `wa.me/<active number>` (auto-hidden while WA is paused / dry_run). The `ENROLL_` start payload lets Glenda auto-identify the partner AND know they came from the journey page → prompt context: answer enrollment-wizard questions, knows their current step.
- **Phase 2 (optional):** true embedded webchat (new `web` channel on `ai.agent.conversation`) — significant work; only if Telegram/WA bridge proves insufficient.
- New Glenda capability either way: `_get_enrollment_journey_context()` — inject the family's 6-step status into the prompt so Glenda answers "¿qué me falta?" precisely; possible `ACTION:JOURNEY_STATUS` for WA/Telegram users without the page open.

---

## 5. Implementation phases (tracking checklist)

- [ ] **Phase 0 — Decisions (Gustavo):** see §6 open questions
- [ ] **Phase 1 — Model + staff UI (testing):** `enrollment.journey` + log, auto-create on quote confirm, backend kanban/list with clear/re-open buttons, security groups (Support clears 2-4, IT 4-5, Finance 6 — or single support group?)
- [ ] **Phase 2 — Soft checks engine:** step 1 (order state), step 4 (directory JSON lookup), step 6 (payment-plan residuals); cron + recompute button
- [ ] **Phase 3 — Customer page:** `/enrollment-journey/<token>` mora-policy-styled timeline; mobile-first (parents open from WA/Telegram)
- [ ] **Phase 4 — Glenda bubble + context:** floating avatar + deep links; `ENROLL_` start handler; journey context block in prompt
- [ ] **Phase 5 — Step 6 contract refresh:** review Google Docs template `1LuML0ud…` content for 2026-2027; re-point generator at Odoo order data (or rebuild as QWeb PDF like the Acuerdo — decision)
- [ ] **Phase 6 — Comms:** journey link delivered in quote-confirmation message (Glenda channels) + email; optional step-completion notifications
- [ ] **Phase 7 — Prod deploy + runbook**

---

## 6. Open questions (Phase 0)

1. **Module home:** extend `ueipab_sales` vs new `ueipab_enrollment_journey`? (Recommend new module — different lifecycle, depends on ueipab_sales.)
2. **Step 2 signature:** keep manual (signed paper/PDF Acuerdo) or enable Odoo portal signature (`require_signature=True`) for a fully digital sign-off? Portal signature would make Step 2 a soft check too.
3. **Step 6 contract:** keep Google Docs copy mechanism (odoo_api_bridge) or rebuild as Odoo QWeb PDF (same pattern as Acuerdo — versionable, no MariaDB dependency)?
4. **Clearance roles:** one "Enrollment Support" group clears everything, or per-step role split (Support/IT/Academic/Finance)?
5. **Journey creation trigger:** auto on every confirmed 2026-2027 enrollment order, or manually by support for committed families only?
6. **Notifications:** notify parent on each step completion (Telegram/email) or page-only (pull, no push)?
7. **URL & hosting:** serve from Odoo prod (`odoo.ueipab.edu.ve/enrollment-journey/<token>`) — confirm; nginx already proxies Odoo so no new vhost needed.

---

## 7. Risks / notes

- **WA paused** (dry_run=True since 2026-05-22): bubble shows Telegram only until Massiva primary restored.
- **Akdemia has no API** — Step 3 soft check depends on the daily scraper; treat as advisory, manual clearance is authoritative.
- **odoo_api_bridge contract code is 2025-2026 era** (MariaDB customer_matches) — do not reuse data layer blindly; only the Google Docs template-copy mechanism is salvageable as-is.
- **Token security:** journey page exposes student names/grades — token must be long/random (reuse notice-ack generator); no enumeration; no financial amounts on the page beyond step status (amounts live in the Acuerdo PDF).
