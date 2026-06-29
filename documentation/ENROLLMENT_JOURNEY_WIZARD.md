# Enrollment Journey Wizard — 2026-2027 Academic Period

**Status:** IN PROGRESS | **Created:** 2026-06-12 | **Updated:** 2026-06-19 (Step 0 design) | **Owner:** Gustavo Perdomo
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

---

## 4b. Step 0 — Continuidad Confirmation Gate (designed 2026-06-19)

### Concept

Before showing the 9-step wizard, the parent must answer whether their student(s) will continue at UEIPAB for 2026-2027. This is the **zero step** — a pre-qualification gate that the parent activates by opening their personal link for the first time.

**The URL `/enrollment-journey/<token>` routes to 3 different pages depending on `continuation_status`:**

| `continuation_status` | Page shown |
|---|---|
| `pending` (default) | Step 0 confirmation page |
| `confirmed` | Existing 9-step wizard |
| `declined` | Farewell/decline confirmation page (read-only) |

### Step 0 page — "Sí / No" confirmation

**Text displayed (Spanish):**

> Estimado Representante, usted ha recibido su vínculo para invocar y dar inicio al proceso virtual asistido en referencia a la inscripción de su(s) representado(s) en nuestra institución. Para comenzar dicho proceso, primero que nada necesitamos saber y nos confirme si su(s) hijo(s):
>
> • **[Nombre Estudiante 1]** · [Grado Actual → Grado Siguiente]
> • **[Nombre Estudiante 2]** · [Grado Actual → Grado Siguiente]
>
> ¿van a continuar con nosotros el próximo año escolar 2026-2027?

Two buttons: **[ Sí, continuamos ✓ ]** and **[ No, no continuaremos ]**

**Grade progression formula:** `_next_grade(grade)` — regex extracts leading digit, increments by 1. Example: "3° Grado" → "4° Grado", "2° Año" → "3° Año". Edge case: graduating 5° Año students produce "6° Año" (non-existent) — confirm with Gustavo whether graduating seniors are included in this wizard.

**Student data prerequisite (critical):** Step 0 can only show student names if `student_ids` is populated. If the link is opened before Phase 1b (student import) has run, show a holding screen: *"Estamos preparando la información de tu familia, vuelve en breve."* Staff **must import students before sharing the link.**

### YES flow

`POST /enrollment-journey/<token>/confirm` → `continuation_status='confirmed'` + `confirmation_date=now()` → `302` redirect to GET → controller branches to 9-step wizard. No other action required.

### NO flow — inline expand (two-stage UX)

Clicking **"No"** does **NOT** immediately POST. JavaScript expands an inline section below the buttons showing:

**Farewell message:**

> Estimado Representante, ha sido un honor haber prestado los servicios educativos para su(s) representado(s) este año escolar 2025-2026 y los vamos a extrañar mucho en nuestra institución, independientemente de la razón por la cual lo llevó a usted a no seguir con nosotros. En este sentido, nos gustaría que nos comentara la razón de no continuidad:
>
> [textarea — libre, sin límite de caracteres]
>
> Finalmente le recordamos que para formalizar el retiro usted debe contar con la solvencia administrativa correspondiente, que se obtiene con el pago total del año escolar 2025-2026 en curso de las dos mensualidades pendientes correspondientes al mes de julio y agosto.
>
> [ Confirmar retiro ]

**Important UX rule:** Clicking **"Sí"** after the NO section has expanded collapses it again — the parent can change their mind before the final submit.

`POST /enrollment-journey/<token>/decline` → `continuation_status='declined'` + `decline_reason=<textarea>` + `decline_date=now()` → staff notification → `302` redirect to GET → controller shows decline confirmation (read-only, no textarea).

### Staff notification on decline (immediate)

When a parent POSTs a decline:
1. `message_post()` chatter note on the `enrollment.journey` record (visible in backend to all users with access)
2. Email to `pagos@ueipab.edu.ve` — subject: `[No Continuidad] Familia <partner_name>` — body includes student list + typed reason + timestamp

### Decline confirmation page (read-only)

