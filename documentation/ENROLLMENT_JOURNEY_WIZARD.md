# Enrollment Journey Wizard — 2026-2027 Academic Period

**Status:** IN PROGRESS | **Created:** 2026-06-12 | **Updated:** 2026-06-15 (v0.4.2) | **Owner:** Gustavo Perdomo
**Style reference:** https://odoo.ueipab.edu.ve/mora-policy/ (`/var/www/mora/index.html` — Poppins, navy `#1a2c5b` / gold `#f0c400` / teal palette, `.timeline` vertical component)

---

## 1. Concept

A customer-facing **web timeline page** where each parent (Representante) can see, in real time, where their family stands in the 2026-2027 enrollment process — and what comes next. Internally it is a **macro follow-up wizard**: each of the 9 steps is *cleared* by the responsible team (hybrid: manual clearance by Customer Support + soft automatic green validations where Odoo/Google data can confirm it), and the customer's page reflects progress instantly.

**Glenda is always present** on the page as a floating AI assistant bubble — one click away for any question about the enrollment process.

```
Parent opens /enrollment-journey/<token>
┌──────────────────────────────────────────────────────┐
│  🏫 Proceso de Inscripción 2026-2027                  │
│  Familia: PEREZ — 2 estudiantes                       │
│                                                      │
│  🏛️ INSCRIPCIÓN FORMAL                                │
│  ✅ 1. Cotización confirmada                          │
│  ✅ 2. Acuerdo de Inscripción firmado                 │
│  📋 3. Contrato Educativo firmado (en custodia)       │
│                                                      │
│  💻 ACTIVACIÓN DE PLATAFORMAS                         │
│  ✅ 4. Registro Akdemia completo                      │
│  🔵 5. Cuenta Dawere habilitada     ← estás aquí      │
│  ⚪ 6. Cuenta @ueipab.edu.ve actualizada              │
│  ⚪ 7. Google Classroom                               │
│                                                      │
│  📁 CIERRE ADMINISTRATIVO                             │
│  ⚪ 8. Guía de Inglés entregada                       │
│  ⚪ 9. Expediente físico actualizado                  │
│                                                      │
│                          [🤖 Glenda — pregúntame]    │
└──────────────────────────────────────────────────────┘
```

**Hard gate:** Steps 4-9 cannot be marked done while any Block 1 step (1-3) is incomplete — `UserError` raised.

---

## 2. The 9 Steps — owners, soft checks, clearance rules

### Block 1 — Inscripción Formal (support, single enrollment visit)

| # | Step (customer-facing label) | Cleared by | Soft auto-validation | Manual clearance |
|---|------------------------------|-----------|----------------------|------------------|
| 1 | **Cotización confirmada** | Auto | `sale.order.state == 'sale'` | Override allowed |
| 2 | **Acuerdo de Inscripción firmado** | Support | None (portal signature OFF) | ✅ Support confirms signed Acuerdo PDF received |
| 3 | **Contrato Educativo firmado** | Support | Auto-release: all order invoices `amount_residual==0` | ✅ Support confirms signed contract on file; contract retained until payment plan complete |

### Block 2 — Activación de Plataformas (IT + academic, 1-3 weeks after visit)

| # | Step (customer-facing label) | Cleared by | Soft auto-validation | Manual clearance |
|---|------------------------------|-----------|----------------------|------------------|
| 4 | **Registro Akdemia completo** | Support | Future: akdemia_scraper cross-check | ✅ Support confirms in Akdemia |
| 5 | **Cuenta Dawere habilitada** | IT | None | ✅ IT provisions account, sends credentials |
| 6 | **Cuenta @ueipab.edu.ve actualizada** | IT | `school.student_directory_json` email exists | ✅ IT confirms OU move / new account |
| 7 | **Google Classroom** | IT/Academic | Future: Classroom API roster check | ✅ Academic coordinator confirms |

### Block 3 — Cierre Administrativo (support/admin, within first week)

| # | Step (customer-facing label) | Cleared by | Soft auto-validation | Manual clearance |
|---|------------------------------|-----------|----------------------|------------------|
| 8 | **Guía de Inglés entregada** | Support | None | ✅ Support confirms guide handed to parent |
| 9 | **Expediente físico actualizado** | Admin | None | ✅ Admin confirms physical file complete |

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

