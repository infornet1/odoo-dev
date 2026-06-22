# Academic Executive Annual Report 2025–2026 — Initiative & Design

**Status:** DESIGN / PROPOSAL · **Created:** 2026-06-22 · **Owner:** Gustavo Perdomo (CEO)
**Type:** Public-facing web page + continuity-survey on-ramp

A beautifully designed, newsletter-style **executive academic report** for the
closing 2025–2026 school year. It tells our story across the **3 academic
momentos (lapsos)**, showcases student achievements, announces our new **AI
assistant (Glenda)**, and celebrates our **ecosystem of allied experts** — then
funnels each parent into the **"Encuesta de Continuidad"** to reaffirm their
trust in our quality education for 2026–2027.

This is the emotional/credibility on-ramp that sits **before** the
[Enrollment Journey Wizard](ENROLLMENT_JOURNEY_WIZARD.md): *report → reaffirm
(survey) → enroll (journey)*.

---

## 1. Goals

1. **Celebrate & prove value** — give parents a tangible, premium recap of the
   year's academic results and student stories before the renewal decision.
2. **Anchor the continuity survey** — every section builds toward one CTA:
   reaffirm continuity for 2026–2027.
3. **Showcase the AI launch** — position UEIPAB as innovative (Glenda, deployed
   ~2 months ago) — a differentiator no local competitor has.
4. **Credibility through alliances** — display the expert/vendor ecosystem
   (Kurios, MOA, Akdemia, Fundación la Paz, Digital Ocean, Odoo, Comercial
   Caracas, Ferretería Veramar) to signal a serious, well-supported institution.

## 2. Design language

Base: the **`/mora-policy/`** look (clean cards, brand palette, generous spacing)
— **enhanced** toward a magazine/newsletter feel:

- **Palette:** brand navy `#1a1a6e` → Kurios blue `#2b6fd6`, accent yellow
  `#ffd400`, soft off-white background `#eef1f8` (same family as the Kurios
  newsletters, for visual continuity with what parents just received).
- **Sections** as full-width "scenes" with alternating backgrounds, rounded
  cards, subtle shadows, and a sticky progress/scroll cue.
- **Newsletter touches:** stat counters, a director's letter, a 3-momento
  timeline, a photo/achievement showcase, a partner logo wall, and a final
  high-contrast CTA band.
- **Responsive-first** (most parents open on mobile via WhatsApp link).

## 3. Proposed page structure (scenes, top → bottom)

| # | Scene | Content | Notes |
|---|-------|---------|-------|
| 1 | **Portada / Hero** | UEIPAB logo, "Reporte Ejecutivo Académico 2025–2026", tagline, hero image, scroll cue | Navy→blue gradient |
| 2 | **Mensaje de la Dirección** | Short letter from the CEO framing the year | ~120 words |
| 3 | **Nuestro año en números** | Stat band: # estudiantes, # docentes, # graduandos, logros, etc. | ⏳ data to gather |
| 4 | **Los 3 Momentos Académicos** | Timeline — I, II, III momento: theme, milestones, photos, achievements per lapso | 3-block timeline (reuse enrollment-journey style) |
| 5 | **Historias que nos enorgullecen** | Student achievements showcase — **Robótica Kurios** (oro Desafío 14 + los 7 equipos), olimpiadas, proyectos STEAM, etc. | Ties to the Kurios campaign just sent |
| 6 | **Innovación: nuestra IA "Glenda"** | Announce the AI assistant: 24/7 atención, pagos, info académica, canales WhatsApp/Telegram | See [Glenda overview](GLENDA_AI_AGENT_OVERVIEW.md) |
| 7 | **Nuestro ecosistema de aliados** | Partner logo wall + one-liner each (see §5) | ⏳ logos to source |
| 8 | **Mirando al 2026–2027** | Vision + early-bird/continuity framing | Links to pricing ground truth |
| 9 | **CTA: Encuesta de Continuidad** | High-contrast band + button → survey (tokenized per parent) | The conversion point |
| 10 | **Footer** | Contacts, RIF J-08008617-1, redes, soporte@ | Matches newsletter footer |

## 4. Technical approach (recommendation + options)

**DECIDED (2026-06-22):**
- **Report page = static HTML/CSS**, **generic for all** (no per-parent token on
  the report itself), served via nginx alias — same pattern as mora-policy
  (`alias /var/www/dev/<dir>/`). Fast, fully designable, no Odoo load.
  Route: **`/reporte-anual-2025-2026/`**.