Shown on any GET with `continuation_status='declined'`. Displays:
- The farewell message (static)
- The parent's recorded reason (read-only, labelled "Tu respuesta registrada el DD/MM/YYYY")
- Contact: *"Si cometiste un error o cambiaste de opinión, contáctanos en pagos@ueipab.edu.ve"*

**No re-edit from the parent side once submitted.** Staff resets via `action_reset_confirmation()` backend button.

### Student list filtering — 5° Año excluded silently

Venezuelan Educational Law (LOPNNA + reglamento) mandates that schools take all necessary remedial measures to ensure every student graduates. A 5° Año student not graduating is an extraordinary legal/administrative exception, not a normal enrollment decision a parent makes via a web form. Therefore:

- **5° Año students are excluded from the Step 0 student list** — the question does not apply to them.
- For a family with a mix of 5° Año + younger students, Step 0 shows only the younger students. The parent's Yes/No covers only them.
- **Mass-create exclusion:** if a family's *only* student(s) are in 5° Año, do not create an `enrollment.journey` for them — they are graduating, not re-enrolling.

**Binary (family-level) Yes/No is correct for V1.** The remaining mixed-family edge case (one sibling leaves voluntarily while another continues) is genuinely rare given the legal context. Staff handles it manually via chatter note if it arises. Per-student checkboxes are a possible V2 enhancement only if volume warrants it.

### New model fields required

```python
continuation_status = fields.Selection([
    ('pending',   'Pendiente de confirmación'),
    ('confirmed', 'Continúa'),
    ('declined',  'No continúa'),
], default='pending', string='Continuidad')
decline_reason   = fields.Text('Motivo de retiro', readonly=True)
confirmation_date = fields.Datetime('Fecha de confirmación', readonly=True)
decline_date      = fields.Datetime('Fecha de retiro', readonly=True)
```

### New controller routes required

| Method | Route | Action |
|---|---|---|
| GET | `/enrollment-journey/<token>` | Branch on `continuation_status` (existing route, new branch logic) |
| POST | `/enrollment-journey/<token>/confirm` | Set confirmed + redirect |
| POST | `/enrollment-journey/<token>/decline` | Set declined + notify staff + redirect |

### S0 Notification Architecture (locked 2026-06-19)

Three distinct moments, all implemented inside `ueipab_enrollment_journey`:

**Moment 1 — Blast email (staff-initiated, campaign launch)**

Staff triggers "📧 Enviar email S0" from the journey list → sends the Step 0 link to each family.

- **TO:** `partner_id.email`
- **CC:** `soporte@ueipab.edu.ve`
- **Reply-To:** `soporte@ueipab.edu.ve`
- Sets `blast_sent_date` on the journey record
- If `partner_id.email` is empty → skip send, set `email_missing=True`, flag visually in UI

**Moment 2 — Response notification (auto, fires on POST /confirm or /decline)**

- **TO:** `soporte@ueipab.edu.ve`
- **CC:** `partner_id.email`
- **Subject (Yes):** `[S0 Confirmada] Familia <name>`
- **Subject (No):** `[S0 No Continúa] Familia <name>`
- **Body (Yes):** family name, student list, timestamp, link to Odoo backend record
- **Body (No):** same + parent's typed decline reason

**Moment 3 — WA escalation (manual, staff-triggered from review UI)**

Staff clicks **"📱 Enviar WA"** on any journey record (always available — not gated behind `email_bounced` flag, staff decides when to escalate).

Phone resolution order:
1. `partner_id.mobile` → use if present
2. `partner_id.phone` → use if present
3. Neither → block send, set `phone_missing=True`, show inline warning in UI

WA message sent via existing MassivaMóvil integration (respects `dry_run` flag). Sets `wa_sent_date` on record.

### New fields on `enrollment.journey`

```python
# Blast tracking
blast_sent_date  = fields.Datetime('Email enviado', readonly=True)
email_missing    = fields.Boolean('Sin email', readonly=True)   # auto-set at blast time
# Response tracking (continuation_date / decline_date already listed above)
# WA escalation
wa_sent_date     = fields.Datetime('WA enviado', readonly=True)
phone_missing    = fields.Boolean('Sin teléfono', readonly=True)  # auto-set at WA trigger
email_bounced    = fields.Boolean('Email rebotado', default=False)  # staff toggles manually
```