- [x] **Phase 0 — Decisions (Gustavo):** ✅ 2026-06-12 — new module ✓; keep Acuerdo PDF ✓; QWeb contract PDF (not Google Docs) ✓; single Enrollment Support group for now ✓; legal snapshot model (draft→signed→amended) ✓
- [x] **Phase 1 — Model + staff UI (testing):** ✅ 2026-06-12 — `ueipab_enrollment_journey` v0.2.0 installed in testing. `enrollment.journey` + `enrollment.journey.student` (name/cédula/grade/institutional_email/insurance_policy). Backend: Sales → "Inscripción 2026-2027" list+form, ✅ Completar / ↩️ Reabrir buttons per step with audit (cleared_by/cleared_at), 🔄 Validaciones + 🌐 Ver página + 🖨️ Imprimir buttons in header.
- [x] **Phase 3 — Customer page:** ✅ 2026-06-12 — `/enrollment-journey/<token>` (auth=public) mora-policy-styled: hero, animated progress bar, vertical timeline (green/pulsing blue/grey/amber states), student chips, Glenda FAB. Mobile-first. Live: http://dev.ueipab.edu.ve:8019/enrollment-journey/4f3c497f-7a41-428a-8896-b42fa224988f
- [x] **Phase 4 — Glenda bubble:** ✅ 2026-06-12 — floating 🤖 FAB → slide-up card → Telegram deep link `t.me/GlendaUeipabBot?start=ENROLL_<token[:8]>`. Phase 1 complete; Glenda ENROLL_ handler + journey context injection = Phase 4b (pending).
- [x] **Phase 5 — Step 6 contract (QWeb PDF):** ✅ 2026-06-13 → **v0.4.1 2026-06-15** — 2-page "Contrato Servicio Educativo Privado - Orden de Servicio" QWeb PDF bound to `enrollment.journey`. Page 1: institution + representante + Section C (students + insurance merged: name/cédula/grade/póliza) + Section E (ceiling summary: $218,88 × N students × 13 payments = max obligation) + Section F (early payment benefit + **QR code**) + dual signatures. Page 2: full 10-clause T&C (Cláusula 4 Plazo de Pago: "pagarse" — corrected 2026-06-15). Auto-sequence `CSE-2627-XXXX` on first print.
  - **QR verification (v0.4.1 → v0.4.2):** QR code anchored at **bottom-right** of page 1 alongside signature row (approved layout 2026-06-15). Links to `/verify-contract/<token>` — public route returns branded "✅ DOCUMENTO VÁLIDO" page: contract number, representante name, date, student list. Invalid/unknown token → 404. Generated in Python report class using `qrcode` lib; URL from `web.base.url` → auto-correct in prod. Sections E + F are full-width; QR is 4th column in signature table.
  - **v0.4.3 — QR seal on page 2 T&C (2026-06-15):** Same QR also rendered at **bottom-right of page 2** T&C signature row (66pt). Both contract pages carry the verification seal.
- [x] **Phase 5b — Contract escrow workflow (Option B):** ✅ 2026-06-13 — `contract_retained` (Boolean) + `contract_released_date` (Date) on `enrollment.journey`. Step 3 clear → auto `contract_retained=True`. Staff "📋 Liberar contrato" button → manual release. Soft-check hook: all `order_id.invoice_ids` `amount_residual==0` → auto-release. Customer page: retained → amber 📋 "en custodia" card; released → green ✓ + 🎉 celebration.
- [x] **v0.4.0 — 9-step 3-block workflow:** ✅ 2026-06-13 — Restructured from 6 → 9 steps in 3 blocks. `BLOCK_DEFS` + `BLOCK1_STEPS` constants added. Hard gate prevents Block 2/3 clearance until Block 1 complete. Customer page renders block section headers. Contract escrow moved to step 3 (enrollment visit, not end). New steps 5 (Dawere), 8 (Guía Inglés), 9 (Expediente). DB verified: 27 step columns. Demo journey (id=1) reset: Block 1 done + retained, step 4 done, steps 5-9 pending (44%). **Visually verified 2026-06-13:** 3 block headers render correctly; step 3 amber "en custodia" card with left-border callout; step 5 pulsing blue ESTÁS AQUÍ; progress 44% paso 5 de 9.
- [ ] **Phase 2 — Soft checks engine:** step 1 wired (order.state='sale' → done_auto). Steps 6 (directory JSON) + step 3 contract-release cron = pending.
- [ ] **Phase 4b — Glenda ENROLL_ handler:** `_handle_telegram_start(ENROLL_<token>)` → inject journey step context into prompt so Glenda answers "¿qué me falta?" precisely.
- [ ] **Phase 1b — Student import:** "📥 Importar estudiantes" button — publish `school.akdemia_students_json` param (extend existing `akdemia_api_sync.py` cron), match partner VAT → guardian cédula, auto-fill student lines + grade auto-promote (+1 for 2026-2027). Staff editable before signing.
- [ ] **Phase 6 — Comms:** journey link in quote-confirmation message (Glenda/email); optional step-completion push notifications.
- [ ] **Phase 7 — Prod deploy + runbook**

### Phase-0 Architecture decisions (locked)
| Question | Decision |
|---|---|
| Module home | New `ueipab_enrollment_journey` (depends ueipab_sales) |
| Step 2 signature | Manual (staff confirms signed Acuerdo PDF received) |
| Step 6 contract | QWeb 2-page PDF bound to `enrollment.journey` (not Google Docs) |
| Clearance roles | Single `group_enrollment_support` for now |
| Contract model | Snapshot: draft → signed → amended (never overwrite signed lines) |
| Student data | One-shot import from Akdemia cached param; no sync cron against imported rows |
| Insurance policy | Manual field (Seguros Caracas hasn't issued 2026-2027 policies yet) |

---

## 6. Open questions (Phase 0) — STATUS: RESOLVED ✅

All Phase-0 decisions locked 2026-06-12/13. See Phase-0 Architecture decisions table in §5.

**Still open (next discussions):**
- **Journey creation trigger:** auto on every confirmed 2026-2027 enrollment order, or manually by support for committed families only?
- **Clearance role split (future):** once volume grows, split Support (steps 2-3) / IT (4-5) / Finance (6) into separate groups?
- **Notifications (Phase 6):** push notification per step completion via Telegram/email, or page-only pull?

---

## 7. Risks / notes

- **WA paused** (dry_run=True since 2026-05-22): bubble shows Telegram only until Massiva primary restored.
- **Akdemia has no API** — Step 3 soft check depends on the daily scraper; treat as advisory, manual clearance is authoritative.
- **odoo_api_bridge contract code is 2025-2026 era** (MariaDB customer_matches) — do not reuse data layer blindly; only the Google Docs template-copy mechanism is salvageable as-is.
- **Token security:** journey page exposes student names/grades — token must be long/random (reuse notice-ack generator); no enumeration; no financial amounts on the page beyond step status (amounts live in the Acuerdo PDF).
