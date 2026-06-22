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

**Recommended hybrid:**
- **Report page = static HTML/CSS** served via nginx alias — same pattern as
  mora-policy (`alias /var/www/dev/<dir>/`). Fast, fully designable, no Odoo load.
  Proposed route: **`/reporte-anual-2025-2026/`** (or `/annual-report/`).
- **Survey = tokenized Odoo route** for per-parent tracking of who reaffirmed.
  Reuse an existing pattern:
  - `partner.communication.ack` (used by PDVSA/Representante continuity campaigns), **or**
  - a `survey.survey` form, **or**
  - the `notice-ack/<token>` style public route.
  Each parent gets a **personalized link** (`…/reporte-anual-2025-2026/?t=<token>`
  or a Glenda/WA/email blast link) so the CTA pre-identifies them and records the
  reaffirmation against their partner record.

**Alternative:** full Odoo QWeb controller (`auth='public'`) rendering the whole
page per-token — better if we want heavy personalization (parent name, their
student's specific achievements). Trade-off: more dev + Odoo render load.

**Delivery:** announce via the same proven prod email-blast infra
([prod blast pattern](../scripts/send_robotics_kurios_recap.py)) + Glenda
WhatsApp/Telegram push, linking to the report.

## 5. Partner / ally ecosystem — logo asset checklist

⚠️ **None of the partner logos are on the server yet** (only UEIPAB's own
`ueipab_logo.png` / `school_logo.png` and the Kurios poster wordmark). To source
and host under e.g. `/var/www/dev/flyers/partners/` →
`https://dev.ueipab.edu.ve/flyers/partners/<name>.png`:

| Partner | Role (proposed copy) | Logo status | Likely source |
|---------|----------------------|-------------|---------------|
| **Kurios** | Robótica educativa & STEAM | ⏳ extract from posters / get clean PNG | kuriosedu.com / posters |
| **MOA (MoA School)** | Programa de inglés After School | ⏳ need PNG | ceo@moaeducation.com |
| **Akdemia** | Plataforma de gestión académica | ⏳ need PNG | akdemia.com |
| **Fundación La Paz** | *(role to confirm)* | ⏳ need PNG + role | — |
| **Digital Ocean** | Infraestructura cloud | ⏳ official brand asset | digitalocean.com/press |
| **Odoo** | ERP / gestión institucional | ⏳ official brand asset | odoo.com/brand-assets |
| **Comercial Caracas** | Proveedor local (aliado comercial) | ⏳ need logo | local vendor |
| **Ferretería Veramar** | Proveedor local (aliado comercial) | ⏳ need logo | local vendor |

**Note:** mixing education partners (Kurios/MOA/Akdemia) with infrastructure
(DO/Odoo) and **local vendors** (Comercial Caracas / Ferretería Veramar) on one
wall is unusual. Suggestion: **group them** — "Aliados Académicos", "Tecnología
& Plataforma", "Aliados Comerciales / Proveedores" — so each reads intentionally.
Confirm Fundación La Paz's role so its copy is accurate.

## 6. Content to gather (⏳ from the school)

- Per-lapso (I, II, III momento): theme + 2–3 headline achievements + photos.
- Year-in-numbers stats (students, teachers, graduandos, % aprobación, eventos).
- Director's letter (or I draft for approval).
- Confirmed achievement list (Kurios robotics ✅ already have; others?).
- Glenda announcement angle for parents (benefits, not tech).
- Final continuity-survey questions + where reaffirmations are stored.

## 7. Open questions / decisions

1. **Route name** — `/reporte-anual-2025-2026/` vs `/annual-report/` vs other?
2. **Survey mechanism** — `partner.communication.ack`, `survey.survey`, or new
   token route? (Affects how we track who reaffirmed.)
3. **Personalization depth** — generic page for all, or per-parent token with
   their student's name/achievements?
4. **Language** — Spanish only (parent-facing), correct.
5. **Fundación La Paz** role + which local-vendor logos we can actually obtain.
6. **Timing** — relative to the 2026–2027 continuity survey launch.

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