### Staff S0 Review UI (new Odoo action within `ueipab_enrollment_journey`)

Dedicated list view — action filters to journeys with `continuation_status=pending` or `email_bounced=True`. Columns:

| Column | Source |
|---|---|
| Familia | `partner_id.name` |
| Estudiantes | count `student_ids` |
| Continuidad | `continuation_status` (color badge: amber/green/red) |
| Email enviado | `blast_sent_date` |
| Respuesta | `confirmation_date` or `decline_date` |
| ⚠ Sin email | `email_missing` flag |
| ⚠ Sin tel. | `phone_missing` flag |
| WA enviado | `wa_sent_date` |

Per-record header buttons: **📧 Reenviar email** · **📱 Enviar WA** · **🌐 Ver página**

### Backend (staff) additions required

- `continuation_status` color-coded badge in list view (amber=pending, green=confirmed, red=declined)
- `decline_reason` + `decline_date` + `confirmation_date` in form view (readonly)
- `action_reset_confirmation()` button — resets to `pending`, clears decline fields (staff only)
- `email_bounced` toggle checkbox in form view (staff marks manually when they see bounce in Freescout)
- List/group by `continuation_status`

### Module ownership (important)

All Step 0 functionality — model fields, controllers, blast email, response notifications, WA trigger, staff review UI — lives entirely in **`ueipab_enrollment_journey`** (not `ueipab_sales`).

| Module | Scope |
|---|---|
| `ueipab_sales` | Quotation engine, Acuerdo PDF, T&C annex — no enrollment logic |
| `ueipab_enrollment_journey` | Enrollment journey wizard, Step 0 gate, all S0 notifications, staff review UI |

The module appears in the Odoo backend under **Sales → Inscripción 2026-2027**. `ueipab_enrollment_journey` depends on `ueipab_sales` (for `sale.order` linkage) but is fully independent — it can evolve without touching the sales module.

### Open question — journey creation scope

✅ Resolved 2026-06-19: mass-create for all ~207 active families at campaign launch, excluding families whose only student(s) are in 5° Año.

---

## 5. Implementation phases (tracking checklist)

