# Enrollment In-Person Assist + Checklist — Plan

**Created:** 2026-06-28
**Module:** `ueipab_enrollment_journey` (✅ deployed to prod 2026-06-29 as part of v0.14.0)
**Related:** [ENROLLMENT_JOURNEY_WIZARD.md](ENROLLMENT_JOURNEY_WIZARD.md) · [QUOTE_ACCEPTANCE_VERSIONING_PLAN.md](QUOTE_ACCEPTANCE_VERSIONING_PLAN.md) · [ELECTRONIC_SIGNATURES_VENEZUELA_LAW.md](ELECTRONIC_SIGNATURES_VENEZUELA_LAW.md) · [ENROLLMENT_PROCESS_PROD_DEPLOYMENT_ASSESSMENT.md](ENROLLMENT_PROCESS_PROD_DEPLOYMENT_ASSESSMENT.md)

## Goal

Let the **customer-support team drive the entire enrollment business process at the premises** for families who prefer to enroll in person, using the **backend form as a working enrollment checklist**. The in-person path is a **staff-driven mirror** of the public self-service flow — **one model, one token + QR, one lifecycle** — with a **wet-signature** acceptance evidence type instead of the Tier-2 electronic one.

## Why this is mostly already there

The backend `enrollment.journey` form is already a checklist: all **9 steps** have **✅ Completar** (`action_clear_step`→`done_manual`) / **↩️ Reabrir** buttons stamping `cleared_by` + `cleared_at`, with the **Block-1 hard gate** enforced in `_set_step`. Staff buttons already exist for quote send/re-issue, contract print/release, soft checks, student import, S0 reset, blast/WA. **Four gaps** block fully operating it at the desk (below).

## The 4 gaps → the 4 additions

### 1. Backend S0 confirm / decline **on behalf** (presencial)
S0 only flips via the public `/confirm` `/decline` routes. Add staff buttons that replicate the controller logic exactly:
- `action_confirm_presencial()` — guard `continuation_status=='pending'` → set `confirmed` + `confirmation_date`, `enrollment_mode='presencial'`, `assisted_by=uid` (if empty) → **`_ensure_quote()`** → **`_send_response_notification('confirmed')`** → chatter note.
- `action_decline_presencial()` — opens a tiny wizard for the reason → sets `declined` + reason + `decline_date` → `_send_response_notification('declined')` (which already **auto-creates the `enrollment.withdrawal` expediente**, line 933).

### 2. Staff **wet-signature** acceptance of the quote (presencial)
Public accept is parent-only Tier-2 e-sig (`/quote/accept`, IP/UTC/T&C). In person the parent signs the **printed Acuerdo** (wet signature — supported by the DECLARACIÓN box and **legally stronger** than Tier-2). Add:
- `action_mark_quote_accepted_presencial()` — guard `quote_state=='sent'` → opens an accept wizard.
- **Accept wizard** (`enrollment.presencial.accept.wizard`): a **required attestation** checkbox ("Doy fe de que el representante firmó en físico el Acuerdo y sus T&C") + an **optional scanned wet-signed PDF** upload.
- `_record_acceptance_presencial(staff_user_id, attested, signed_attachment_id)` — sibling of `_record_acceptance`; marks the current version `accepted` with `accept_method='presencial'`, `accept_staff_user_id`, `presencial_attested=True`, `tyc_accepted=True` (wet signature covers the printed T&C), `accept_timestamp_utc=now`, optional `signed_pdf_attachment_id`; flips `quote_state='accepted'`, auto-completes step 1; sends the accepted email. **Public path untouched** (separate method).

### 3. Per-step **notes + document capture** (checklist affordance)
Add a `step{i}_note` text field per step (9) so reception can record "recibí copia de cédula / partida de nacimiento" against each step. Physical documents attach via the standard chatter/attachments (and the signed Acuerdo via the version log in #2).

### 4. **Modalidad** + **Atendido por** markers
- `enrollment_mode` (`online` / `presencial`, default `online`) — set to `presencial` by the staff actions.
- `assisted_by` (res.users) — which support agent handled the family. For reporting/filtering.

## Data model deltas

**`enrollment.journey` (new):** `enrollment_mode` (Selection online/presencial, default online), `assisted_by` (M2o res.users), `step1_note`…`step9_note` (Text).

**`enrollment.quote.version` (new):** `accept_method` (Selection electronic/presencial, default electronic), `accept_staff_user_id` (M2o res.users), `presencial_attested` (Boolean), `signed_pdf_attachment_id` (M2o ir.attachment, ondelete set null).

**New transient wizards:** `enrollment.presencial.decline.wizard` (journey_id, reason Text required) · `enrollment.presencial.accept.wizard` (journey_id, attested Boolean required, signed_pdf Binary + filename). Both need access rules for `group_enrollment_support`.

## Backend UX

- **Header buttons:** "✅ Confirmar (presencial)" + "✖️ No continúa (presencial)" (visible when `continuation_status=='pending'`); "✍️ Aceptación presencial" (visible when `quote_state=='sent'`).
- **Top group:** `enrollment_mode` + `assisted_by` shown alongside continuity status.
- **Steps area = checklist:** each existing step block gains its `step{i}_note`. Progress bar (`progress_pct`) already present. This is the "enrollment checklist" the support agent ticks through with the family.
- **Versiones tab:** add `accept_method` + `accept_staff_user_id` columns so electronic vs presencial acceptances sit in one audit trail.

## Legal note

Wet signature on the printed Acuerdo (with the DECLARACIÓN box + the new e-sig clause Cl.10) is the **strongest** acceptance form under Venezuelan law — firma autógrafa, Art. 16 LMDFE. The staff attestation + optional scanned PDF give a clean, auditable record in the same `enrollment.quote.version` log used for electronic acceptances. No new legal exposure beyond what counsel is already reviewing (B6 in the deploy assessment).

## Out of scope (follow-ups)

Per-step file attachments as a structured One2many (chatter is enough for v1) · a dedicated "reception kiosk" view of the public page (staff can already use **Abrir página del representante**) · reporting dashboard by `assisted_by` / `enrollment_mode`.

## Test plan (testing-first)

1. Reset a journey to S0 pending (e.g. Roberto, id=11). Click **Confirmar (presencial)** → status confirmed, `enrollment_mode=presencial`, `assisted_by` set, auto-quote draft created, notification sent.
2. **Enviar cotización** → **Aceptación presencial** → wizard: try without attestation (blocked) → with attestation + scanned PDF → version accepted with `accept_method=presencial`, staff user, attestation, attachment; `quote_state=accepted`; step 1 auto-done.
3. Tick steps 2-9 with notes; confirm Block-1 gate still enforced.
4. Second journey → **No continúa (presencial)** → reason wizard → declined + withdrawal expediente auto-created + internal notice.
5. Confirm the public self-service path is unchanged (regression): a normal `/quote/accept` still records `accept_method=electronic`.

## Status

✅ **BUILT + DEPLOYED TO PROD 2026-06-29** (v0.14.0, folded into the enrollment prod deploy — see ENROLLMENT_PROCESS_PROD_DEPLOYMENT_ASSESSMENT.md §13). ⚠️ B6 counsel sign-off still pending before any parent-facing send; pilot deferred to manual UI validation.
