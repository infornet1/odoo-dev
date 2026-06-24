# Enrollment Withdrawal (Egreso / Retiro) Plan — 2025-2026

**Status:** 🛠️ PHASES 1-4 DONE 2026-06-24 (v0.10.0) — model + staff UI + notifications + auto-create-on-decline live in testing; Phase 5 (Gmail automation) pending
**Created:** 2026-06-23
**Module:** `ueipab_enrollment_journey` (same module — new sibling model)
**Related:** [ENROLLMENT_JOURNEY_WIZARD.md](ENROLLMENT_JOURNEY_WIZARD.md) · memory `project-enrollment-journey`

---

## 1. Purpose & Trigger

When a family responds **"No continúa"** on the Step-0 continuity survey
(`enrollment.journey.continuation_status = 'declined'`), the school must run a
formal **offboarding / egreso** process: confirm solvencia, prepare exit
documentation, and release the student(s) from every platform and regulatory
register.

This is a **distinct business process** from enrollment — different goal
(offboarding vs. onboarding), different owners (admin / finance / IT vs.
sales / support), different audience (staff-internal vs. customer-facing). It
therefore gets its **own model**, not extra steps on `enrollment.journey`.

```
enrollment.journey  ──(continuation_status='declined')──▶  enrollment.withdrawal
   (onboarding, customer-facing)                            (offboarding, staff-facing)
```

### Why split (and not extend the journey)

- `progress_pct`, the `BLOCK1_STEPS` hard gate, and `_set_step()` all assume a
  forward enrollment path — a declined family would read as "0% enrolled" forever.
- "How many withdrawals are fully processed?" wants its own `state` field, not a
  filter over enrollment steps.
- The enrollment public page is customer-facing; exit steps are staff-only.

---

## 2. Data Model — `enrollment.withdrawal`

**Label:** "Retiro / Egreso 2025-2026" (aligns with the farewell page's existing
"formalizar el retiro" wording).

| Field | Type | Notes |
|-------|------|-------|
| `journey_id` | M2o `enrollment.journey` | Origin link (the declined journey). `ondelete='set null'` |
| `partner_id` | M2o `res.partner` | Representante (copied/related from journey) |
| `student_ids` | M2o or snapshot | The withdrawing students = the journey's **enrolling** students (excludes graduating 5° Año — that is a *graduation* egress, not a withdrawal) |
| `exit_reason` | Text, readonly | Copied from `journey_id.decline_reason` |
| `state` | Selection | `in_progress` / `completed` (auto-`completed` when all steps done) |
| `step1_state` … `step5_state` | Selection (`STEP_STATES`) | Reuse the enrollment state machine (`pending` / `in_progress` / `done_auto` / `done_manual` / `blocked`) |
| `step1_cleared_at` … `step5_cleared_at` | Datetime, readonly | Audit timestamps |
| `solvencia_ref` | Char | Reference for the no-due-balance letter (step 1) |
| `sige_ref` | Char | SIGE constancia / reference number (step 4) |
| `access_token` | — | **Not needed** — no customer page (see §5) |

Storage mirrors the enrollment pattern: **generic `stepN_state` columns** so
reordering the step definitions never requires a DB migration.

---

## 3. The 5 Steps

Driven by a module-level `WITHDRAWAL_STEP_DEFS` constant (same pattern as
`STEP_DEFS`).

| # | Step (es) | Scope | Gate | Notification |
|---|-----------|-------|------|--------------|
| 0 | *(entry)* Proviene de "No continúa" | family | — | — (record auto-created on decline) |
| 1 | Solvencia administrativa 2025-2026 (carta de no deuda — jul+ago pagados) | family | — (legal gate for all below) | — |
| 2 | Preparar documentación de egreso | family | needs **1** | → `soporte@` **CC `josefina.rodriguez@`** |
| 3 | Desincorporar de Akdemia (edge.akdemia.com) | per-family* | needs **1 + 2** | — |
| 4 | Liberar de SIGE (Mppe — sistema de gobernanza estudiantil) | per-family* | needs **1 + 2** | — |
| 5 | Suspender cuentas Gmail institucionales | per-family* | needs **1 + 2** | → `soporte@` **CC `lorena.reyes@`, `alejandra.lopez@`** |