- [x] **Phase 0 — Decisions (Gustavo):** ✅ 2026-06-12 — new module ✓; keep Acuerdo PDF ✓; QWeb contract PDF (not Google Docs) ✓; single Enrollment Support group for now ✓; legal snapshot model (draft→signed→amended) ✓
- [x] **Phase 1 — Model + staff UI (testing):** ✅ 2026-06-12 — `ueipab_enrollment_journey` v0.2.0 installed in testing. `enrollment.journey` + `enrollment.journey.student` (name/cédula/grade/institutional_email/insurance_policy). Backend: Sales → "Inscripción 2026-2027" list+form, ✅ Completar / ↩️ Reabrir buttons per step with audit (cleared_by/cleared_at), 🔄 Validaciones + 🌐 Ver página + 🖨️ Imprimir buttons in header.
- [x] **Phase 3 — Customer page:** ✅ 2026-06-12 — `/enrollment-journey/<token>` (auth=public) mora-policy-styled: hero, animated progress bar, vertical timeline (green/pulsing blue/grey/amber states), student chips, Glenda FAB. Mobile-first. Live: http://dev.ueipab.edu.ve:8019/enrollment-journey/4f3c497f-7a41-428a-8896-b42fa224988f
- [x] **Phase 4 — Glenda bubble:** ✅ 2026-06-12 — floating 🤖 FAB → slide-up card → Telegram deep link `t.me/GlendaUeipabBot?start=ENROLL_<token[:8]>`. Phase 1 complete; Glenda ENROLL_ handler + journey context injection = Phase 4b (pending).
- [x] **Phase 5 — Step 6 contract (QWeb PDF):** ✅ 2026-06-13 → **v0.4.1 2026-06-15** — 2-page "Contrato Servicio Educativo Privado - Orden de Servicio" QWeb PDF bound to `enrollment.journey`. Page 1: institution + representante + Section C (students + insurance merged: name/cédula/grade/póliza) + Section E (ceiling summary: $218,88 × N students × 13 payments = max obligation) + Section F (early payment benefit + **QR code**) + dual signatures. Page 2: full 10-clause T&C (Cláusula 4 Plazo de Pago: "pagarse" — corrected 2026-06-15). Auto-sequence `CSE-2627-XXXX` on first print.
  - **QR verification (v0.4.1 → v0.4.2):** QR code anchored at **bottom-right** of page 1 alongside signature row (approved layout 2026-06-15). Links to `/verify-contract/<token>` — public route returns branded "✅ DOCUMENTO VÁLIDO" page: contract number, representante name, date, student list. Invalid/unknown token → 404. Generated in Python report class using `qrcode` lib; URL from `web.base.url` → auto-correct in prod. Sections E + F are full-width; QR is 4th column in signature table.
  - **v0.4.3 — QR seal on page 2 T&C (2026-06-15):** Same QR also rendered at **bottom-right of page 2** T&C signature row (66pt). Both contract pages carry the verification seal.
  - **v0.14.0 — In-person assist + enrollment checklist (2026-06-28, testing):** lets the customer-support team drive the entire process **at the premises** for walk-in families. Staff header buttons **✅ Confirmar (presencial)** / **✖️ No continúa (presencial)** (visible when S0 pending) replicate the public `/confirm`+`/decline` exactly — set status, `_ensure_quote()`, `_send_response_notification()`, auto-create the `enrollment.withdrawal` expediente on decline. **✍️ Aceptación presencial** (visible when `quote_state=='sent'`) opens a wizard requiring a staff attestation ("doy fe de que el representante firmó en físico…") + optional scanned wet-signed PDF → `_record_acceptance_presencial()` marks the current `enrollment.quote.version` accepted with `accept_method='presencial'`, `accept_staff_user_id`, `presencial_attested`, `signed_pdf_attachment_id`, step 1 auto-done. New fields: `enrollment_mode` (online/presencial), `assisted_by`, and per-step `step{1..9}_note` — the backend form doubles as the **enrollment checklist** (Completar/Reabrir + cleared_by/at + note per step). **Public electronic path untouched** (still records `accept_method='electronic'`). One model / token / QR / audit log shared across both modalities. Wizards: `enrollment.presencial.decline.wizard`, `enrollment.presencial.accept.wizard`. See ENROLLMENT_IN_PERSON_ASSIST_PLAN.md.
  - **v0.13.1 / v0.13.2 — Electronic-signature + anticipo T&C clauses (2026-06-28, testing; prod pending counsel pass):** Page-2 T&C extended from 10 → 12 clauses. **Cl.11 ACEPTACIÓN ELECTRÓNICA Y VALIDEZ DE LA FIRMA ELECTRÓNICA** (binds online accept as Firma Electrónica = firma autógrafa; Decreto-Ley G.O. 37.148/2001 arts. 16/4/7/8/17/18; IP+UTC+SHA-256) + acceptance note under the signature block. **Cl.12 FACTURACIÓN FRACCIONADA Y RECUPERACIÓN DE PAGOS ANTICIPADOS (ANTICIPOS)** (multiple SENIAT invoices vs one Anticipo — inscripción + cierre de períodos — "no constituye doble cobro"; BCV rate per invoice; ajustes link to Cl.3). Same canonical text as the Acuerdo (ueipab_sales Cl.10/Cl.11). See TC_ELECTRONIC_SIGNATURE_ENHANCEMENT.md.
