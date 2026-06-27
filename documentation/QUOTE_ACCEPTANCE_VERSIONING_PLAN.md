# Quote Acceptance, Revision & Version Control — Plan

**Created:** 2026-06-27
**Module:** `ueipab_enrollment_journey` (testing-first; prod deploy later via scp kit)
**Related:** [ENROLLMENT_JOURNEY_WIZARD.md](ENROLLMENT_JOURNEY_WIZARD.md) · [ELECTRONIC_SIGNATURES_VENEZUELA_LAW.md](ELECTRONIC_SIGNATURES_VENEZUELA_LAW.md)

## Goal

In wizard step **"1. Cotización confirmada"**, let the parent either **accept** the quotation (a Tier-2 electronic acceptance capturing IP + timestamp + PDF hash) or **request a revision** (escalated to soporte@ CC pagos@). Keep **full quotation version control** with the **same journey token + QR** across revisions.

## Decisions (confirmed 2026-06-27)

- **Revision escalation:** email **soporte@** (auto-creates a Freescout conv) **CC pagos@**. *(Not the parent, not RRHH.)*
- **Versioning:** **single `sale.order` per journey** (stable token + QR) + an **immutable `enrollment.quote.version` log** (frozen PDF + SHA-256 per issued version).
- **E-signature level:** **Tier-2 now** (logged consent + T&C checkbox + IP + UTC timestamp + PDF SHA-256 + retained data message + cédula in PDF). **OTP = fast-follow.** *(Legal basis: Art. 17 LMDFE — valid, weighed under sana crítica; compensating controls maximize defensibility. See the legal doc.)*

## Lifecycle (`enrollment.journey.quote_state`)

```
none ──_ensure_quote (S0 'Sí')──▶ draft ──staff "Enviar cotización"──▶ sent
  sent ──parent "Acepto" (+T&C)──────────────────────────────────────▶ accepted ──▶ step 1 done → step 2
  sent ──parent "Solicitar revisión"──▶ revision_requested ──staff "Re-emitir"──▶ sent (v2, v3…)
```

- **draft** = auto-quote exists but not released → **download gate**: parent sees "en preparación", no download/accept.
- **sent** = staff released vN → download + **Acepto** / **Solicitar revisión** appear.
- **accepted** = Tier-2 acceptance recorded; step 1 auto-completes.
- **revision_requested** = escalated; parent told "le contactaremos"; current version still downloadable.

## Data model

**`enrollment.journey` (new fields):** `quote_state` (Selection: none/draft/sent/accepted/revision_requested), `quote_sent_date`, `quote_accepted_date`, `quote_revision_reason`, `quote_version` (int, current), `quote_version_ids` (O2M).

**`enrollment.quote.version` (new, immutable audit log):**
`journey_id`, `version` (int), `order_id`, `amount_total` + `currency_id`, `pdf_attachment_id` (frozen PDF = retained *mensaje de datos*), `pdf_sha256`, `issued_date`, `issued_by`, `state` (issued/superseded/accepted/rejected); acceptance evidence: `accept_ip`, `accept_user_agent`, `accept_timestamp_utc`, `tyc_accepted`; revision evidence: `revision_reason`, `revision_ip`, `revision_timestamp_utc`.

## Model methods

- `_render_quote_pdf()` — render `ueipab_sales.action_report_quotation_agreement` for `order_id`.
- `_freeze_quote_version()` — render PDF → SHA-256 → `ir.attachment` → supersede prior `issued` row → create new `issued` version row → bump `quote_version`. Returns the version.
- `action_send_quote()` — staff (initial send **and** re-issue): freeze new version, `quote_state='sent'`, stamp `quote_sent_date`, clear prior acceptance/revision, email parent the journey link. Guard: requires `order_id`.
- `_record_acceptance(ip, user_agent, tyc)` — guard `quote_state=='sent'`; mark current version `accepted` + write IP/UA/UTC-ts/tyc; `quote_state='accepted'`; auto-complete step 1 (`step1_state='done_auto'`); notify pagos@.
- `_record_revision_request(reason, ip)` — guard `quote_state=='sent'`; write revision evidence on current version; `quote_state='revision_requested'`; email soporte@ CC pagos@.
- `_ensure_quote()` — also sets `quote_state='draft'` on auto-create.

## Controller (public, token-scoped)

- `GET …/cotizacion.pdf` — serve the **frozen current version's** attachment (immutable = exactly what was sent); 404 when `quote_state` ∈ {none, draft}.
- `POST …/quote/accept` — require `tyc` checkbox; capture **IP via `X-Forwarded-For`** (nginx sets it; `remote_addr` = 127.0.0.1), UA, UTC ts → `_record_acceptance` → redirect.
- `POST …/quote/revision` — `reason` (required) + IP → `_record_revision_request` → redirect.
- **Step-1 UI by state:** draft→"en preparación"; sent→download + Acepto form (T&C checkbox) + `<details>` revision box (JS-free); accepted→"✅ aceptada el … · vN" + download; revision_requested→"🕓 en revisión, le contactaremos" + download.

## Backend views

- Header buttons: **📤 Enviar cotización** (`quote_state=='draft'`) and **🔁 Re-emitir cotización** (`quote_state` ∈ sent/accepted/revision_requested), both `action_send_quote`.
- Step-1 group: show `quote_state`, `quote_sent_date`, `quote_accepted_date`, `quote_revision_reason` (invisible unless revision).
- New page **"Cotización"**: read-only `quote_version_ids` tree (version, state, amount, issued_date/by, sha256, accept_ip, accept_timestamp_utc, PDF attachment).

## Legal mapping (Tier-2)

consent + T&C = Art. 16 chapeau · IP + timestamp = Art. 8(3) · PDF SHA-256 = Art. 7 (integrity) · retained frozen PDF = Art. 8 (conservation) · printout = Art. 4 ¶3 (fotostática) · cédula in PDF = signer link. Evidentiary value under Art. 17 (sana crítica). OTP fast-follow strengthens identity.

## Status & decision (2026-06-27)

**Tier-2 implementation KEPT AS-IS** — for enrollment adhesion contracts this is the proportionate, recommended path (Art. 17). No further e-signature work scheduled. The ranked enhancement backlog (OTP, acceptance acta page, T&C hash, consent clause, RFC-3161 timestamp, PSC certification, WORM archival) lives in [ELECTRONIC_SIGNATURES_VENEZUELA_LAW.md](ELECTRONIC_SIGNATURES_VENEZUELA_LAW.md) §9 — build only when a real need arises.

## Out of scope (follow-ups)

Deferred e-signature enhancements (see legal doc §9) · prod nginx route whitelist for `/enrollment-journey` · `proxy_mode` (we read `X-Forwarded-For` manually instead).