\* See decision **D1** — per-family vs per-student.

**Gating logic** mirrors the enrollment hard gate: steps 3–5 raise `UserError`
if step 1 (solvencia) or step 2 (exit docs) is not in `DONE_STATES`. Steps 3, 4,
5 are independent of one another (parallel once the gate opens).

**Completion:** when all 5 steps reach `DONE_STATES`, `state = 'completed'`
(auto), timestamp recorded.

---

## 4. Notifications

Reuse the existing email helpers (`_email_wrapper`, `_cta_button`,
`_student_list_html`) — all already module-level functions.

| Trigger | To | CC | Purpose |
|---------|----|----|---------|
| Step 2 cleared | `soporte@` | `josefina.rodriguez@` | Prepare exit documentation |
| Step 5 cleared | `soporte@` | `lorena.reyes@`, `alejandra.lopez@` | Suspend Gmail accounts |

All addresses `@ueipab.edu.ve`. Emails are **staff-internal** (no customer
copy — customers are not in the Odoo process; the farewell page already covers
their side).

**Integration with the existing declined email:** the declined **internal**
notification's "Ver expediente en Odoo →" button should deep-link to the new
**withdrawal** record (the offboarding checklist), not the enrollment form — so
staff land exactly where the work is.

---

## 5. UI

- **Staff form** — header buttons per step ("✔️ Confirmar solvencia",
  "📄 Documentación lista", "🎓 Desincorporar Akdemia", "🏛️ Liberar SIGE",
  "📧 Suspender Gmail"), each calling a `_set_step()`-style clearance method;
  reference fields for solvencia/SIGE; chatter log per action.
- **List view** — `state` badge + per-step progress; decoration by state.
- **Menu** — under "Inscripción 2026-2027" → new "Egresos / Retiros" item
  (sibling of the "Revisión S0" menu).
- **No public/customer page.** The declined farewell page
  (`/enrollment-journey/<token>` when `declined`) already serves the customer.

---

## 6. External-System Reality (informs future automation)

v1 = **all manual confirm**, but field design should leave room for automation:

| System | API? | v1 | Future |
|--------|------|----|--------|
| **Akdemia** (edge.akdemia.com) | Scraper only (`akdemia_scraper.py`, Playwright) | Manual + deep link to student | Automatable but fragile — low priority |
| **SIGE (MPPE)** | **None** (government) | Manual + `sige_ref` audit field | Permanently manual |
| **Gmail / Workspace** | **Yes** — Admin SDK | Manual confirm | **Best candidate**: `users.update {suspended:true}` via existing Google creds (`sync_google_directory.py`) |

---

## 7. Triggering & Wiring

- **Auto-create** the `enrollment.withdrawal` record when a family declines —
  hook into `journey_decline` controller POST (or
  `_send_response_notification('declined')`), **idempotent** (one withdrawal per
  journey; guard against duplicates). Rationale: nothing falls through the cracks.
  See decision **D2**.
- Copy `exit_reason` from `decline_reason`; snapshot `student_ids`.
- Set `state='in_progress'`, all steps `pending`.

---

## 8. Reuse Inventory (low duplication)

Directly reusable from `models/enrollment_journey.py`:

- `_email_wrapper()`, `_cta_button()`, `_student_list_html()` — email building
- `STEP_STATES`, `DONE_STATES` — state machine
- `_set_step()` clearance + hard-gate pattern (adapt for 5 steps / new gate)
- `_backend_url()` — backend deep links
- `SOPORTE_EMAIL` constant; new `JOSEFINA_*` / `GMAIL_SUSPEND_CC` constants

The split is **a new model + view + ~2 email builders**, not a parallel
reimplementation.

---