- [x] **Phase 5b — Contract escrow workflow (Option B):** ✅ 2026-06-13 — `contract_retained` (Boolean) + `contract_released_date` (Date) on `enrollment.journey`. Step 3 clear → auto `contract_retained=True`. Staff "📋 Liberar contrato" button → manual release. Soft-check hook: all `order_id.invoice_ids` `amount_residual==0` → auto-release. Customer page: retained → amber 📋 "en custodia" card; released → green ✓ + 🎉 celebration.
- [x] **v0.4.0 — 9-step 3-block workflow:** ✅ 2026-06-13 — Restructured from 6 → 9 steps in 3 blocks. `BLOCK_DEFS` + `BLOCK1_STEPS` constants added. Hard gate prevents Block 2/3 clearance until Block 1 complete. Customer page renders block section headers. Contract escrow moved to step 3 (enrollment visit, not end). New steps 5 (Dawere), 8 (Guía Inglés), 9 (Expediente). DB verified: 27 step columns. Demo journey (id=1) reset: Block 1 done + retained, step 4 done, steps 5-9 pending (44%). **Visually verified 2026-06-13:** 3 block headers render correctly; step 3 amber "en custodia" card with left-border callout; step 5 pulsing blue ESTÁS AQUÍ; progress 44% paso 5 de 9.
- [ ] **Phase S0 — Step 0 continuation gate (next priority — pre-prod):** Add `continuation_status/decline_reason/confirmation_date/decline_date` fields to model. Controller branches on status (pending→Step0 page / confirmed→wizard / declined→read-only farewell). POST routes: `/confirm` + `/decline`. Inline JS expand for NO path (prevents accidental irrevocable submit). Staff notification email on decline (`pagos@`). Backend: color badges in list view, reset button. `_next_grade()` helper for grade progression display. See §4b for full spec.
- [ ] **Phase 2 — Soft checks engine:** step 1 wired (order.state='sale' → done_auto). Steps 6 (directory JSON) + step 3 contract-release cron = pending.
- [ ] **Phase 4b — Glenda ENROLL_ handler:** `_handle_telegram_start(ENROLL_<token>)` → inject journey step context into prompt so Glenda answers "¿qué me falta?" precisely.
- [~] **Phase 1b — Student import (HYBRID: live API fetch → snapshot):** ✅ **Steps 1-4 DONE 2026-06-25 (v0.11.0, testing)** — see "Phase 1b — Student Import" section below. Pending: optional daily-cron cache param + prod Akdemia URL confirmation.
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
- ✅ **Journey creation scope (2026-06-19):** Mass-create journeys for all ~207 active families at campaign launch (excluding families whose only student(s) are in 5° Año).
- ✅ **Graduating seniors (5° Año) (2026-06-19):** Excluded from Step 0 student list and from mass-create. Venezuelan law mandates remedial measures to ensure graduation — this is not a parent enrollment decision.
- ✅ **Per-student continuity (2026-06-19):** V1 binary family-level Yes/No is correct. 5° Año students silently filtered from the list; any remaining mixed-family edge case handled manually by staff via chatter note.
- **Clearance role split (future):** once volume grows, split Support (steps 2-3) / IT (4-5) / Finance (6) into separate groups?
- **Notifications (Phase 6):** push notification per step completion via Telegram/email, or page-only pull?

---

## 7. Risks / notes

- **WA paused** (dry_run=True since 2026-05-22): bubble shows Telegram only until Massiva primary restored.
- **Akdemia has no API** — Step 3 soft check depends on the daily scraper; treat as advisory, manual clearance is authoritative.
- **odoo_api_bridge contract code is 2025-2026 era** (MariaDB customer_matches) — do not reuse data layer blindly; only the Google Docs template-copy mechanism is salvageable as-is.
- **Token security:** journey page exposes student names/grades — token must be long/random (reuse notice-ack generator); no enumeration; no financial amounts on the page beyond step status (amounts live in the Acuerdo PDF).

---

## Phase 1b — Student Import (Hybrid: live Akdemia API fetch → snapshot)

**Status:** ✅ Steps 1-4 DONE 2026-06-25 (v0.11.0, testing-only). Tested end-to-end via `odoo shell` with rollback.

> **⚠️ Correction to the older "Akdemia has no API" note above:** Akdemia **does** expose a REST API — `GET /api/ext/v1/students` (Bearer auth, paginated), already used by `scripts/akdemia_api_sync.py`. Phase 1b reuses that endpoint. The *scraper* (Playwright) remains for the 122-col XLS pipeline, but student import for the journey uses the API.

### Design principle
Akdemia is the **source**; data is **persisted** to `enrollment.journey.student` at a controlled moment (staff button, or future daily cache), **never read live on the public page**. Rationale: the contract PDF (`CSE-2627`) is a legal snapshot; the public page must survive Akdemia downtime; grade needs a `_next_grade()` +1 transform with staff override; `insurance_policy`/`institutional_email` are UEIPAB-side and have no Akdemia source.

