# Enrollment Process — Production Pilot Checklist

**Module:** `ueipab_enrollment_journey` v17.0.0.11.2 · **Env:** PRODUCTION (`DB_UEIPAB` / `odoo.ueipab.edu.ve`)
**Goal:** prove the full enrollment process end-to-end on **ONE** real family before any parent-facing blast.
**Safety rule:** set the pilot journey **contact email = `gustavo.perdomo@ueipab.edu.ve`** → every email lands in your inbox, **zero real parents touched**.

**Pilot run by:** ________________  **Date:** ____ / ____ / 2026  **Start time:** ______  **End time:** ______

---

## A. Pre-pilot gates (must ALL be ✅ before starting)

| ✓ | Gate | How to confirm | OK? |
|---|------|----------------|-----|
| ☐ | Module installed | XML-RPC: `ueipab_enrollment_journey` `state=installed`, `installed_version=17.0.0.11.2` | ☐ |
| ☐ | Dependency present | `ueipab_sales` `state=installed` | ☐ |
| ☐ | `akdemia.api_key` set | non-empty (post-deploy `--live` output) | ☐ |
| ☐ | `enrollment.report_url` set | points at the chosen public host | ☐ |
| ☐ | `web.base.url` correct | `https://odoo.ueipab.edu.ve` (+ `web.base.url.freeze=True`) | ☐ |
| ☐ | Mail works | ≥1 `ir.mail_server`; a test send reaches `gustavo.perdomo@` | ☐ |
| ☐ | DB backup taken | pre-pilot `DB_UEIPAB` backup exists (for rollback) | ☐ |

> If any gate is ✗ → stop, fix it, do **not** start the pilot.

---

## B. Pilot steps (one family, contact = gustavo.perdomo@)

### ☐ STEP 0 — Create the pilot journey
- **Do:** Create one `enrollment.journey` for a real family whose `partner.vat` is a valid Akdemia guardian cédula (`VXXXXXXXX`). Set the contact email to `gustavo.perdomo@`.
- **Expect:** record saved, access token generated.
- Journey id: ________  Token: ____________________  **Result:** ☐ Pass ☐ Fail
- Notes: ______________________________________________

### ☐ STEP 1 — Journey page renders
- **Do:** Open `https://odoo.ueipab.edu.ve/enrollment-journey/<token>` in a browser.
- **Expect:** 9-step / 3-block timeline renders, correct students + grades, Glenda bubble, no error.
- **Result:** ☐ Pass ☐ Fail  Notes: ______________________________________

### ☐ STEP 2 — Akdemia import → preview
- **Do:** On the journey form (backend), click **📥 Importar estudiantes**.
- **Expect:** preview wizard opens, lists the family's REAL Akdemia students (matched `partner.vat` ↔ guardian cédula), correct next-year grade roll. **Nothing written yet.**
- ⚠️ If `UserError: akdemia.api_key` → param missing, fix gate A and retry.
- **Result:** ☐ Pass ☐ Fail  Match looks right? ☐ Yes ☐ No  Notes: ____________________

### ☐ STEP 3 — Confirm import → lines created
- **Do:** Click **✅ Aplicar importación** in the preview wizard.
- **Expect:** `enrollment.journey.student` lines created (next-year grades), no duplicates, Block-1 state updated.
- **Result:** ☐ Pass ☐ Fail  # students created: ____  Notes: ________________________

### ☐ STEP 4 — S0 continuity → CONFIRM
- **Do:** Trigger the S0 continuity send (goes to gustavo.perdomo@ = safe test). Open the email, click **CONFIRM / Continuar**.
- **Expect:** email delivered to your inbox; `continuation_status` → confirmed; journey advances past the Block-1 gate; NO withdrawal created.
- **Result:** ☐ Pass ☐ Fail  Notes: ______________________________________

### ☐ STEP 5 — Contract PDF (CSE-2627 + QR)
- **Do:** With S0 confirmed, **🖨️ Imprimir Contrato**. Then scan/visit the QR target.
- **Expect:** PDF = `CSE-2627-0001` (first prod contract), QR seal on **all** pages; `/verify-contract/<token>` resolves on prod and matches the contract.
- **Result:** ☐ Pass ☐ Fail  Contract #: ____________  QR resolves? ☐ Yes ☐ No

### ☐ STEP 6 — Withdrawal auto-create on DECLINE
- **Do:** On a SECOND pilot S0 send (or a 2nd pilot journey), open the email and click **DECLINE / No continúo**.
- **Expect:** an `enrollment.withdrawal` auto-creates + links to the journey; internal notice emails `pagos@` (CC RRHH/support) with a working backend link; 5-step egreso timeline initialized. (Gmail auto-suspend = manual v1, no action.)
- **Result:** ☐ Pass ☐ Fail  Withdrawal id: ______  Notes: ____________________

### ☐ STEP 7 — Report CTA round-trip
- **Do:** Open `enrollment.report_url` in a browser, then follow the report's enrollment CTA with `?j=<pilot journey>`.
- **Expect:** report loads on the chosen host (logos + `ceo-profile-pic.jpeg` present); CTA routes back to `/enrollment-journey/<token>`.
- **Result:** ☐ Pass ☐ Fail  Notes: ______________________________________

---

## C. Verdict

- ☐ **PILOT GREEN** — all STEPs 0–7 passed, **zero real-parent emails sent**.
  → Cleared to share journey links / start the S0 blast wave.
  - ☐ `ai_agent.dry_run` at intended state · ☐ 5° Año (graduating-senior) inclusion decided.
- ☐ **PILOT FAILED at STEP ____** → do NOT blast. Fix or roll back (assessment §12). No parent was affected.

**Sign-off:** ____________________  **Time:** ______

---

## D. Cleanup after a successful pilot
- Delete or archive the pilot journey(s) + withdrawal(s) so the first real contract number stays clean (or accept `CSE-2627-0001` as the pilot and start real families at `-0002`).
- Confirm no pilot artifacts remain that would confuse staff.

> Full context: `ENROLLMENT_PROCESS_PROD_DEPLOYMENT_ASSESSMENT.md` (§9 deploy kit · §10 gates · §11 smoke · §12 rollback).