- **No new survey mechanism.** The continuity reaffirmation IS the existing
  **`enrollment.journey`** Step-0 flow — that's the "survey." The annual report
  is the credibility on-ramp whose final CTA links each parent into that journey.
  - **Existing blast template (located):** `enrollment.journey.action_send_blast_email()`
    in `addons/ueipab_enrollment_journey/models/enrollment_journey.py:311`, HTML
    built by `_build_blast_email_html()` (`:352`).
    Subject: *"Proceso de Inscripción 2026-2027 — Confirme la continuidad de
    su(s) representado(s)"*; from/cc `soporte@`; one `mail.mail` per record;
    tracks `blast_sent_date` / `email_missing` / `email_bounced`.
  - **Per-parent link:** the journey token route
    **`/enrollment-journey/<access_token>`** (controller `journey_page.py:142`;
    confirm `:165` / decline `:184`). `access_token` = uuid4 per record;
    `journey_url` computed field. Example live link given by CEO:
    `/enrollment-journey/4f3c497f-7a41-428a-8896-b42fa224988f`.
  - **Tracking:** confirm/decline already updates `continuation_status` on the
    `enrollment.journey` record — so "who reaffirmed" is read straight off that
    model. No `partner.communication.ack` / `survey.survey` needed.

**Personalization split:** the **report page is generic** (same for everyone);
**personalization lives in the CTA** — the button deep-links to that parent's
own `/enrollment-journey/<token>` (their name + students rendered by the journey,
not the report). Best of both: one cacheable static page + per-parent conversion.

**Delivery:** announce via the same proven prod email-blast infra
([prod blast pattern](../scripts/send_robotics_kurios_recap.py)) + Glenda
WhatsApp/Telegram push, linking to the report.

## 5. Partner / ally ecosystem — logo asset checklist

**✅ ALL 9 logos hosted (2026-06-22).** CEO uploaded to
`/home/ftpuser/odoo-dev/annual-rpt-2526/`; staged to
`/var/www/dev/flyers/partners/`, all verified **HTTP 200**. Base URL:
`https://dev.ueipab.edu.ve/flyers/partners/<file>`.