### What was built (steps 1-4)
1. **Config params** (`ir.config_parameter`):
   | Key | Default | Notes |
   |-----|---------|-------|
   | `akdemia.api_key` | *(none — UserError if missing)* | Bearer token; set in both envs |
   | `akdemia.base_url` | `https://api-staging.akdemia.com` | ⚠️ **staging** — confirm prod URL before prod deploy |
   | `akdemia.per_page` | `200` | pagination |
   | `akdemia.min_students` | `200` | partial-data guard (abort below) |
   | `akdemia.students_json` | *(cron-published, optional)* | guardian→students cache for `use_cache=True` |
2. **Service methods on `enrollment.journey`** (model):
   - `_akdemia_fetch_students()` — live paginated pull; `UserError` on missing key / network / partial (<min).
   - `_akdemia_index_by_guardian(entries)` — `{normalized_cedula: [{name,cedula,grade,section}]}`; student indexed under **every** guardian (parent 2/3 also match).
   - `_akdemia_student_index(use_cache=False)` — cache-or-live dispatcher (falls back to live on corrupt cache).
   - Module helpers `_s()` (string coerce) + `_normalize_cedula()` (`re.sub(r'\D','')` → digits only; `V-14.641.877` → `14641877`).
3. **`action_import_students()`** — matches `partner.vat` → guardian cédula; creates new lines (`source='akdemia'`), updates non-edited lines' name/grade, **preserves** `staff_edited` lines + póliza/correo; reports drift, missing students, and a summary to the chatter; returns a `display_notification` for single-record (form) calls. Context `use_cache=True` reads the daily cache.
4. **`enrollment.journey.student`** gained `source` (manual/akdemia) + `staff_edited` (Boolean). `write()` override: any human edit to `name`/`grade`/`cedula` sets `staff_edited=True`; the sync passes context `akdemia_sync=True` to bypass the guard. View: 📥 Importar / 🔄 Re-sincronizar header buttons (visibility toggled on `student_ids`), `source` column, muted styling for unedited Akdemia rows.

### Verified (testing, rolled back)
Import creates 2 akdemia lines → manual name edit flips `staff_edited` → re-sync **keeps** corrected name + póliza (`POL-999`) untouched → blank-VAT partner raises `UserError`. ✅

### v0.11.1 hardening (2026-06-25 — adversarial code-review fixes)
- **HIGH — blank-cédula idempotency:** `_line_key(cedula, name)` falls back to normalized name when cédula is blank (preescolar pupils). Used for both the `existing` map and the loop/`seen` set, so blank-cédula students match across re-syncs instead of being re-created every run. Per-record body extracted to `_import_students_one()`.
- **MED — pagination:** loop now driven off the LOCAL page counter + returned batch size (`len(batch) < per_page` → stop) with a hard `page > 200` cap, instead of the server-echoed `meta.page` (which could silently truncate or infinite-loop).
- **MED — batch atomicity:** multi-record runs wrap each record in `cr.savepoint()`; a bad record (e.g. missing VAT) is skipped + collected, not fatal — single-record keeps the hard `UserError`. Combined batch notification.
- Verified in testing: 3× re-sync keeps blank-cédula student at count 1; staff edit preserved; batch good-record survives a bad sibling.

### Step 5 — daily cache param ✅ DONE (2026-06-25)
`scripts/akdemia_api_sync.py` Phase 2b: `build_guardian_index(entries)` (1:1 mirror of `_akdemia_index_by_guardian`) + `publish_student_cache(index)` → XML-RPC `set_param('akdemia.students_json', …)` on every reachable env, **skipped under DRY_RUN**. Runs right after the parent map, wrapped in try/except (failure logged, never breaks sheets/bounce phases). Smoke-tested: normalized guardian keys, shared-guardian dedup, empty-name skip, DRY_RUN no-write.

### Pending (not blocking testing)
- **Prod Akdemia base URL** — `akdemia.base_url` default is **staging**; confirmed real for both envs (scope `school_id=63`, env-agnostic) — leave default unless a prod URL is issued.
- **Cached-index sanity floor** (low) — `use_cache=True` trusts any parseable JSON; a degenerate/stale cache degrades silently. Add a min-guardians floor or cron-side size check.
- **Re-sync diff preview UI** — current re-sync reports drift to chatter; a pre-overwrite diff dialog is a nice-to-have.