## 9. Decisions — SETTLED 2026-06-23 ✅

| ID | Decision | Resolution |
|----|----------|-----------|
| **D1** | Per-student vs per-family confirm for steps 3–5 | ✅ **Per-family** — one confirm per step, student list shown for reference |
| **D2** | Trigger: auto-create on decline vs. manual button | ✅ **Auto-create on decline**, idempotent (one withdrawal per journey) |
| **D3** | Audit reference fields on regulated steps | ✅ **Add** `solvencia_ref` (step 1) + `sige_ref` (step 4) |
| **D4** | Gmail suspension automation now or later | ✅ **Manual v1**; Admin SDK `users.update{suspended:true}` deferred to v2 (see §10 Phase 5) |

---

## 10. Implementation Phases (once approved)

1. **Phase 1 — Model + steps:** ✅ **DONE 2026-06-23 (v0.7.0)** — `enrollment.withdrawal`
   (`models/enrollment_withdrawal.py`), `WITHDRAWAL_STEP_DEFS`, state machine
   (`state` in_progress/completed + `progress_pct`), hard gate (steps 3-5 require
   1+2), `_set_step` clearance + chatter audit, `solvencia_ref`/`sige_ref`,
   per-family related fields from `journey_id`, security. Smoke-tested
   (gate/completion/reopen/related/chatter), testing-only.
2. **Phase 2 — Staff UI:** ✅ **DONE 2026-06-24 (v0.8.0)** — `views/enrollment_withdrawal_views.xml`
   (registered in manifest): tree (state/progress badges + per-step cols) + form
   (5-step checklist, clear/reopen buttons, hard gate, solvencia/SIGE refs,
   chatter) + action + menu under Sales (seq 32). Also fixed: `enrollment.journey`
   now `_inherit=['mail.thread']`.
3. **Phase 3 — Notifications:** ✅ **DONE 2026-06-24 (v0.9.0)** — `_set_step` fires
   a staff-internal email on transition INTO a done state for **step 2** (To
   `soporte@`, CC `josefina.rodriguez@`) and **step 5** (To `soporte@`, CC
   `lorena.reyes@`, `alejandra.lopez@`); steps 1/3/4 silent; double-send guard
   (skips re-confirmations via `was_done`). Builders `_build_step_notification_html`
   + `_notify_step` reuse `_email_wrapper`/`_cta_button`; CTA → withdrawal
   `_backend_url`. Journey declined **internal** email button re-pointed to the
   withdrawal record via new `_withdrawal_url()` (falls back to journey form until
   Phase 4 auto-create exists). Verified end-to-end in testing (To/CC, gate,
   no-double-send, deep-link, completion), mails non-delivered + rolled back.
4. **Phase 4 — Trigger wiring:** ✅ **DONE 2026-06-24 (v0.10.0)** — `enrollment.journey._ensure_withdrawal()`
   (idempotent: one withdrawal per journey, returns existing if present) is
   called from `_send_response_notification('declined')` before the internal
   email is built, so the "Ver expediente de egreso →" button always deep-links
   to the real record. partner/students/exit_reason populate via related fields
   from `journey_id`. Chatter note on the journey when created. Verified
   (0→1 create, idempotent re-decline stays 1, related fields populated,
   internal email embeds the withdrawal link); test rolled back.
5. **Phase 5 (later) — Gmail automation:** Admin SDK suspension button.

Testing-only until validated; production deploy is a separate later phase
(mirrors enrollment journey, which is also testing-only).

---

## Appendix — Step-to-Owner Quick Map

| Step | Primary owner | Notified |
|------|---------------|----------|
| 1 Solvencia | Finance | — |
| 2 Exit docs | Admin (Josefina) | soporte@ + josefina.rodriguez@ |
| 3 Akdemia | IT / Support | — |
| 4 SIGE | Admin | — |
| 5 Gmail suspend | IT (Lorena / Alejandra) | soporte@ + lorena.reyes@ + alejandra.lopez@ |
