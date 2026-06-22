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

⚠️ **None of the partner logos are on the server yet** (only UEIPAB's own
`ueipab_logo.png` / `school_logo.png` and the Kurios poster wordmark). To source
and host under e.g. `/var/www/dev/flyers/partners/` →
`https://dev.ueipab.edu.ve/flyers/partners/<name>.png`:

| Partner | Role (proposed copy) | Logo status | Source / link |
|---------|----------------------|-------------|---------------|
| **Kurios** | Robótica educativa & STEAM | ⏳ extract from posters / get clean PNG | kuriosedu.com / posters |
| **MOA (MoA School)** | Programa de inglés After School | ⏳ need PNG | ceo@moaeducation.com |
| **Akdemia** | Plataforma de gestión académica | ⏳ need PNG | akdemia.com |
| **Motores por la Paz** | Coordina el programa de **olimpiadas estudiantiles ORM** (lengua y matemática) | ✅ hosted `partners/logo-motores-por-la-paz.jpg` (150×150, gris) | IG [@motoresporlapaz](https://www.instagram.com/motoresporlapaz/) |
| **ORM Venezuela** | Olimpiadas de **lengua y matemática** (gestionadas por Motores por la Paz) | ✅ hosted `partners/logo-orm.jpg` (150×150) | IG [@orm_venezuela](https://www.instagram.com/orm_venezuela/) |
| **Digital Ocean** | Infraestructura cloud | ⏳ official brand asset | digitalocean.com/press |
| **Odoo** | ERP / gestión institucional | ⏳ official brand asset | odoo.com/brand-assets |
| **Comercial Caracas** | Proveedor local (aliado comercial) | ⏳ need logo | local vendor |
| **Ferretería Veramar** | Proveedor local (aliado comercial) | ⏳ need logo | local vendor |

**✅ Hosted (2026-06-22):** CEO uploaded to `/home/ftpuser/odoo-dev/annual-rpt-2526/`;
staged to `/var/www/dev/flyers/partners/` and verified HTTP 200:
- `https://dev.ueipab.edu.ve/flyers/partners/logo-motores-por-la-paz.jpg`
- `https://dev.ueipab.edu.ve/flyers/partners/logo-orm.jpg`

Both are small **150×150** JPEGs (the Motores propeller mark is greyscale/low-res)
— fine as logo-wall thumbnails; request higher-res PNGs if we want them larger.
Remaining 7 partner logos still to source go in the same `partners/` folder.

**Grouping (9 partners):** mixing education partners with infrastructure and
local vendors on one wall is unusual — **group them** so each reads intentionally:
- **Aliados Académicos:** Kurios · MOA · Akdemia · **Motores por la Paz** · **ORM Venezuela**
- **Tecnología & Plataforma:** Digital Ocean · Odoo
- **Aliados Comerciales / Proveedores:** Comercial Caracas · Ferretería Veramar

**Note:** Motores por la Paz ↔ ORM are a coordinated pair (Motores por la Paz
manages the ORM olympic programme) — present them adjacent, or as one combined
"Motores por la Paz · ORM" card to avoid reading as two unrelated logos.

## 6. Content to gather (⏳ from the school)

- Per-lapso (I, II, III momento): theme + 2–3 headline achievements + photos.
- Year-in-numbers stats (students, teachers, graduandos, % aprobación, eventos).
- Director's letter (or I draft for approval).
- Confirmed achievement list (Kurios robotics ✅ already have; others?).
- Glenda announcement angle for parents (benefits, not tech).
- Final continuity-survey questions + where reaffirmations are stored.

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
- ⏳ Source the remaining **7** logos (Kurios, MOA, Akdemia, Digital Ocean, Odoo,
  Comercial Caracas, Ferretería Veramar) + the two local-vendor roles.
  DO + Odoo auto-grabbable. (2/9 done: Motores por la Paz + ORM.)
- ⏳ Per-lapso content, year-in-numbers stats, director's letter (§6).
- ⏳ **Timing** — when to publish/announce the report (see below).

**On "timing":** the enrollment-journey Step-0 blast is the conversion engine and
is already live (tokens issued, e.g. the CEO's sample link). The question is
**sequencing**: do we (a) publish the report first and let it *precede* the
journey blast — report builds the emotional case, then the journey email arrives
as the "act now" follow-up; (b) launch them *together* — the journey blast links
out to the report; or (c) send the report to families who have **not yet**
confirmed in the journey, as a re-engagement nudge. Recommendation: **(b)** —
embed the report link in the journey blast and also push it via Glenda WA/Telegram,
so every parent sees the credibility story at the moment of decision.

## 8. Suggested phasing

- **Phase 0 (now):** approve structure §3, confirm route + survey mechanism,
  start logo sourcing (§5) and content gathering (§6).
- **Phase 1:** build the static report page (mora-style enhanced), placeholder
  data, real Kurios/AI/partner sections.
- **Phase 2:** wire the tokenized continuity-survey CTA + tracking.
- **Phase 3:** announce via email blast + Glenda WA/Telegram; monitor
  reaffirmations.

## Related

[Enrollment Journey Wizard](ENROLLMENT_JOURNEY_WIZARD.md) ·
[Glenda Overview](GLENDA_AI_AGENT_OVERVIEW.md) ·
[Kurios Newsletter](ROBOTICS_KURIOS_NEWSLETTER.md) ·
[Budget/Continuity campaigns](PDVSA_CONTINUITY_CAMPAIGN.md) ·
[Pricing ground truth](../scripts/) · mora-policy page (`/var/www/dev/mora/`)