### Akdemia API connectivity (configured 2026-06-26)
Real credentials live in `/var/www/dev/odoo_api_bridge/.env` (loaded by `scripts/akdemia_api_sync.py` via `load_dotenv`): `AKDEMIA_API_KEY` (72-char Bearer, name `school-UEIAB-api-key-scoped`, scope `school_id=63`, **expires 2027-04-20**), `AKDEMIA_BASE_URL=https://api-staging.akdemia.com`. Set in **testing** `ir.config_parameter` (`akdemia.api_key`/`base_url`/`per_page=200`/`min_students=200`/`min_cache_guardians=150`). Live API verified: HTTP 200, `meta.total=227`, shape `data:[{student,guardians}]`. **Same key+URL go to prod** via `scripts/prod_post_deploy_enrollment_journey.py` (reads env `AKDEMIA_API_KEY`).

---

## Rollout model — bulk survey, per-family auto-quote (locked 2026-06-26)

**Decision (Gustavo):** the S0 continuity survey is the **universal bulk trigger**; the quotation is created **per family, automatically when they answer 'Sí'** — never bulk up front (avoids ~200 wasted draft orders + pricing drift as the llamado window moves L1→L2→L3).

```
1. ONE-TIME mass-create journeys  → all eligible families (skip all-5°-Año), import students
2. BULK S0 blast                  → continuity survey to each parent (action_send_blast_email is multi-record safe)
3. Parent answers Sí / No
4. Sí → auto-create quote (current llamado)   |   No → withdrawal/egreso flow
```

### Auto-quote on confirm (v0.12.0)
`enrollment.journey._ensure_quote()` — idempotent (skips if `order_id` set), sizes to `len(_enrolling_students())` (excludes 5° Año), calls `sale.order.create_ai_quote(partner, n, channel='manual')` at the llamado active on confirmation day, links `order_id`, posts a chatter note. **Never raises** — confirmation must survive a quote hiccup. Wired into controller `journey_confirm` after the status write, before `_send_response_notification`. Verified in testing: idempotent on an existing-order journey; fresh 2-student family → draft $973.20, 2nd call no-dup (rolled back).

### Mass-create script — `scripts/enrollment_journey_mass_create.py`
DRY-RUN by default; `LIVE=1` env to create + import + commit. Universe = Representante tag (25); eligible = VAT matches an Akdemia guardian AND ≥1 enrolling (non-5°-Año) student; skips graduating-only + already-journeyed. LIVE publishes `akdemia.students_json` then imports per-partner with `use_cache=True`.

**3-pass billing-parent dedup** (handles the two-parent case): collect per-student claims → assign each student to the billing parent via `_billing_rank = (posted out_invoices, customer_rank, -id)` → create one journey per partner that wins ≥1 student (pure co-parents skipped, mixed households flagged).

### VAT-matching analysis (2026-06-26) — why the matcher is correct
Investigation of the dry-run's 129 no-match families:
- **The API is complete:** Akdemia API guardian cédulas (322) === Akdemia2526 sheet 3-guardian columns (cols 36/67/98). No guardian is missing from the API.
- **The Customers-tab `Registration` VAT (col 1, 203 families) is the "one valid VAT"** — the curated **billing parent's** cédula, which already resolved the two-parent question (in every shared household exactly one side is in the Customers tab).
- **Odoo reproduces that selection without a sheet dependency:** `max(posted invoices) → customer_rank → lowest id` picks the same billing parent the sheet does, in every shared household tested. (The sheet also has `#N/A` rows, so Odoo billing data is the more reliable authority.)
- **129 breakdown:** 123 genuinely stale (VAT in neither Akdemia guardians nor Customers tab → old/graduated tags, correctly excluded); **6 active-customer data issues** (billing VAT ≠ Akdemia guardian AND Customers `Student(s)` = `#N/A`): BRIMENCA (J-RIF), DAMELIS DOMINGUEZ, DIOLEIDYS ESPINOZA, FIRAS EZZEDDIN, LUIS VILLAZANA, MARIANA GONZALEZ → need a manual cédula fix in Akdemia or manual student entry on the journey.