| Partner | Role (proposed copy) | Logo file | Source / link |
|---------|----------------------|-----------|---------------|
| **Kurios** | Robótica educativa & STEAM | ✅ `logo-kurios.jpg` | IG / kuriosedu.com |
| **MOA (MoA School)** | Programa de inglés After School | ✅ `logo-moa.jpg` | ceo@moaeducation.com |
| **Akdemia** | Plataforma de gestión académica | ✅ `logo-akdemia.jpg` | akdemia.com |
| **Motores por la Paz** | Coordina el programa de **olimpiadas estudiantiles ORM** (lengua y matemática) | ✅ `logo-motores-por-la-paz.jpg` (150×150, gris) | IG [@motoresporlapaz](https://www.instagram.com/motoresporlapaz/) |
| **ORM Venezuela** | Olimpiadas de **lengua y matemática** (gestionadas por Motores por la Paz) | ✅ `logo-orm.jpg` (150×150) | IG [@orm_venezuela](https://www.instagram.com/orm_venezuela/) |
| **Digital Ocean** | Infraestructura cloud | ✅ `logo-digitalocean.svg` (oficial, 200×65, fondo navy) | digitalocean.com |
| **Odoo** | ERP / gestión institucional | ✅ `logo-odoo.jpg` (anillo "O" morado) | odoo.com |
| **Comercial Caracas** | Proveedor local (aliado comercial) | ✅ `logo-comercialcaracas.jpg` | local vendor |
| **Ferretería Veramar** | Proveedor local (aliado comercial) | ✅ `logo-veramar.jpg` | local vendor |

**⚠️ Asset notes:**
- **Digital Ocean** — uploaded the **official wordmark SVG** (white logo on navy
  `#031B4E`). CEO also flagged the **referral badge** option:
  `https://web-platforms.sfo2.cdn.digitaloceanspaces.com/WWW/Badge%201.svg`
  linking to `digitalocean.com/?refcode=e16f543b7f99…` — that *earns referral
  credit* but reads as a "Referral Badge", not a clean partner logo. **Decision
  needed:** clean wordmark on the wall (recommended for visual consistency) vs.
  referral badge (affiliate benefit). Can also put the clean logo on the wall and
  the referral link in the footer — best of both.
- The DO SVG has a dark background; on a white logo wall it'll render as a navy
  tile. Either keep as-is (intentional brand block) or request a transparent
  variant. The two 150×150 JPEGs (Motores/ORM) are low-res but fine as thumbnails.
- `veramar.jpg` was renamed to `logo-veramar.jpg` for naming consistency.

**Grouping (9 partners)** — group so each reads intentionally:
- **Aliados Académicos:** Kurios · MOA · Akdemia · **Motores por la Paz** · **ORM Venezuela**
- **Tecnología & Plataforma:** Digital Ocean · Odoo
- **Aliados Comerciales / Proveedores:** Comercial Caracas · Ferretería Veramar

**Note:** Motores por la Paz ↔ ORM are a coordinated pair (Motores por la Paz
manages the ORM olympic programme) — present them adjacent, or as one combined
"Motores por la Paz · ORM" card to avoid reading as two unrelated logos.

## 6. Content to gather (⏳ from the school)

**📝 Skeleton drafted →
[ACADEMIC_ANNUAL_REPORT_CONTENT_DRAFT.md](ACADEMIC_ANNUAL_REPORT_CONTENT_DRAFT.md)**
— a fill-in companion with: a ready-to-edit **director's letter** draft, a
**year-in-numbers** stat grid (pre-filled estimates flagged "verify"), the
**3-momentos** per-lapso structure, a **Glenda** blurb, and a CEO data-request
checklist. Populate it as info is located.

- Per-lapso (I, II, III momento): theme + 2–3 headline achievements + photos.
- Year-in-numbers stats (students, teachers, graduandos, % aprobación, eventos).
- Director's letter (draft ready in the skeleton — approve/edit).
- Confirmed achievement list (Kurios robotics ✅ already have; ORM olimpiadas? others?).
- Glenda announcement angle for parents (benefits, not tech).
- Scene photos → upload to a new `/var/www/dev/flyers/annual/` folder.

## 7. Decisions (RESOLVED 2026-06-22)

1. **Route** — ✅ `/reporte-anual-2025-2026/`.
2. **Survey mechanism** — ✅ **none new**; reuse the existing `enrollment.journey`
   Step-0 blast + `/enrollment-journey/<token>` confirm/decline as the
   reaffirmation. See §4.
3. **Personalization depth** — ✅ **generic page for all**; personalization lives
   only in the CTA (deep-link to the parent's `/enrollment-journey/<token>`).
4. **Language** — ✅ Spanish only (parent-facing).
5. **Academic-olympics partners** — ✅ corrected: it's **Motores por la Paz**
   (coordinates the **ORM** lengua/matemática olympics), plus add **ORM Venezuela**.
   Logos `logo-motores-por-la-paz.jpg` + `logo-orm.jpg` — ✅ uploaded & hosted.

**Still open:**
- ✅ **All 9 partner logos hosted** (2026-06-22) — see §5. (One sub-decision: DO
  clean wordmark vs. referral badge.)
- ⏳ Per-lapso content, year-in-numbers stats, director's letter — skeleton
  drafted (§6 → CONTENT_DRAFT); CEO to populate real data.
6. **Timing / sequencing** — ✅ **DECIDED: option (b)** (CEO agreed 2026-06-22).
   The report and the enrollment-journey blast launch **together**: the journey
   Step-0 blast embeds the report link, and Glenda also pushes it via
   WhatsApp/Telegram — so every parent meets the credibility story at the moment
   of decision (rather than as a separate mailing). Implication: the report page
   must be **published before** the next journey blast wave goes out, and the
   journey `_build_blast_email_html()` body should gain a "Lee nuestro Reporte
   Anual →" button linking to `/reporte-anual-2025-2026/`.

## 8. Suggested phasing

- **Phase 0:** ✅ DONE — structure approved, route + survey mechanism confirmed,
  all 9 logos hosted (§5), content skeleton drafted (§6).
- **Phase 1:** ✅ DONE (2026-06-22) — static report page built & **LIVE**. See
  deployment block below.
- **Phase 2:** ✅ DONE (2026-06-22) — bidirectional journey ↔ report wiring. See §10.
- **Phase 3:** ⏸️ **ON HOLD (2026-06-22)** — page is live with placeholders; the
  CEO will provide real data, then we replace the `.ph` placeholders, remove the
  `.ph` highlight styling, verify the stat counts, and announce via the journey
  blast + Glenda WA/Telegram. **To resume,** the CEO supplies (see
  [CONTENT_DRAFT](ACADEMIC_ANNUAL_REPORT_CONTENT_DRAFT.md) checklist): director's
  name/title + logro 2/3; Momento I & II themes + hitos (+ scene photos →
  `/flyers/annual/`); ORM olympics results; verified student/staff counts.

## 9. Phase 1 deployment (LIVE 2026-06-22)

| Item | Value |
|------|-------|
| **URL** | https://dev.ueipab.edu.ve/reporte-anual-2025-2026/ (HTTP 200) |
| **Served from** | `/var/www/dev/reporte-anual-2025-2026/index.html` |
| **Source (tracked)** | `web/reporte-anual-2025-2026/index.html` (this repo) |
| **nginx** | `location /reporte-anual-2025-2026/` alias block added to `/etc/nginx/sites-available/dev.ueipab.edu.ve` (mirrors mora-policy; backup `*.bak-<ts>`), `nginx -t` OK, reloaded |
| **Design** | mora-policy CSS system (Poppins, navy/blue/gold/teal), enhanced |
| **Scenes built** | nav · hero · year-in-numbers · director letter · 3 momentos · achievements (Kurios real) · Glenda · partner wall (9 logos, 3 groups) · CTA · footer |

**Editing for real data:** placeholders are wrapped in `<span class="ph">…</span>`
(highlighted yellow on the page). Search the HTML for `class="ph"` and the
`<!-- VERIFY -->` comment (stat counts). Remove the `.ph` highlight styling before
the public announcement. To redeploy after editing the tracked source:
`cp web/reporte-anual-2025-2026/index.html /var/www/dev/reporte-anual-2025-2026/`.

**Known follow-ups:** DO logo is a dark-navy SVG tile (intentional brand block;
request transparent variant if undesired); stat counts (+200 students, +40 staff)
are estimates flagged to verify.

## 10. Phase 2 — journey ↔ report wiring (DONE 2026-06-22, testing)

Bidirectional link between the report page and each parent's enrollment journey:

**A. Report → journey (static page JS).** The CTA reads `?j=<journey_url>` from
the URL; if it passes a strict same-domain regex
(`…ueipab.edu.ve(:port)?/enrollment-journey/<uuid>`) the button is rewritten to
that journey link and relabelled "Continuar mi inscripción →". Otherwise the
WhatsApp fallback (`wa.me/584148321963`) stays. **Open-redirect guard verified**
in-browser: a forged `?j=https://evil.com/…` correctly keeps the fallback.

**B. Journey blast → report (Odoo).** `_build_blast_email_html()` now embeds a
secondary "📘 Ver el Reporte Anual 2025-2026 →" card (new helper
`_report_cta_block()`), linking to
`https://dev.ueipab.edu.ve/reporte-anual-2025-2026/?j=<urlencoded journey_url>`.
Constants: `REPORT_URL` + `from urllib.parse import quote`. This realises timing
option (b): the blast carries the report, the report routes back to the journey.

**Why `?j=<full url>` and not `?t=<token>`:** in testing `web.base.url =
http://dev.ueipab.edu.ve:8019` (Odoo on :8019, HTTP) while the report is on
`https://dev.ueipab.edu.ve` (:443). Passing the full per-record `journey_url`
keeps the static page env-agnostic — no hardcoded scheme/port.

**Verification (testing):** module upgraded to **17.0.0.6.0**; email round-trip
checked (link encodes/decodes correctly, JS regex passes); in-browser DOM test of
all 3 cases (valid / forged / no-param) passed; preview emailed to
`gustavo.perdomo@` (mail.mail sent).

**⚠️ Commit note:** the report page + this doc are committed. The **Odoo module
edits (`models/enrollment_journey.py` report-CTA block + helper + constant +
manifest bump to 0.6.0) are applied & live in testing but LEFT UNCOMMITTED** —
they sit on top of large pre-existing uncommitted WIP in the same module (the
Step-0 continuity-survey feature: ~900 lines across model/controller/views). Fold
the report-CTA edit into that feature's commit when it lands; don't commit the
module in isolation. enrollment_journey is **testing-only** (not in production).

## Related

[Enrollment Journey Wizard](ENROLLMENT_JOURNEY_WIZARD.md) ·
[Glenda Overview](GLENDA_AI_AGENT_OVERVIEW.md) ·
[Kurios Newsletter](ROBOTICS_KURIOS_NEWSLETTER.md) ·
[Budget/Continuity campaigns](PDVSA_CONTINUITY_CAMPAIGN.md) ·
[Pricing ground truth](../scripts/) · mora-policy page (`/var/www/dev/mora/`)