**Enhanced DRY-RUN (testing):** universe 242 → eligible 103 → **created 98** (co_parent_skipped 4, mixed_household 0, already 1=Roberto), created_no_email 5, 8 shared households all → correct billing parent. **Not run live yet.**

### Quote Accept / Revision + Version Control (v0.13.0, 2026-06-27)

Full design: [QUOTE_ACCEPTANCE_VERSIONING_PLAN.md](QUOTE_ACCEPTANCE_VERSIONING_PLAN.md). Legal basis: [ELECTRONIC_SIGNATURES_VENEZUELA_LAW.md](ELECTRONIC_SIGNATURES_VENEZUELA_LAW.md).

**Lifecycle** (`enrollment.journey.quote_state`): `none → draft → sent → accepted | revision_requested`; re-issue loops `revision_requested → sent` (v2, v3…). Auto-quote on S0 'Sí' lands in `draft`.

**Download gate:** `GET /enrollment-journey/<token>/cotizacion.pdf` returns 404 while `none/draft`; once `sent` it serves the **frozen current version's** attachment (immutable = exactly what was sent), not a live render.

**Version log** `enrollment.quote.version` (immutable audit): one row per issued version — `version`, `order_id`, `amount_total`, `pdf_attachment_id` (frozen PDF = retained *mensaje de datos*), `pdf_sha256`, `issued_date/by`, `state` (issued/superseded/accepted/rejected), plus acceptance evidence (`accept_ip`, `accept_user_agent`, `accept_timestamp_utc`, `tyc_accepted`) and revision evidence. **Single `sale.order` per journey** is kept so the token + QR stay stable across revisions; `_freeze_quote_version()` supersedes the prior `issued` row and bumps `quote_version`.

**Staff:** `action_send_quote()` (header buttons **📤 Enviar cotización** / **🔁 Re-emitir cotización**) freezes a new version, sets `sent`, clears prior acceptance/revision, emails the parent the journey link. Backend page **"Cotización — Versiones"** shows the audit log.

**Parent (public routes, token-scoped):**
- `POST …/quote/accept` — Tier-2 e-signature: requires `tyc` checkbox (server-enforced), captures **IP via `X-Forwarded-For`** (nginx; `remote_addr`=127.0.0.1), User-Agent, UTC timestamp → marks the version `accepted`, sets journey `accepted`, auto-completes step 1, emails pagos@ (internal) + parent (confirmation w/ evidence block).
- `POST …/quote/revision` — captures reason + IP → state `revision_requested`, escalates to **soporte@ CC pagos@** (auto-creates a Freescout conv); parent page shows "le contactaremos".

**Step-1 page UI by state:** draft→"en preparación" (no download/accept); sent→download + **Acepto** (T&C checkbox) + JS-free `<details>` revision box; accepted→"✅ aceptada vN"+download; revision_requested→"🕓 en revisión"+download.

**Legal mapping (Tier-2 / Art. 17 LMDFE):** consent+T&C = Art. 16 chapeau · IP+ts = Art. 8(3) · SHA-256 = Art. 7 integrity · frozen PDF retained = Art. 8 conservation · cédula in PDF = signer link. OTP identity = planned fast-follow; PSC-certified (Art. 18) reserved for highest-stakes clauses.

**Smoke-tested in testing (journey #11, through nginx :8019):** draft download 404 → send (v1 frozen, sha+attachment, parent emailed, download 200) → revision (state+reason+IP, soporte@/pagos@ escalation) → re-issue (v1 superseded, v2 issued) → accept-without-T&C blocked → accept-with-T&C (state accepted, step1 done_auto, IP+UA+UTC+T&C captured, pagos@ notified). ✅ All green.

**Infra:** the :8019 nginx vhost now forwards `Host $http_host` (preserves the port so post-POST 303 redirects don't 404) and already sets `X-Forwarded-For`/`X-Real-IP`. Prod deploy must (a) scp module changes, (b) add `/enrollment-journey` to the prod nginx route whitelist, (c) ensure the prod vhost forwards `X-Forwarded-For` for accurate acceptance IP capture.
