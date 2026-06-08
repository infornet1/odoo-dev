# Odoo 17 Recruitment + Roster + AI Skill Evaluation System

**Created:** 2026-06-07 | **Updated:** 2026-06-07 (session 3)
**Status:** Phase 0 COMPLETE — Phase 1 (Glenda evaluation) design APPROVED, build pending  
**Priority:** 20% effort → 80% impact (MVP-first approach)

---

## Problem Statement

UEIPAB has historically hired professionals who do not meet the demands of a modern administrative paradigm. The goal is an innovative, multi-layered evaluation pipeline that produces a **confidence percentage (%)** before the final interview — reducing bias, gut-feel hiring, and mismatches.

**Target role (first use case):** Auxiliar de Contabilidad y Administración (Enfoque Tecnológico)

---

## ⚡ Real-World Status (2026-06-07) — Active Hiring in Progress

> **This is NOT a test scenario.** The job post is live and CVs are already arriving.

| Item | Status |
|------|--------|
| Job post published | ✅ 2026-06-06 |
| Publication channel | Instagram `@diarioeltigrense` — local news feed for El Tigre, Venezuela |
| CV intake active | ✅ CVs landing in Freescout (`recursoshumanos@ueipab.edu.ve`) |
| Odoo recruitment module | ✅ `ueipab_recruitment` v2.0.0 installed in testing |
| CV AI scoring pipeline | ✅ 29 applicants loaded — Tier A:1 / Tier B:21 / Tier C:7 |
| Daily cron | ✅ `/etc/cron.d/fs_cv_processor` — 09:00 VET daily |
| Glenda evaluation (any mode) | ⏳ Phase 1 — design complete, build pending |

**Key implication for architecture:** We are building the Odoo layer *after* intake has already started. Priority is to get the Kanban pipeline + applicant forms live quickly so existing CVs can be logged and evaluated — not to redesign the intake channel. The Freescout bridge (Option C) becomes more urgent than expected since CVs are already accumulating.

**Immediate action (Phase 0):** Manually create one `hr.applicant` per CV already received in Freescout. Paste Freescout conversation URL in chatter. This gives us real data to validate the evaluation pipeline against.

---

## Job Description — Auxiliar de Contabilidad y Administración (Enfoque Tecnológico)

**Published:** 2026-06-06 | **Source:** `@diarioeltigrense` Instagram | **Location:** El Tigre, Venezuela | **Modalidad:** Presencial

**Reporta a:** Administración Interna / Coordinación de Finanzas (enlace directo con Contador Público Externo)

### Por qué existe este cargo — Tres brechas que bloquean la Acta de Conformidad SENIAT

El colegio tiene como meta a mediano plazo obtener la **Acta de Conformidad SENIAT** ante una fiscalización. Hoy tres brechas concretas lo impiden:

| # | Brecha | Síntoma actual |
|---|--------|---------------|
| 1 | **Calendario fiscal SENIAT sin dueño** | Retenciones IVA (libro de compras), retenciones ISLR a proveedores, y planillas IVSS/FAOV/INCES no tienen un responsable de día a día — el contador externo no está presente para cumplirlas |
| 2 | **Archivos físicos desorganizados** | El contador externo reporta que no puede encontrar comprobantes, facturas de compra, planillas pagadas o expedientes de personal — cada visita empieza con una búsqueda, no con trabajo contable |
| 3 | **Sin conciliaciones bancarias** | Los extractos bancarios mensuales nunca se cruzan contra Odoo — SENIAT solicita conciliaciones en toda fiscalización; sin ellas el proceso se cae desde el inicio |

El ocupante de este cargo resuelve las tres brechas y libera al contador externo para hacer cierre, certificación y estrategia fiscal — no logística de documentos.

### Objetivo del Puesto
Ser el guardián de cumplimiento fiscal diario del colegio: mantener archivos organizados, cumplir el calendario SENIAT cada mes, realizar conciliaciones bancarias mensuales y servir de puente operativo con el Contador Externo — permitiendo al colegio alcanzar y mantener la Acta de Conformidad SENIAT.

### Responsabilidades Principales
- **Calendario Fiscal SENIAT:** Seguimiento y cumplimiento mensual de retenciones IVA (libro de compras), retenciones ISLR a proveedores, y planillas IVSS/FAOV/INCES — preparación de declaraciones y pago oportuno en el portal SENIAT
- **Conciliación Bancaria:** Descarga mensual de extractos bancarios + cruce contra registros en Odoo + identificación y documentación de partidas en tránsito
- **Archivo Físico y Digital:** Organización mensual de facturas de compra, comprobantes de retención emitidos/recibidos, planillas de organismos pagadas — disponibles para el Contador Externo en cualquier momento
- **Enlace con Contador Externo:** Preparación de paquete mensual de cierre (extractos reconciliados, retenciones, facturas, nómina) para entrega ordenada y completa
- **Gestión Transaccional:** Registro diario de ingresos (matrículas, mensualidades) y egresos (proveedores, servicios) en Odoo
- **Atención al Representante:** Verificación de pagos, emisión de facturas y solvencias
- **Archivos de Personal (RRHH):** Mantenimiento de expedientes físicos de empleados actualizados
- **Adopción Tecnológica:** Formación e implementación activa de herramientas de IA para automatizar tareas repetitivas

### Perfil Requerido
**Educación:**
- Técnicos Medios en Comercio/Contabilidad
- TSU en Contabilidad o Administración
- Estudiantes de últimos semestres de Contaduría Pública (ideales para desarrollo)
- Licenciados/Contadores Públicos bienvenidos si expectativa alineada a rol operativo de soporte

**Conocimientos Técnicos (evaluados en examen):**
- Principios de contabilidad básica (debe/haber, cuentas por cobrar/pagar, conciliaciones)
- Excel intermedio (tablas dinámicas, fórmulas básicas)
- Valor agregado: SAINT o Odoo previo

**Habilidades Blandas:**
- Alta orientación al detalle y orden
- Disposición y curiosidad por tecnología e IA
- Excelentes habilidades de comunicación (padres y representantes)

### Ofrecemos
- Formación técnica con IA aplicada a gestión contable
- Mentoría indirecta con Contador Externo experimentado
- Estabilidad laboral en institución educativa de trayectoria
- Ambiente colaborativo

### Salary Range (internal — not published)
- Budget 25-26: ~$230–$270 total (salary + bonus)
- Budget 26-27 (Sep 2026): ~$254–$294 total (+6% salary / +14% bonus)

---

## Advertisement Context — Blind Ad Analysis

**Published:** 2026-06-06 | **Channel:** `@diarioeltigrense` Instagram (El Tigre, Venezuela) | **Deadline:** 2026-06-30

**Ad is intentionally blind** — reads "Empresa Educativa Líder Busca..." with zero mention of UEIPAB. The only traceable identifier is the email domain `@ueipab.edu.ve` in `recursoshumanos@ueipab.edu.ve`. Motivated candidates who Google the domain self-select further.

**What the ad already promises (critical for pipeline design):**
- `EXAMEN TÉCNICO` — candidates arrive expecting to be evaluated. Zero friction introducing our AI assessment layer.
- `HERRAMIENTA DE INTELIGENCIA ARTIFICIAL` — the AI angle is in the ad itself. Tech-curious candidates self-sort in; tech-averse self-sort out before applying.
- Target profile: `INICIÁNDOSE` — deliberately entry/junior level. Salary range is aligned. Senior accountants expecting $500+ will self-filter via the roster salary question.

**Only landing place: Freescout** — `recursoshumanos@ueipab.edu.ve`. Every CV arriving since 2026-06-06 is a Freescout conversation. This IS the current candidate database.

---

## Angle Analysis — Gaps & Insights (Updated with Real Context)

| Angle | Insight |
|-------|---------|
| **Volume + deadline** | June 30 deadline = 23 days. Could receive 5 CVs or 80. Pipeline must handle both. Build for 50, test with first 5. |
| **CV format chaos** | Venezuelan applicants send via: PDF email attachment, email body text, WhatsApp message, Instagram DM. Freescout catches email only. DMs are lost unless manually forwarded. |
| **El Tigre market** | TSU-level candidates likely dominant. Licenciados apply but salary expectation gap filtered by Roster survey Section 3. |
| **Blind ad advantage** | No UEIPAB name = no preconceptions. Candidates judged on merit, not school reputation. Also means no one can "prep" for a specific employer. |
| **Examen Técnico already expected** | The ad promises it. NOT delivering a real technical test would be the surprise. Our AI evaluation fulfills the implicit contract the ad makes. |
| **Contador Externo interface** | The role is data *handoff* to an external accountant. Evaluation should test: can this person organize and deliver information cleanly, not just know theory? |
| **Instagram DMs gap** | Some candidates will DM the news page or school Instagram directly. Those never reach Freescout. Need a manual fallback (recruiter forwards to `recursoshumanos@`). |
| **Venezuelan connectivity reality** | Smartphones dominant, laptops rare. Telegram works on minimal data (2G/3G). Web forms may fail on slow connections. Telegram-first evaluation is the RIGHT choice for this market specifically. |

---

## AI Shortlisting from Freescout — Feasibility & Design

### Can AI identify a preliminary shortlist from Freescout CVs?

**Yes — and this is the highest-leverage 20% action before the Odoo pipeline is fully built.**

**How it works:**
```
Freescout conversations (recursoshumanos@)
    ↓
Script reads email body + attachment text via Freescout REST API
    ↓
Claude Haiku evaluates each CV against job requirements
    ↓
Returns: score 0-100 + tier (A/B/C) + key signals + red flags
    ↓
Odoo hr.applicant created with score pre-filled
    ↓
HR reviews tier-A list → approves shortlist
    ↓
Blast email sent to shortlisted candidates → Glenda Telegram invite
```

**Claude scoring prompt (per CV):**
```
Role: "Auxiliar de Contabilidad y Administración (Enfoque Tecnológico)"
Target profile: Entry/junior level, Venezuelan school, $250-300/month budget
Ad already promised: technical exam + AI training

Evaluate this CV/email:
{cv_text}

Score 0-100 on:
- Education match (30%): TSU/técnico medio in accounting/admin = full points
- Technical foundation (30%): mentions debe/haber, Excel, reconciliation, accounting systems
- Tech openness (20%): mentions tech tools, learning, AI, computers, Odoo/SAINT
- Communication signals (20%): email is well-written, organized, professional

Return JSON: {
  "score": int,
  "tier": "A" | "B" | "C",
  "education": "one line",
  "tech_signals": ["..."],
  "red_flags": ["..."],  // e.g. "5 years exp → may expect senior salary"
  "summary": "2 sentences max"
}
```

**Tier definitions:**
- **Tier A (score ≥ 70):** Shortlist → send blast email invitation to Telegram evaluation
- **Tier B (score 45-69):** Hold → review manually if Tier A pool is thin
- **Tier C (score < 45):** Archive in Odoo, polite rejection email later

### The Self-Selection Signal — Venezuela Context

> *"The act of engaging with the process is itself a signal."*

This is the key insight for Venezuelan market context:

A candidate who receives the blast email → taps the Telegram deep-link → opens `@GlendaUeipabBot` → completes an 8-turn evaluation is demonstrating:

1. **Digital literacy** — navigates Telegram bot without instructions (essential for the AI-adoption role)
2. **Commitment** — invests 15–20 minutes in a structured process when they could have just sent a WhatsApp "vi su anuncio"
3. **Tech openness** — didn't abandon at "a Telegram bot will evaluate you"
4. **Connectivity baseline** — has a smartphone and sufficient data for a chat session

In a market where many candidates send a WhatsApp voice note as their "CV application," someone who completes a Glenda evaluation is already in the top quartile of digital readiness for this specific role — *regardless of their accounting score*.

**Important caveat:** Some excellent candidates may be digitally capable but lack data/WiFi at the moment. The blast email should include a fallback: *"¿No tienes acceso a Telegram? Responde este correo para coordinar una evaluación presencial."* Never let connectivity be the disqualifier for an otherwise strong candidate.

### Operator Context — CEO as Sole HR

**Critical constraint:** Gustavo Perdomo is UEIPAB's CEO and is running this hiring process alone due to school budget limitations. There is no HR team or recruiter. This fundamentally changes the architecture requirements:

| Assumption | Reality |
|-----------|---------|
| "HR manually logs CVs" | ❌ No HR. CEO has no time for data entry. |
| "Recruiter reviews shortlist daily" | ❌ CEO reviews once, acts on output |
| "Manual Freescout → Odoo bridge is Phase 0" | ❌ Replaced by automated one-time load |
| "Build slowly, validate with team" | ❌ Must work autonomously from day 1 |

**Design principle shift:** Every step that requires human attention must produce a **decision-ready output**, not raw data. The system must tell the CEO *what to do next*, not show him more data to interpret.

**Revised Phase 0:** A one-time script reads all existing Freescout CVs → Claude scores each → Odoo applicants created automatically. CEO opens Odoo, sees a ranked list with tier badges, and acts on it. Zero manual data entry.

**Live count (2026-06-07, ~24h after publication):** 25 external CVs in `recursoshumanos@` mailbox (conv_ids 46987–47018). Early signals from subject lines alone:
- 4+ Licenciados/as flagged by subject ("LCDO.", "LCDA.") → salary filter needed
- 1 candidate quoted the AI angle verbatim in subject → immediate Tier A signal
- 1 CV arrived as WhatsApp `.docx` forwarded to email → Venezuelan market pattern confirmed
- Script must exclude internal system emails (`@ueipab.edu.ve` sender) and pre-June-6 non-CV convs

**Script:** `scripts/fs_cv_loader.py` — one-time run, idempotent (skips if `hr.applicant` already exists for that Freescout conv_id)

---

## Experimental Frame — Building While Running

This process is being built simultaneously with a live hiring round. That is intentional and valuable:

- **Real CVs = real test data** for the evaluation algorithm
- **Pipeline gaps surface immediately** (e.g., Instagram DM CVs not captured)
- **Scoring calibration** happens against actual candidates, not hypotheticals
- **The recruiter (Gustavo) IS the feedback loop** — every manual adjustment refines the system

This is a legitimate product methodology: build → measure → learn → iterate, with a 23-day deadline forcing scope discipline.

**Risk to manage:** Don't let the experiment slow down a real hiring decision. If a clearly excellent candidate emerges from Freescout, hire them. The pipeline serves the decision, not the other way around.

---

## System Layers

| Layer | Purpose | Effort |
|-------|---------|--------|
| **1. Recruitment** | Standard applicant tracking, job posting, pipeline stages | Native Odoo 17 |
| **2. Roster Pre-Approval** | Basic eligibility gate (availability, location, salary, legal status) | Survey module |
| **3. AI Skill Evaluator** | Practical technical exercises scored by AI | Custom + Claude API |
| **4. Confidence Score** | Weighted aggregate → % fed into human interview stage | Custom field |

---

## Odoo 17 Community Module Inventory

### Available natively (Community, no cost) — **verified installed in `testing` 2026-06-07**

| Module | Technical Name | Status | What it provides |
|--------|----------------|--------|-----------------|
| Recruitment | `hr_recruitment` | ✅ installed | Kanban pipeline, applicant model `hr.applicant`, job posts |
| Employees | `hr` | ✅ installed | Employee model, department/job position linkage |
| Skills | `hr_skills` | ✅ installed | `hr.skill`, `hr.skill.type`, skill levels — already on employee |
| Surveys | `survey` | ✅ installed | Multi-page questionnaires, scoring, public URLs |
| Discuss | `mail` | ✅ installed | Threaded messaging, bot hooks |
| Calendar | `calendar` | ✅ installed | Interview scheduling |

### NOT available in Community (Enterprise-only) — **verified 2026-06-07**

| Feature | Enterprise module | Status | Workaround |
|---------|-------------------|--------|------------|
| Recruitment + Survey link | `hr_recruitment_survey` | ⚠️ uninstalled (available but needs install) | Install it — it's Community, just not auto-installed |
| Skills on Applicant | `hr_appraisal` | ❌ uninstallable (Enterprise) | Custom: `hr.applicant.skill` one2many |
| Video interviews | none | n/a | Zoom/Meet link in chatter |

> **Key finding:** `hr_recruitment_survey` is **LGPL-3 Community** — it's simply uninstalled. License confirmed from manifest. Installing it gives a native "Send Survey" button on applicants with zero custom code. This is the highest-leverage first step.
>
> **Install command:**
> ```bash
> docker exec odoo-dev-web python3 /usr/lib/python3/dist-packages/odoo/odoo-bin \
>   -d testing --stop-after-init -i hr_recruitment_survey \
>   --config /etc/odoo/odoo.conf
> ```
> Or via Odoo UI: Settings → Apps → search "Interview Forms" → Install.

### External OSS tools (zero cost)

| Tool | Role | Integration |
|------|------|-------------|
| Claude API (Haiku 4.5) | AI evaluator engine | Already configured in `/opt/odoo-dev/config/anthropic_api.json` |
| Google Forms (optional) | Richer UX for skill test | Webhook → Odoo via existing bridge pattern |
| LibreOffice Calc exercise | Practical accounting test | Email attachment, manual review or AI grading |

---

## Architecture Proposal

```
[Job Post published]
        ↓
[Applicant submits CV]  ← hr.applicant created (Stage: Nuevo)
        ↓
[Roster Pre-Screen]     ← Survey sent via email (public URL)
   Pass / Fail          → Stage: Pre-Aprobado / Descartado
        ↓
[AI Skill Evaluation]   ← Odoo Discuss bot or email exercise
   Practical test       → AI grades → writes confidence_%
        ↓
[Confidence Score]      ← Weighted: Roster(30%) + Skills(70%)
   Stored on hr.applicant
        ↓
[Human Interview]       ← Recruiter sees % on applicant card
        ↓
[Hire / Reject]
```

### Data model additions (custom fields on `hr.applicant`)

```python
# In a new module: ueipab_recruitment_eval
ueipab_roster_score    = fields.Float("Roster Score %", default=0.0)
ueipab_skill_score     = fields.Float("AI Skill Score %", default=0.0)
ueipab_confidence_pct  = fields.Float("Confidence %", compute="_compute_confidence", store=True)
ueipab_eval_state      = fields.Selection([
    ('pending', 'Pendiente'),
    ('roster_sent', 'Roster Enviado'),
    ('roster_pass', 'Roster Aprobado'),
    ('roster_fail', 'Roster Fallido'),
    ('ai_sent', 'Evaluación Enviada'),
    ('ai_done', 'Evaluación Completa'),
    ('interview', 'Entrevista'),
], default='pending')
ueipab_ai_eval_notes   = fields.Text("AI Evaluation Notes")
```

```python
@api.depends('ueipab_roster_score', 'ueipab_skill_score')
def _compute_confidence(self):
    for rec in self:
        rec.ueipab_confidence_pct = (
            rec.ueipab_roster_score * 0.30 +
            rec.ueipab_skill_score  * 0.70
        )
```

---

## Layer 1 — Recruitment (Native Odoo 17)

### Kanban pipeline — live state (testing, 2026-06-07, cleaned up)

7 stages — 3 kept/renamed Odoo defaults + 4 custom (`ueipab_recruitment`).

| ID | Seq | Name | Fold | Hired | Source |
|----|-----|------|------|-------|--------|
| 1 | 0 | **New** | No | No | Odoo default |
| 13 | 5 | **Pre-Screening** | No | No | `ueipab_recruitment` |
| 15 | 10 | **Pre-Approved** | No | No | `ueipab_recruitment` |
| 14 | 15 | **Technical Evaluation** | No | No | `ueipab_recruitment` |
| 3 | 20 | **Interview** | No | No | Odoo default (renamed) |
| 6 | 40 | **Hired** | Yes | ✅ Yes | Odoo default (renamed) |
| 16 | 50 | **Rejected** | Yes | No | `ueipab_recruitment` |

**Deleted:** Initial Qualification (id=2), Second Interview (id=4), Contract Proposal (id=5) — none had applicants.

### Stage meaning in the UEIPAB flow

| Stage | Trigger | Who acts |
|-------|---------|---------|
| **New** | CV arrives → cron scores it → `hr.applicant` created | Cron (automatic) |
| **Pre-Screening** | CEO sends 3-question confirmation email | CEO manually |
| **Pre-Approved** | Candidate replies: salary ✅ + location ✅ + Telegram ✅ | CEO manually |
| **Technical Evaluation** | CEO clicks "Invitar a Evaluación Presencial" → appointment email sent | Button on form |
| **Interview** | Glenda scores ≥ threshold + consensus HIGH/MEDIUM | CEO manually after review |
| **Hired** | Offer accepted — marks hired in Odoo | CEO manually |
| **Rejected** | Any point of disqualification — folded from Kanban | CEO manually |

### Job Position: Auxiliar de Contabilidad y Administración

**Draft Job Description (to be refined):**

```
Puesto: Auxiliar de Contabilidad y Administración
Institución: UEIPAB (Unidad Educativa Integral Privada Antonio Borjas)
Departamento: Administración

Responsabilidades principales:
- Registro y conciliación de cuentas por cobrar / pagar
- Facturación electrónica y control de pagos de mensualidades
- Soporte al sistema Odoo 17 (módulo de contabilidad)
- Cálculo y seguimiento de nómina quincenal en moneda USD/VEB
- Gestión de archivos físicos y digitales de representantes
- Generación de reportes financieros básicos y estados de cuenta
- Coordinación con proveedores y seguimiento de órdenes de compra

Perfil requerido:
- TSU o Licenciado/a en Contabilidad, Administración, o carrera afín
- Conocimiento de contabilidad venezolana (SENIAT, ISLR, IVA, IGTF)
- Manejo de herramientas digitales (Google Sheets, Excel, correo electrónico)
- Deseable: experiencia en ERP (Odoo, SAP, o similar)
- Disponibilidad: jornada completa, presencial en [Ciudad]
- Residencia en [Ciudad] o área metropolitana

Competencias valoradas:
- Atención al detalle y precisión numérica
- Organización y gestión del tiempo
- Comunicación efectiva con representantes y docentes
- Actitud de mejora continua y apertura tecnológica

Beneficios:
- Salario en USD (componentes: salario base + bono + cesta ticket)
- Ambiente colaborativo y propósito educativo
```

---

## Layer 2 — Eligibility Gate (REVISED 2026-06-07)

### Strategic pivot: drop the full roster survey

**Original design:** 10-question Odoo survey → auto-scored → `ueipab_roster_score`

**Revised design:** 3-question confirmation email → binary gate → advance to Glenda

**Why the pivot:**
- `fs_cv_loader.py` already reads the actual CV document (PDF/DOCX) with Claude — the education, experience, and accounting knowledge pre-screen that the roster survey was designed to provide is already done at CV scoring time.
- 27 real candidates are scored and waiting. Building a full survey pipeline takes 4h of dev. Venezuelan candidates don't wait 3 weeks.
- The salary gate, location check, and availability check can be asked in one personal email — no survey infrastructure needed.
- The high-value differentiator was always Layer 3 (Glenda Telegram evaluation), not Layer 2. Build that instead.

### Revised Layer 2: Confirmation Email (3 questions)

CEO sends a short personal email to Tier A + top Tier B candidates (prioritized by: no salary_risk first, then by score):

```
Asunto: Evaluación — Auxiliar de Contabilidad y Administración | UEIPAB

Estimada/o [Nombre],

Hemos revisado su CV y nos gustaría continuar con su evaluación.
Antes de avanzar, necesitamos confirmar tres puntos:

1. La remuneración mensual total del cargo es de $250–$300 (salario + bono).
   ¿Está dentro de su expectativa? (Sí / No)

2. El cargo es presencial en El Tigre, Anzoátegui, de lunes a viernes.
   ¿Tiene disponibilidad inmediata? (Sí / No)

3. La evaluación técnica se realiza por Telegram con nuestra asistente IA Glenda.
   ¿Tiene Telegram instalado y disponible? (Sí / No)

Si los tres puntos son "Sí", le enviamos el enlace de evaluación de inmediato.

Saludos,
Administración UEIPAB
```

**Outcome mapping:**
| Response | Action | eval_state |
|----------|--------|------------|
| All 3 = Sí | Send Glenda Telegram deep-link | `roster_pass` |
| Salary = No | Close politely | `roster_fail` |
| Location/avail = No | Hold or close | `roster_fail` |
| No response in 48h | Mark inactive | `roster_fail` |

**Odoo tracking:** CEO notes the email confirmation manually in `ueipab_ai_eval_notes` + flips `eval_state` via the form. The `ueipab_roster_score` field is repurposed: `1.0` = confirmed fit, `0.0` = not confirmed. No survey.user_input linkage needed for this position.

### Who gets the confirmation email first

Priority order from current 27-CV batch:

**Immediate (Tier A, no salary risk):**
1. Edglis Rondón — 75/100, no salary risk ← contact today

**Second wave (Tier B ≥60, no salary risk):**
2. YOERLYS JIMÉNEZ — 68/100, no salary risk
3. Ivanethe Guatache — 62/100, salary risk (ask salary Q first)
4. Valleinnys Naimalhys López León — 62/100, salary risk

**Third wave (Tier B ≥60, salary risk — salary Q is critical):**
5. D Jose Ramirez Reyes — 62/100
6. José Arriojas — 62/100
7. Caterin Lineros, Isomaris Duran, Norkis Hernández, etc. — 58/100

**Hold (Tier C or score <50):**
- Enderson Medina (42), Lirida Olivero Mejias (32), Nohely García (32), carliannys cedeño (32)

### What happens to the original roster survey design

The 10-question survey design (Sections 1–5 below) is kept for reference. It may be useful for:
- Future positions where volume is higher and personal emails don't scale
- Positions where the CV AI score is less reliable (e.g. highly specialized roles)
- A more formal HR process once a dedicated HR person is hired

**Original Survey Design (archived — not built for this position):**

*Section 1: Disponibilidad* (pass/fail) — ¿Jornada completa L-V? / ¿Restricción en 4 semanas?
*Section 2: Ubicación* — ¿Reside en El Tigre?
*Section 3: Expectativa Salarial* — rango selección + ¿dentro de expectativa?
*Section 4: Estatus Legal* — cédula vigente + restricción laboral
*Section 5: Autoevaluación* — ERP experience + IVA knowledge

Scoring: weighted total → `ueipab_roster_score`. Threshold ≥70% to advance.

---

## Layer 3 — AI Skill Evaluator

### Exercise Design (anti-gaming focused)

**Principle:** Test *reasoning*, not memorization. Exercises change per applicant using parameterized templates.

#### Exercise A — Practical Spreadsheet Scenario

```
Email to applicant (generated by Odoo):

"Adjuntamos un archivo con 20 transacciones de una semana de operaciones del colegio.
Tiene 45 minutos para:
1. Clasificar cada transacción en la cuenta contable correcta (Plan de Cuentas adjunto).
2. Calcular el saldo de cada cuenta al cierre del período.
3. Identificar si existe alguna discrepancia o transacción sospechosa.
Envíe su respuesta como archivo .xlsx respondiendo este correo."
```

- Template varies: amounts, account names, one intentional error changes per candidate.
- AI (Claude Haiku) grades the returned file description or screenshot.

#### Exercise B — Venezuelan Tax Quiz (dynamic)

5 questions drawn from a pool of 20, covering:
- IVA alícuota vigente (16%) y casos de exención
- IGTF: qué es, cuándo aplica, tasa actual
- ISLR: retención a personas naturales, tabla de tarifas
- Declaración de retenciones SENIAT (fechas, portal)
- INCES, SSO, FAOV: diferencia entre aporte patronal y trabajador

Implemented as Odoo Survey with automatic scoring.

#### Exercise C — Document Processing Scenario

```
"Recibimos el siguiente correo de un representante [scenario text].
Redacte la respuesta apropiada y describa los pasos que seguiría para
procesar su solicitud en el sistema."
```

AI evaluates: tone, accuracy, steps completeness, Venezuelan context awareness.

### AI Grading Flow

```python
# Pseudo-code for the AI evaluator cron / webhook handler
def evaluate_applicant_submission(applicant_id, submission_text):
    prompt = f"""
    You are evaluating a candidate for "Auxiliar de Contabilidad" at a Venezuelan school.
    
    Candidate submission:
    {submission_text}
    
    Answer key context:
    {ANSWER_KEY_FOR_THIS_APPLICANT}
    
    Score from 0–100 on:
    - Technical accuracy (40%)
    - Reasoning quality (30%)
    - Venezuelan fiscal context awareness (20%)
    - Communication clarity (10%)
    
    Return JSON: {{"score": int, "strengths": [...], "gaps": [...], "summary": "..."}}
    """
    response = claude_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )
    result = json.loads(response.content[0].text)
    applicant.ueipab_skill_score = result["score"]
    applicant.ueipab_ai_eval_notes = result["summary"]
```

### Anti-Gaming / Cheating Controls — Full Stack

**The core problem:** A candidate can have ChatGPT or Claude open in another tab while Glenda evaluates them via Telegram. No single control prevents this — the defense is layered.

#### Layer 1 — Question design (hardest to fake)

Glenda never asks fact-recall questions. She asks applied, context-specific scenarios:

> ❌ "¿Cuál es la tasa de IVA?" — Googleable in 3 seconds
> ✅ "Un representante dice que pagó su mensualidad pero el sistema la muestra pendiente. Explícame paso a paso qué harías en los primeros 10 minutos."

No AI gives a perfect answer to UEIPAB-specific workflows because the specifics only exist in Glenda's system prompt. Generic AI answers fail on specificity.

#### Layer 2 — Venezuelan fiscal specifics

Questions anchored to Venezuelan context: SENIAT forma 30, retenciones IVA, Gaceta Oficial updates, IVSS/FAOV rates. ChatGPT gets these wrong or outdated. Claude scores the gap between claimed expertise and actual answer quality.

#### Layer 3 — Adaptive probing (Turn N+1 always follows up Turn N)

After any answer, Glenda fires an unpredictable follow-up:
> *"Interesante. Dijiste que usarías la cuenta 1.1.03 — ¿por qué esa y no la 2.1.01? Dame el razonamiento."*

Copy-paste AI answers don't anticipate follow-ups. The second answer always exposes whether the first was genuine.

#### Layer 4 — Response timing (Telegram timestamps)

Every Telegram message has a server timestamp. Glenda logs these. Patterns flagged for review:
- Every answer arrives in exactly 30–60s → AI generation cadence
- Answers in < 8 seconds → impossible to type a 3-sentence reply
- Long gap mid-conversation → switching tabs, looking things up

#### Layer 5 — Identity at Turn 1

Full name + cédula, cross-checked against `hr.applicant`. Mismatch → session ends. This blocks someone sending a more qualified friend instead.

#### Layer 6 — Dual-AI scoring consensus (Claude + OpenAI credits)

**This is the confidence mechanism that answers "how do I know I can trust the score?"**

After the 8-turn conversation ends, the same transcript is scored independently by **two different AI systems**:

```
Claude Haiku scores the transcript  → score A
GPT-4o-mini scores the transcript   → score B
Delta = |A - B|
```

| Delta | Meaning | Odoo indicator | Action |
|-------|---------|----------------|--------|
| ≤ 15 pts | Both AIs agree | ✅ HIGH consensus | Advance pipeline normally |
| 16–25 pts | Mild disagreement | ⚠️ MEDIUM | Review transcript notes |
| > 25 pts | Significant disagreement | 🔴 LOW — flag | Hold — human reads transcript before advancing |

**Why low consensus flags gaming:** A candidate using ChatGPT produces textbook-perfect, overly-structured answers. Claude may score those highly. GPT-4o-mini, instructed to penalize "AI-generated pattern vs. applied Venezuelan context," often scores them lower. The disagreement IS the signal.

**Cost:** GPT-4o-mini = $0.15/1M input tokens. A full 8-turn transcript ≈ 2,000 tokens = $0.0003 per candidate. Negligible.

**Scoring prompt instruction (both models receive this):**
> *"Penalize answers that are textbook-perfect but lack applied context, specific examples, or acknowledged uncertainty. Real practitioners make small errors and say 'depende.' AI-generated answers are typically over-structured and complete. Reward genuine struggle and practical specificity."*

**Odoo fields added for dual-AI:**
- `ueipab_skill_score` — Claude Haiku score (primary, 0–100)
- `ueipab_skill_score_gpt` — GPT-4o-mini score (secondary, stored in ai_eval_notes or new field)
- `ueipab_eval_consensus` — Selection: `high` / `medium` / `low`

**Example Odoo display:**

```
Glenda Evaluation Result
  Claude score:    78/100
  GPT-4o score:    74/100
  Consensus:       ✅ HIGH (Δ=4)
  Confidence %:    76.6%  ← reliable, advance to interview
```
vs.
```
Glenda Evaluation Result
  Claude score:    82/100
  GPT-4o score:    55/100
  Consensus:       🔴 LOW (Δ=27) — review transcript
  Confidence %:    ⚠️ flagged — do not advance without review
```

#### Layer 7 — Human interview is the absolute backstop

The confidence % decides **who gets the interview slot** — it never hires anyone. A candidate who gamed every AI layer still has to sit in front of you in person, no phone, for 30 minutes. That layer is unjammable.

**What "gaming" still can't be caught:**
- A knowledgeable friend physically next to the candidate coaching in real time (no digital trace)
- Someone who genuinely knows accounting but sends a substitute for the interview (identity gap)
- **Mitigation:** The 3-question confirmation email asks for a cédula-confirmed name. The interview asks for physical ID. These are the same person.

---

## Layer 4 — Confidence Score Display

**Revised formula (2026-06-07):**
```
confidence_pct = cv_score × 0.40 + glenda_score × 0.60

where:
  cv_score     = ueipab_skill_score set by fs_cv_loader (Claude read actual PDF)
  glenda_score = average(claude_eval_score, gpt_eval_score) — only when consensus ≥ medium
               = claude_eval_score only — when GPT not yet run or consensus = high
```

`ueipab_roster_score` repurposed: `1.0` = email confirmation received, `0.0` = pending. Binary gate, not scored.

**Odoo form panel (revised):**

```
┌─ Evaluación de Confianza — UEIPAB ────────────────────────────────┐
│ Estado Evaluación:   [roster_pass      ▼]                          │
│                                                                    │
│ CV Score (Claude):   75 / 100                                      │
│ Glenda (Claude):     78 / 100                                      │
│ Glenda (GPT-4o):     74 / 100    Consenso: ✅ HIGH (Δ=4)          │
│ Confianza Total:     76.6 %                                        │
│                                                                    │
│ Freescout Conv #:    46999   [Ver en Freescout →]                  │
│                                                                    │
│ Notas IA:  [fs_cv_loader 2026-06-07 | text-extracted              │
│             Tier A | Score 75 | No salary risk                    │
│             Educación: TSU Contaduría — IUPSM El Tigre            │
│             ...]                                                   │
│                                                                    │
│  [Enviar Filtro de Elegibilidad]  [Invitar a Evaluación Telegram]  │
└────────────────────────────────────────────────────────────────────┘
```

**Confidence thresholds:**
- ≥ 80% + consensus HIGH → 🟢 "Listo para entrevista"
- 60–79% + consensus HIGH/MEDIUM → 🟡 "Considerar con reservas"
- Any score + consensus LOW → 🔴 "Revisar transcript antes de avanzar"
- < 60% → 🔴 "No recomendado"

**New Odoo fields needed (Phase 1 model update):**
- `ueipab_skill_score_gpt` — Float, GPT-4o-mini score (0–100)
- `ueipab_eval_consensus` — Selection: `('high','✅ Alta')`, `('medium','⚠️ Media')`, `('low','🔴 Baja')`

---

## MVP Scope (3–5 real applicants)

### Phase 0 — CV pipeline live (DONE ✅ — 2026-06-07)

1. ✅ `ueipab_recruitment` module v2.0.0 installed in testing
2. ✅ `fs_cv_loader.py` — 29 CVs scored and loaded LIVE into Odoo testing
3. ✅ Custom fields: `ueipab_cv_score`, `ueipab_cv_tier`, `ueipab_cv_salary_risk`, `ueipab_cv_extract_method`, `ueipab_eval_state`, `ueipab_confidence_pct`, `ueipab_ai_eval_notes`, `ueipab_freescout_conv_id`, `ueipab_evaluation_mode`, `ueipab_skill_score_gpt`, `ueipab_eval_consensus`
4. ✅ Salary risk flagged on 22/29 candidates
5. ✅ Confidence formula: `cv_score × 0.40 + glenda_score × 0.60`
6. ✅ Daily cron: `/etc/cron.d/fs_cv_processor` — 09:00 VET, idempotent

**Current leaderboard (2026-06-07, 29 CVs):**

| Rank | Candidate | CV Score | Salary Risk | Status |
|------|-----------|----------|-------------|--------|
| 1 🟢 | Edglis Rondón | 72/100 | None | **Priority — contact now** |
| 2 🟡 | YOERLYS JIMÉNEZ | 68/100 | None | Second wave |
| 3 🟡 | Valleinnys Naimalhys López León | 68/100 | ⚠️ | Confirm salary first |
| 4 🟡 | Norkis Hernández | 62/100 | ⚠️ | Confirm salary first |

### Phase 1 — Confirmation email + Glenda evaluation (THIS WEEK, ~7h effort)

**Replaces:** original roster survey build (~4h) + survey automation (~4h) = saves ~5h

1. ⏳ CEO sends 3-question confirmation email to Tier A + top Tier B (manual, personal)
2. ⏳ Confirmed candidates → flip `eval_state = confirmed` in Odoo form
3. ⏳ Evaluation station account (`recursoshumanos@ueipab.edu.ve`) created via Odoo UI — used as shared login on school computer during in-person sessions
4. ⏳ Build Glenda `RECRUIT_*` OdooBot handler — detects evaluation session, runs 8-turn conversation
5. ⏳ Dual-AI scoring (Claude + GPT-4o-mini on transcript) → writes `ueipab_skill_score`, `ueipab_skill_score_gpt`, `ueipab_eval_consensus` to `hr.applicant`

**Confidence formula:**
```
confidence_pct = cv_score × 0.40 + glenda_score × 0.60
```
- `ueipab_cv_score` — set by `fs_cv_loader.py` (Claude reads actual PDF)
- `ueipab_skill_score` — set by Glenda at end of evaluation session (0–100)

### Phase 2 — Iterate and scale (AFTER first hire)

1. Deploy `ueipab_recruitment` to production
2. Set up cron on prod server
3. Refine Claude scoring prompt based on real evaluation outcomes
4. Consider roster survey only if volume exceeds ~50 CVs/position

**Total revised MVP: ~5h across 1 week** (vs. original 18h across 3–4 weeks)

---

## Feasibility Assessment

| Question | Answer |
|---------|--------|
| Entirely within Odoo 17 Community? | **~80% yes.** Recruitment + Survey native. AI grading needs custom code (same pattern as existing `ueipab_ai_agent`). |
| Need external tools? | Only Claude API (already configured). No n8n, no local LLM needed. |
| Simplest MVP for 3–5 applicants? | Phase 0 (4h): manual pipeline + survey + spreadsheet score entry. Proves concept before building automation. |
| How to prevent cheating? | Parameterized exercises + time-boxed tokens + reasoning-over-answer grading rubric. |

---

## 20/80 Priority Map

| Action | Effort | Impact |
|--------|--------|--------|
| Create Odoo Job Post + pipeline stages | 30 min | High — visible, structured process |
| Draft Job Description (above) | 1h | High — clarity for all evaluators |
| Build Roster Survey (10 Qs) | 2h | High — gates unqualified candidates early |
| Add confidence % field + manual entry | 1h | High — recruiter UX |
| Parameterize skill exercise template | 2h | Medium — anti-gaming |
| AI auto-grading via Claude | 4h | High — scales to many applicants |
| Full automation (stage triggers) | 6h | Medium — manual process works for MVP |

**Start here (Week 1, ~4h total):**
1. Job Post + pipeline in Odoo
2. Roster Survey
3. Confidence % field (manual entry for now)
4. Run with first 2–3 real applicants → validate before automating

---

## Salary Range — Real Data (Dry-Sync from Production, 2026-06-07)

Production has **43 active contracts** (V2 salary model). Key benchmarks:

| Metric | Base Salary | Bonus | Total |
|--------|-------------|-------|-------|
| Minimum (excl. symbolic) | $95.69 | $55.69 | $151.38 |
| P25 (25th percentile) | ~$112 | ~$118 | ~$230 |
| Median | $127.66 | $139.67 | $267.33 |
| P75 | ~$154 | ~$163 | ~$314 |
| Maximum | $285.39 | $249.52 | $534.91 |
| Average | — | — | $291.61 |

### Budget 26-27 Projection (Sep 1, 2026)

Maximum allowed increase: **20% total** — split as:
- **+6%** to base salary (`ueipab_salary_v2`)
- **+14%** to regular bonus (`ueipab_bonus_v2`)

Note: the extra bonus (`ueipab_extrabonus_v2`) is not in the standard increase formula.

### Recommended Range for Auxiliar de Contabilidad (26-27 budget)

For a new hire at the administrative assistant level, the comparable band is the P25–P50 range of current non-director staff, projected to Sep 2026:

| Component | Min (P25 → 26-27) | Max (P50 → 26-27) |
|-----------|-------------------|-------------------|
| Base Salary | ~$119 | ~$135 |
| Bonus | ~$135 | ~$159 |
| **Total** | **~$254** | **~$294** |

**Roster Survey Section 3 answer:** Target range **$250–$300/month total** (salary + bonus). Candidates expecting above $350 are outside budget for this role.

### Wage Range Advisor (module: `ueipab_recruitment`)

`hr.recruitment.wage.range` TransientModel in `models/wage_range.py`:
- Lookup active contracts for the same `job_id`
- Falls back to global P25–P50 if no matches
- Applies 26-27 projection rates automatically
- Recruiters access it from the job position form (Phase 2 — UI not yet wired)

---

## CV Intake — Email Alias Options

**Current flow:** CVs arrive at `recursoshumanos@ueipab.edu.ve` → Freescout conversation created → HR processes manually.

**Odoo alias status (verified 2026-06-07):** Alias domain NOT SET, no incoming mail server, all job position aliases inactive. Native email intake requires infrastructure work not justified at Phase 0 scale.

| Option | Approach | Effort | Phase |
|--------|---------|--------|-------|
| **A — Native Odoo Alias** | New `empleo@` mailbox, Odoo IMAP polling, DNS change | High | ❌ Skip |
| **B — Manual Entry** | HR creates `hr.applicant` in Odoo manually, pastes Freescout conv URL in chatter | Zero | ✅ Phase 0 |
| **C — Freescout Bridge Script** | Cron polls Freescout REST API for convs tagged `#cv-recibido` → XML-RPC creates `hr.applicant` | Medium (~4h) | ✅ Phase 1 |
| **D — Dedicated `empleo@` + Odoo** | Separate address on job postings, Odoo polls it | High | ⚠️ Consider if vol >50/mo |

**Decision: B now → C at 10+ applicants.**

**Phase 1 bridge trigger design:** Recruiter adds Freescout tag `#cv-recibido` to a conversation → cron script picks it up → creates `hr.applicant` with Freescout conversation ID stored in chatter. Avoids false-positive detection. Follows exact same pattern as `pagos_receipt_processor.py`.

**Fields to store on `hr.applicant` for traceability:**
- `ueipab_freescout_conv_id` (Integer) — Freescout conversation DB id
- `ueipab_freescout_url` (Char, computed) — direct link to Freescout conversation

---

## Job Portal Page — Email CTA Modal (PENDING — Phase 1.5)

**Decision (2026-06-07):** Keep Freescout as the single CV intake channel. The Odoo portal page shows the job description publicly but replaces the native "Apply Now" form with a modal popup that directs candidates to email their CV. No `hr.applicant` is ever created via the portal form — all intake flows through Freescout → `fs_cv_loader.py` cron.

**Rationale:** No HR staff. CEO manages the process alone. One intake channel (Freescout) is simpler to operate and ensures every CV gets AI-scored before it appears in Odoo. The portal form would create unscored applicants in a separate path with no CV file attached.

### Current state (2026-06-07)
- `hr.job` id=8: `is_published = False` — page accessible to logged-in admins only; anonymous visitors get 404
- **Do NOT publish until the modal override is deployed** — or candidates hit the native Odoo apply form

### Implementation plan (⏳ NOT YET BUILT — ~2h effort)

**File to create:** `addons/ueipab_recruitment/views/website_job_apply_override.xml`

**Approach:** QWeb template inheritance inside `ueipab_recruitment` — overrides the apply button section of `website_hr_recruitment`'s job detail page template. Replaces it with a Bootstrap modal (already available on every Odoo website page — no extra JS framework).

```
ueipab_recruitment/
  views/
    website_job_apply_override.xml    ← new
  __manifest__.py                     ← add to data[]
```

**Modal content:**
```
📩 ¿Quieres postularte?

Envía tu CV al siguiente correo:
  recursoshumanos@ueipab.edu.ve

Asunto sugerido: CV — Auxiliar de Contabilidad y Administración

Incluye en tu correo:
  • Tu CV en formato PDF o Word
  • Tu nombre completo y número de cédula
  • Ciudad de residencia

[✉️ Abrir correo]   ← mailto: pre-filled link
[✖ Cerrar]

Recibirás respuesta en 2-3 días hábiles.
```

**`mailto:` pre-fill:**
```
mailto:recursoshumanos@ueipab.edu.ve
  ?subject=CV%20—%20Auxiliar%20de%20Contabilidad%20y%20Administración
  &body=Nombre%3A%0ACédula%3A%0ACiudad%3A%0A%0AAdjunto%20mi%20CV.
```

**Deployment steps (when ready to build):**
1. Identify exact template name from `website_hr_recruitment` source (check `/usr/lib/python3/dist-packages/odoo/addons/website_hr_recruitment/views/`)
2. Create `website_job_apply_override.xml` with XPath targeting the apply button/form
3. Add to `__manifest__.py` data list
4. Run `-u ueipab_recruitment`
5. Set `hr.job` id=8 `is_published = True` (via Odoo UI toggle or shell)
6. Verify anonymous access shows modal, not the Odoo apply form

**Why this approach over alternatives:**
- ✅ Lives in our module — survives Odoo updates
- ✅ Bootstrap already loaded — no extra JS dependency
- ✅ Zero Odoo apply form submissions — Freescout stays sole intake
- ❌ Rejected: JS asset intercepting button — fragile if Odoo renames element
- ❌ Rejected: unpublishing — candidates can't read the job description

*(These fields are planned for Phase 1 — not yet in the module.)*

---

## Open Questions / Decisions Needed

- [x] Salary range — answered above (~$250–$300 total for 26-27 budget)
- [x] CV intake — Option B (manual) for Phase 0; Option C (Freescout bridge) for Phase 1
- [ ] City/location filter (presencial? remoto parcial?)
- [ ] Who conducts the final human interview? (Director, Finance head?)
- [ ] Glenda evaluation via Telegram — confirmed approach (Telegram-only, Phase 2)

---

## Glenda Integration Opportunity (Optional Phase 3)

Since Glenda (WhatsApp + Telegram AI agent) is already deployed, an elegant extension:

1. Applicant receives WhatsApp message from Glenda: "Hola [name], soy Glenda, la asistente de UEIPAB. Vamos a hacer tu evaluación técnica. ¿Empezamos?"
2. Glenda asks 8–10 adaptive questions via conversational chat
3. Conversation logs → Claude evaluates full transcript → writes score to `hr.applicant`

**Advantage:** No email/attachment friction; native mobile UX; Glenda already handles identity verification.

**Constraint:** Glenda currently serves families/parents. A separate conversation `skill_type=recruitment_eval` would need isolation from the family-facing flow.

---

## Gaps Discovered — Phase 0 Findings (2026-06-07)

| Gap | Detail | Impact |
|-----|--------|--------|
| `hr_recruitment_survey` links ONE survey per job/applicant | Designed for the final interview form only; we need two (roster + skill eval) separately linked | Minor — custom fields solve this cleanly |
| `survey.survey` has no `tag_ids` in Community | Can't domain-filter surveys by tag | Minor — use naming convention instead (`[ROSTER]` prefix) |
| Eval panel at bottom of form (before chatter) felt disconnected | Moved to a dedicated **"Evaluación IA" tab** in the notebook alongside "Application Summary" | ✅ Fixed — `//page[@name='application_summary']` position="after" |
| Statusbar widget conflict in `//header` | Can't add a second statusbar to header alongside `stage_id` | ✅ Moved eval state to form body |
| `survey.survey` tag system | Community surveys don't have a tag/category system | Use survey title convention instead |
| Glenda `ai.agent.conversation` has no `skill_type` | All convs are treated as family-facing; recruitment needs isolation | Need new field in `ueipab_ai_agent` Phase 2 |
| No `RECRUIT_*` start handler in Telegram bot | `_handle_telegram_employee_start()` handles `EMP_*` only | Need `RECRUIT_*` handler in Phase 2 |
| **CV attachment content never extracted** | Script reads email body only — all real CV content is in attachments | ✅ Addressed in section below |

---

## CV Attachment Identity Gap — Critical Analysis

### Confirmed data from real 25-CV batch (2026-06-07)

Freescout API investigation revealed:

| Metric | Result |
|--------|--------|
| Convs with attachments | **25 / 25 (100%)** |
| PDF attachments | 23 |
| DOCX attachments | 2 |
| Image attachments (JPG/PNG) | 0 (this batch) |
| Convs with zero attachment | 0 |
| Avg email body (useful text) | 50–200 chars ("adjunto mi CV") |

**Core problem:** The email body is just a greeting. Every substantive CV data point is locked inside the attachment. The current `fs_cv_loader.py` reads only the body — this is why **20 of 25 candidates scored 0** in dry-run despite all having real CVs.

### Freescout attachment API — what we know

Attachments are nested at `thread._embedded.attachments` (NOT `thread.attachments` — that field is always empty).

Each attachment contains:
```json
{
  "id": 33876,
  "fileName": "CV_Maria_Perez.pdf",
  "fileUrl": "https://freescout.ueipab.edu.ve/storage/attachment/3/7/1/CV.pdf?id=33876&token=<sha256>",
  "mimeType": "application/pdf",
  "size": 63540
}
```

**`fileUrl` is tokenized and downloadable without additional auth headers** (token is embedded in query string). Confirmed via test: `GET fileUrl` → HTTP 200, full file bytes returned.

### File types we will encounter in Venezuelan hiring context

| Format | Likelihood | Typical origin | Extractable? |
|--------|-----------|----------------|--------------|
| PDF (text layer) | Medium | Canva export "Download as PDF", Word → PDF | Yes — text extraction |
| PDF (image-based) | High | Canva "flat" export, WhatsApp PDF, scanned | Vision only |
| DOCX | Medium | Microsoft Word directly | Yes — python-docx |
| JPG / PNG | Medium | Phone camera shot of printed CV, WhatsApp image | Vision only |
| PUB | Low–Medium | Microsoft Publisher (very common for Venezuelan graphic CVs) | No Python lib — skip |
| WEBP | Low | WhatsApp compressed image | Vision (convert) |
| XLSX | Rare | Unusual but possible | openpyxl |

**Important Venezuelan context:** Large PDFs (> 500KB for a 1–2 page CV) almost always indicate an image-based PDF (Canva design, photo-heavy layout, or WhatsApp-converted). The current batch has files from 86KB to 1.6MB — at least half are likely image-based PDFs with no text layer.

### Recommended extraction strategy

**Tier 1 — Text extraction (fast, zero AI cost):**
- `DOCX` → `python-docx` → extract full paragraph text
- `PDF with text layer` → `pdfplumber` → extract text (detect: if extracted chars > 80, consider it text-based)
- `XLSX` → `openpyxl` → extract cell values (rare edge case)

**Tier 2 — Claude Vision (image-based content):**
- `PDF image-based` (text extraction yields < 80 chars) → base64 encode first 3 pages → send as `document` content block to Claude
- `JPG / PNG / WEBP` → base64 encode → send as `image` content block to Claude
- `PUB` → skip, set note: "Formato Publisher — revisar manualmente en Freescout"

**Why Claude Vision for image PDFs instead of OCR (Tesseract):**
- Tesseract requires system package install + Spanish language pack training
- Claude Haiku 4.5 supports both image and PDF document blocks natively
- Haiku vision cost: ~$0.001–0.003 per CV attachment — negligible at this scale
- Single code path — Claude reads text PDFs and image PDFs equally well
- No additional system dependencies

### Anthropic API — document and image content blocks

**PDF (document block):**
```python
{
  "type": "document",
  "source": {
    "type": "base64",
    "media_type": "application/pdf",
    "data": "<base64_encoded_pdf>"
  }
}
```
- Supported by Claude Haiku 4.5 (claude-haiku-4-5-20251001) ✓
- Max file size: 32MB (API limit) — all CVs in batch are < 2MB ✓
- Claude reads up to 100 pages; for CVs we cap at 3 pages to control tokens

**Image (image block):**
```python
{
  "type": "image",
  "source": {
    "type": "base64",
    "media_type": "image/jpeg",  # or image/png, image/webp
    "data": "<base64_encoded_image>"
  }
}
```

**Combined message structure (attachment-aware scoring):**
```python
messages = [{
  "role": "user",
  "content": [
    {"type": "text", "text": scoring_prompt_prefix},
    {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": pdf_b64}},
    {"type": "text", "text": scoring_prompt_suffix}
  ]
}]
```

### Cost estimate with attachment extraction

| CV type | Tokens (approx) | Cost (Haiku) |
|---------|----------------|--------------|
| Email-body-only (current) | ~800 | $0.0002 |
| DOCX text extraction | ~1500 | $0.0004 |
| PDF text layer extraction | ~1500 | $0.0004 |
| PDF image-based (document block) | ~3000–8000 | $0.001–0.002 |
| JPG/PNG image | ~2000–5000 | $0.001–0.001 |

**Batch of 25 CVs with full attachment extraction: ~$0.04–0.08 total.** Negligible.

### Gaps that remain AFTER attachment extraction

1. **Password-protected PDFs** — rare, but some candidates lock their CVs. Download succeeds but extraction fails silently. Detect: extracted text = empty + pdfplumber raises exception → flag for manual review.

2. **Multi-attachment convs** — a candidate could send CV + cover letter + references in separate files. Current design takes the first attachment only. Enhancement: extract and concatenate all attachments up to 3 total.

3. **Duplicate candidate (second email)** — if a candidate sends a follow-up or re-submits a corrected CV, Freescout creates a NEW conversation. Without an email-dedup check, the cron creates a second `hr.applicant`. Fix: before creating, search for existing applicant with same `email_from` + same `job_id` → skip or merge.

4. **Subject-as-filename** — When a candidate emails with a file but no subject line, Freescout uses the filename as the subject. Example: conv 47018 subject = `"DOC-20260602-WA0005..docx"`. The current filter doesn't exclude these — correct, but it looks strange in the dry-run output.

5. **PUB files** — Microsoft Publisher CVs can't be parsed by any common Python library. Mark as "formato no soportado" in `ueipab_ai_eval_notes` and route to manual review.

---

## `fs_cv_loader.py` — Cron Architecture Decision

### One-time loader vs. recurring cron

**Decision: recurring cron (run daily while position is open)**

Rationale:
- The job post will receive CVs over days/weeks — not just on day 1
- The script is already idempotent (`ueipab_freescout_conv_id` dedup prevents re-creating existing applicants)
- Running it daily costs almost nothing (Freescout API + Haiku)
- CEO (sole HR operator) shouldn't have to remember to run it manually

### What the cron does and does NOT do

| Behavior | Decision | Reason |
|----------|----------|--------|
| Create new applicants for new CVs | ✅ Yes | Core function |
| Skip already-loaded applicants | ✅ Yes | Idempotency |
| Re-score existing applicants | ❌ No | Preserves manual score edits in Odoo |
| Re-extract attachments if new threads appear | ❌ No | Score is point-in-time; new info → manual update |
| Create duplicate for same-email re-submission | ❌ No (after Gap 3 fix) | Dedup by email + job_id |
| Run after position is filled | ❌ No | Controlled by `ACTIVE = True` flag at top of script |

### Cron schedule

```
# /etc/cron.d/fs_cv_processor
# Run daily at 09:00 VET (13:00 UTC) while position is active
0 13 * * * root /usr/bin/python3 /opt/odoo-dev/scripts/fs_cv_loader.py --live >> /var/log/fs_cv_processor.log 2>&1
```

**Why 09:00 VET:** CVs received overnight are processed before the CEO's morning review. One run per day is sufficient — hiring pipelines don't need real-time CV intake.

### State file (like other crons)

The cron should write a state summary to `scripts/fs_cv_processor_state.json` after each run:
```json
{
  "last_run": "2026-06-07T13:00:00Z",
  "created_today": 5,
  "skipped_dup": 18,
  "skipped_error": 1,
  "total_loaded": 25,
  "tier_counts": {"A": 1, "B": 4, "C": 20}
}
```

### Changes needed before cron-ifying

| Change | Priority | Status |
|--------|----------|--------|
| **Extract attachment content** (PDF + DOCX + image) | Critical | ✅ Done — pdfplumber + python-docx + Claude Vision path |
| **Email dedup** (same email + job_id → skip) | High | ✅ Done — `odoo_already_loaded_by_email()` |
| **`ACTIVE` flag** at top of script for easy on/off | Medium | ✅ Done |
| **State file** write after each run | Medium | ✅ Done — `fs_cv_processor_state.json` |
| **Extraction method** logged in ai_eval_notes | Low | ✅ Done — `method=text-extracted/vision/email-only` |
| Reframe docstring: "CV sync processor" not "one-time loader" | Low | ✅ Done |
| **Cron entry** at `/etc/cron.d/fs_cv_processor` | Medium | ⏳ Pending `--live` validation |

### Required pip installs on host

```bash
pip3 install pdfplumber python-docx   # ✅ installed 2026-06-07
# pymupdf only needed for PDF→image; not required — Claude document block handles image PDFs
```

### Dry-run results (2026-06-07) — with full attachment extraction

| Metric | Before (email body only) | After (attachment extraction) |
|--------|--------------------------|-------------------------------|
| Tier A (≥70) | 0 | **1** — Edglis Rondón (72) |
| Tier B (45–69) | 5 | **21** |
| Tier C (<45) | 20 | **4** |
| Scored 0 | 20 | **0** |
| Extraction method | email-only | text-extracted (all 26 PDFs had text layers) |
| Errors | 0 | 0 |

26 CVs ready for `--live`. Salary risk flagged on 21/26 (Licenciados/TSUs).

---

## Venezuelan Legal & Financial Context — Critical for Evaluation Design

These are non-negotiable constraints that directly affect what Glenda can ask and what counts as a **correct answer** for this role.

### IVA Exemption — Educational Services

Under Venezuelan LIVA (Ley del IVA), private educational services are **exempt from IVA**. UEIPAB does NOT charge IVA to families on mensualidades, matrículas, or any educational service. A candidate who states "se cobra 16% IVA" on a school invoice is factually wrong.

**Correct answer:** The applicable tax when families pay in foreign currency (Zelle, efectivo USD, binance) is **IGTF (3%)** — not IVA. Bs. payments (transferencia, pago móvil) have no additional tax for the recipient.

### No Interest on Late Balances — LOE Constraint

The Venezuelan Ley Orgánica de Educación (LOE) and related MPPE resolutions **prohibit private educational institutions from charging interest or mora fees** on outstanding family balances. UEIPAB cannot legally add a "recargo por mora" to a representante's invoice — only the Ministry can authorize that.

**Implication for evaluation:** MCQ questions about payment application and overdue accounts test accounting mechanics (e.g. FIFO allocation), but must never imply that the school charges interest. A candidate who suggests charging mora fees would be proposing an illegal action in this specific context.

### Valid Payment Methods (Venezuela, 2026)

Cheques — personal, de gerencia, certificados — are **fully discontinued** in the Venezuelan financial system. No bank clears them for routine transactions. Any mention of "cheque" in an evaluation question is invalid and misleads candidates who know the real market.

**Valid payments accepted by UEIPAB:**

| Method | Currency | Notes |
|--------|----------|-------|
| Transferencia bancaria | Bs. | Standard interbank |
| Pago Móvil | Bs. | Phone-to-phone, requires same-bank or C2P |
| Zelle | USD | IGTF 3% applies |
| Binance Pay | USDT | IGTF 3% applies |
| Cashea | USD (settled) | Fintech installments — UEIPAB receives full amount |
| Dólares en efectivo | USD | IGTF 3% applies |

---

## Glenda Evaluation — Delivery Modes

### Two modes: In-Person (preferred) + Remote (fallback)

**Key insight (2026-06-07):** Inviting candidates to UEIPAB premises for a supervised evaluation eliminates the cheating problem completely — no technology solution needed for the hardest risks. The in-person mode is the primary path; remote Telegram is kept as a fallback for candidates who genuinely cannot travel.

---

### Mode A — In-Person Supervised (preferred, maximum trust)

**The setup:**
- Candidate arrives at UEIPAB premises at a scheduled time
- Supervisor greets them, checks physical cédula → perfect identity verification
- No personal cellphone allowed in the room
- Seated at a school computer — only the Odoo portal is open, no other tabs
- Supervisor observes (screen visible) but does not intervene
- Session takes ~30 minutes

**The interface: OdooBot (Discuss)**
Glenda already runs via OdooBot/Discuss (`mail_bot_glenda.py`). The candidate logs into the Odoo portal and chats with OdooBot. No Telegram, no phone, no app install required. A supervised school computer is the only device.

**Why OdooBot is better than Telegram for in-person:**

| Factor | Telegram | OdooBot on school PC |
|--------|----------|----------------------|
| Device | Candidate's phone | School computer (controlled) |
| Browser isolation | Can't enforce | Single tab enforced by supervisor |
| Identity | Cédula crosscheck (digital) | Physical ID check at door ✅ |
| Conversation log | Telegram + Odoo ai.agent | Odoo Discuss natively |
| Requires app install | Yes | No — just a browser |
| App to build | RECRUIT_* Telegram handler | OdooBot recognition of portal user |

**Evaluation station account — `recursoshumanos@ueipab.edu.ve`**

A single shared internal Odoo user is used as the evaluation station — not per-candidate accounts.

- `recursoshumanos@ueipab.edu.ve` already exists as a partner (id=3754 in testing)
- An Odoo internal user is created on top of it (via UI: Settings → Users)
- Access rights: internal user, Discuss only — no Payroll, Accounting, or other apps visible
- School evaluation computer stays permanently logged in as this account with Discuss open

**Why shared account (not per-candidate portal users):**
- Candidate never needs to type a login — supervisor handles it before they sit down
- No per-candidate user management / cleanup required
- Identity is verified at Turn 1 by Glenda (cédula check vs `hr.applicant`) — not by login credentials
- Simpler to build and operate for the first 5–10 evaluations

**Entry flow — In-Person:**
```
SETUP (once):
  1. Create internal user: recursoshumanos@ueipab.edu.ve (Odoo UI — CEO does this)
  2. School computer: permanently logged in as this account, Discuss open at OdooBot

PER CANDIDATE SESSION:
  1. CEO sends appointment email (no credentials):
     "Su evaluación es el [fecha] a las [hora] en UEIPAB, El Tigre.
      Traiga su cédula. Duración: 30 minutos."
  2. Candidate arrives → supervisor physically checks cédula ✅
  3. Supervisor opens new OdooBot chat on school computer → hands keyboard to candidate
  4. Candidate sees a chat window (looks like WhatsApp) — starts typing
  5. Glenda Turn 1: "¿Nombre completo y cédula?" → matches vs hr.applicant → RECRUIT_* session starts
  6. 8-turn evaluation runs under supervisor observation (screen visible)
  7. Session ends → Glenda triggers dual-AI scoring in background
  8. Scores + consensus written to hr.applicant → eval_state = 'ai_done'
  9. Supervisor archives the chat → ready for next candidate
```

**What's built vs. needed:**
- ✅ OdooBot/Glenda integration exists (`mail_bot_glenda.py`)
- ✅ `recursoshumanos@ueipab.edu.ve` partner exists (id=3754) — just needs user account
- ⏳ `recursoshumanos@` Odoo user created via UI (CEO — pending)
- ⏳ OdooBot detects this is an evaluation session (cédula Turn 1 → find `hr.applicant`) → start RECRUIT_* mode
- ⏳ "Invitar a Evaluación Presencial" button → sends appointment email only (no account creation needed)

**Anti-cheating coverage in-person:**

| Risk | Mitigation |
|------|-----------|
| Uses ChatGPT | Impossible — supervisor controls browser, no phone |
| Friend answers instead | Physical ID check at door |
| Shares questions afterward | Still possible — but others still have to show up in person |
| Identity fraud | Supervisor inspects physical cédula document |
| Coaching in real time | Supervisor is watching the screen |
| Google answers | No other tabs, supervisor watching |

**Remaining gap:** A knowledgeable friend who physically accompanies them pretending to be the candidate (extremely unlikely given cédula check). **Mitigation:** Human interview with ID check is the final gate.

---

### Mode B — Remote via Telegram (fallback)

For candidates who cannot travel to El Tigre (legitimate cases only — distance, disability, etc.). Higher scrutiny applied.

**Entry flow — Remote:**
```
1. CEO clicks "Invitar a Evaluación Telegram" on hr.applicant form
2. System generates deep-link: t.me/GlendaUeipabBot?start=RECRUIT_{applicant_id}
3. Email sent to applicant with link + 48h deadline + ground rules
4. Candidate opens Telegram → taps Start → RECRUIT_{id} payload arrives
5. Glenda starts session → identity check Turn 1 (cédula crosscheck vs hr.applicant)
6. 8-turn evaluation
7. Dual-AI scoring (Claude + GPT-4o-mini) → consensus check
8. If consensus LOW → flagged for human transcript review before advancing
```

**Remote requires higher trust bar to advance:**
- Consensus must be HIGH or MEDIUM (not LOW)
- `evaluation_mode = 'remote'` stored on record — visible in Odoo
- LOW consensus remote evaluation → requires CEO to read full transcript before flipping to `ai_done`

---

### Evaluation Architecture — Two-Phase, MCQ-First (v2.0)

**Design principle:** Invest AI conversation time only on candidates who demonstrate baseline knowledge. Phase 1 is fast (~5 min), objective, and cheap. Phase 2 is only triggered when Phase 1 score justifies it.

**Shared session trigger — two entry paths (both supported):**

| Path | How | Best for |
|------|-----|---------|
| **Form button** | HR opens `hr.applicant` → clicks "🤖 Iniciar Evaluación IA" → session armed + Discuss opens | Planned sessions |
| **Direct Discuss** | HR opens OdooBot chat → types `evaluar` → Glenda guides: asks candidate name → confirms → arms session | Walk-in / ad-hoc |

In both cases, `ir.config_parameter` key `recruit.eval.session.{uid}` is written with the applicant_id and session state. Glenda's `_get_answer()` detects this key first — before any normal Glenda routing — and switches into evaluation mode.

---

### Phase 1 — MCQ Knowledge Quiz (~5 minutes)

Candidate types **A / B / C / D** after each question. Glenda acknowledges ("Siguiente pregunta:") without revealing right/wrong until all 10 are done. Scores are tallied silently and written to `hr.applicant` at the end.

**Q1 — Medios de pago válidos**
> La institución recibe pagos de representantes. ¿Cuál de estos medios NO es aceptado actualmente en Venezuela?
>
> A. Transferencia bancaria | B. Pago Móvil | C. Cheque personal | D. Zelle

✅ **C** — cheques están descontinuados en el sistema financiero venezolano.

---

**Q2 — IVA en servicios educativos**
> Al facturar la mensualidad escolar de un representante, ¿qué aplica respecto al IVA?
>
> A. Se cobra 16% de IVA estándar | B. Se cobra 8% de IVA reducido por ser servicio básico | C. El servicio educativo privado está exento de IVA | D. Solo pagan IVA los representantes que usan Zelle

✅ **C** — servicios educativos privados son exentos de IVA bajo la LIVA venezolana.

---

**Q3 — IGTF en pagos en divisa**
> Un representante paga su mensualidad vía Zelle en dólares. ¿Qué impuesto adicional aplica sobre ese pago?
>
> A. IVA 16% | B. IGTF 3% por pago en divisa | C. ISR 10% sobre la transacción | D. Ningún impuesto — servicios educativos son completamente exentos

✅ **B** — IGTF (3%) aplica sobre pagos en divisas recibidos por personas jurídicas. La exención educativa cubre el IVA, no el IGTF.

---

**Q4 — Asiento contable de cobro**
> La institución recibe Bs. 200.000 por Pago Móvil por mensualidad de un alumno. ¿Cuál es el asiento correcto?
>
> A. Débito Cuentas por Cobrar / Crédito Banco | B. Débito Banco / Crédito Ingresos por Servicios | C. Débito Gastos Operativos / Crédito Banco | D. Débito Ingresos / Crédito Cuentas por Pagar

✅ **B** — el cobro aumenta el activo (Banco) y reconoce el ingreso.

---

**Q5 — Requisitos de factura SENIAT**
> ¿Qué información es OBLIGATORIA en una factura válida emitida al representante?
>
> A. Nombre completo del estudiante y grado | B. Número de control, RIF del emisor, fecha y monto | C. Firma del representante y copia del pago | D. Número de cuenta bancaria del colegio

✅ **B** — campos mínimos exigidos por el SENIAT para cualquier factura.

---

**Q6 — Retenciones IVA en compras**
> UEIPAB paga una factura de un proveedor de mantenimiento por Bs. 500.000 más 16% IVA (Bs. 80.000). Si la institución es agente de retención IVA, ¿cuánto retiene de ese IVA y a quién lo paga?
>
> A. Retiene el 100% del IVA (Bs. 80.000) y lo entrega al SENIAT | B. Retiene el 75% del IVA (Bs. 60.000) y lo entera al SENIAT; paga al proveedor solo Bs. 20.000 de IVA | C. No retiene nada porque la institución está exenta de IVA | D. Retiene el 16% sobre el total de la factura incluyendo el monto base

✅ **B** — los agentes de retención IVA retienen 75% del IVA facturado y lo declaran y pagan al SENIAT. La exención educativa aplica a las *ventas* del colegio, no a sus compras.

---

**Q7 — Retenciones ISLR a proveedores**
> El colegio paga honorarios profesionales al contador externo. ¿Qué obligación fiscal tiene UEIPAB sobre ese pago?
>
> A. Ninguna — el contador declara su propio ISLR como persona natural | B. Retener ISLR según la tarifa aplicable, emitir comprobante de retención al proveedor y declararlo mensualmente al SENIAT | C. Pagar el IVA correspondiente a los honorarios profesionales | D. Solo reportarlo en el libro de ventas al cierre del año fiscal

✅ **B** — quien paga honorarios profesionales está obligado a retener ISLR, emitir el comprobante de retención al proveedor y declararlo vía portal SENIAT en el período correspondiente.

---

**Q8 — Conciliación bancaria — proceso**
> Al conciliar el banco de octubre, el saldo contable en Odoo es Bs. 1.200.000 pero el extracto bancario muestra Bs. 1.350.000. ¿Cuál es el primer paso correcto?
>
> A. Ajustar el saldo de Odoo al del banco sin investigar para cuadrar rápido | B. Identificar todas las partidas en tránsito: transferencias no reflejadas en libros, depósitos no acreditados, y posibles errores de registro | C. Emitir una nota de débito por la diferencia de Bs. 150.000 | D. Reportar el error directamente al SENIAT como discrepancia contable

✅ **B** — la conciliación identifica y documenta cada diferencia antes de cualquier ajuste; el objetivo es explicar la diferencia, no igualar un saldo al otro sin entender la causa.

---

**Q9 — Calendario fiscal SENIAT — retenciones**
> ¿Hasta qué fecha vencen generalmente las declaraciones de retenciones de IVA del período anterior para un contribuyente ordinario?
>
> A. El último día hábil del mismo mes en que ocurrieron | B. El día 15 del mes siguiente al período declarado | C. El primer día hábil del mes siguiente | D. Solo se declaran de forma trimestral junto con el IVA propio

✅ **B** — las retenciones IVA se declaran y pagan hasta el día 15 del mes siguiente (contribuyentes ordinarios). Los contribuyentes especiales tienen calendario escalonado según RIF.

---

**Q10 — IVSS / FAOV / INCES — obligación patronal**
> Además de descontar IVSS y FAOV del salario del trabajador, ¿qué debe hacer la institución cada mes?
>
> A. Nada más — el descuento en nómina es suficiente obligación | B. Pagar el aporte patronal correspondiente (IVSS 9–11%, FAOV 2%) y presentar la planilla ante el organismo dentro del plazo | C. Solo reportarlo al SENIAT en el libro de compras al cierre del año | D. Acumularlo durante el año y pagar junto con el ISLR en la declaración anual

✅ **B** — el empleador aporta su parte patronal además de retener la del trabajador, y debe presentar y pagar la planilla mensualmente. El incumplimiento genera multas e impide obtener la Solvencia Laboral — requisito para la Acta de Conformidad SENIAT.

---

### Phase 1 — Scoring & Gate

| Score | Band | Result |
|-------|------|--------|
| 9–10 / 10 | Excelente | Immediate Phase 2 invite |
| 7–8 / 10 | Bueno | HR reviews → Phase 2 invite |
| 5–6 / 10 | Regular | HR manual review only — no Phase 2 |
| 0–4 / 10 | Insuficiente | Polite close — session ends |

Recommended gate threshold: **≥ 7 / 10**.

At session end, Glenda reveals the score, gives brief positive/constructive feedback summary, and (if ≥ 7) asks: *"¡Bien hecho! Ahora pasamos a una segunda parte más práctica. Escribí 'continuar' cuando estés listo/a."* If < 7: *"Gracias por tu tiempo. Nuestro equipo estará en contacto."*

### MCQ Calibration — External Accountant Dry Run (before first real candidate)

Before deploying to real candidates, the external accountant takes the full quiz as UX and accuracy validation.

**Expected outcome:** Score 9–10/10. If he scores < 9, investigate that specific question — either the wording is ambiguous or the answer key reflects theory rather than Venezuelan practice.

**Feedback to collect from him:**

| Signal | What it means |
|---|---|
| Hesitates on a question | Wording is ambiguous — reword |
| Disputes a "correct" answer | Answer key wrong for real VZ practice — fix the key |
| Finds a wrong option obviously absurd | Distractors too easy — replace with realistic wrong answer |
| Scores < 9/10 | Question poorly framed or genuinely debatable — review |
| Finishes in < 3 minutes | Questions too simple for even a junior — raise difficulty |

**UX feedback:** Does A/B/C/D chat format feel natural? Is pacing comfortable? Does any question feel irrelevant to the actual day-to-day?

**Flexibility:** Questions are a Python list/dict in the OdooBot handler — one-line edits, no database migration, module reload to apply. Score gate threshold (7/10) is a single constant at the top of the file.

Fields written to `hr.applicant` at Phase 1 close:
- `ueipab_quiz_score` — Integer 0–10
- `ueipab_quiz_answers` — JSON array `[{"q": 1, "given": "C", "correct": "C", "ok": true}, ...]`
- `ueipab_quiz_completed` — Boolean True

---

### Phase 2 — Conversational Evaluation (gated, ~20 minutes)

Only proceeds if Phase 1 score ≥ threshold AND HR has not intervened to stop. Flows immediately in the same OdooBot chat — no channel switch.

```
Identity Turn (before Phase 1 or at Phase 1 Turn 0):
  "Hola, soy Glenda, la asistente de UEIPAB. Antes de comenzar,
   ¿me confirmas tu nombre completo y número de cédula?"
  → crosscheck vs hr.applicant → session formally starts

Turn 1: Experience warm-up
  "Descríbeme brevemente tu experiencia más reciente en
   contabilidad o administración."

Turn 2: Applied Venezuelan fiscal scenario — IGTF
  "Un representante realizó el pago de su mensualidad mediante Zelle
   en USD. ¿Qué impuesto aplica sobre esa transacción, cuál es
   la tasa, y quién lo paga?"

Turn 3: Follow-up probe — no escape from depth
  "Explicaste [X]. ¿En qué situación ese impuesto NO aplicaría?
   Dame un ejemplo concreto."

Turn 4: Practical classification exercise
  "Clasificá estas 3 transacciones: (1) pago de nómina del colegio,
   (2) cobro de mensualidad de un representante, (3) compra de
   papelería. ¿Qué cuenta de débito y crédito usarías para cada una?"

Turn 5: Bank reconciliation process
  "Descargaste el extracto bancario de octubre. El saldo en Odoo
   es Bs. 1.200.000 y el banco muestra Bs. 1.350.000. ¿Qué hacés
   paso a paso para encontrar y documentar la diferencia antes de
   que llegue el contador?"

Turn 6: Physical file + accountant liaison scenario
  "El contador externo llega el viernes para el cierre y necesita
   las facturas de compra de octubre con sus comprobantes de
   retención IVA y las planillas IVSS/FAOV pagadas ese mes.
   ¿Cómo tendrías organizado ese archivo y en cuánto tiempo lo
   encontrarías?"

Turn 7: Self-awareness check
  "¿Cuál es el área de contabilidad o cumplimiento fiscal donde
   sentís que tenés más por aprender?"

Turn 8: Role fit + close
  "¿Tenés alguna pregunta sobre el cargo, el equipo o cómo
   sería tu primer mes?"
  → triggers dual-AI scoring on full Phase 2 transcript
```

**Phase 2 scoring prompt (both Claude + GPT-4o-mini receive this):**
```
Evaluate this recruitment conversation for "Auxiliar de Contabilidad y Administración"
at a Venezuelan private school. Score 0–100 on:
- Technical accuracy 40%: accounting knowledge, Venezuelan fiscal awareness
  (IGTF, SENIAT — note: educational services are IVA-EXEMPT; correct answers
  must reflect this; also: LOE prohibits interest charges on late educational balances)
- Reasoning quality 30%: explains WHY not just WHAT; shows process thinking
- Communication clarity 20%: professional, organized Spanish; appropriate tone
- Self-awareness 10%: honest about gaps, not overconfident

IMPORTANT: Penalize answers that are textbook-perfect but lack applied specificity
or Venezuelan context. Real practitioners say "depende" and make small errors.
AI-generated answers are over-structured and complete. Reward genuine struggle
and practical examples.

Return JSON: {"score": int, "strengths": [...], "gaps": [...], "summary": "2 sentences in Spanish"}
```

---

### Odoo fields for evaluation mode tracking

New fields on `hr.applicant` (Phase 1 model update):

```python
ueipab_evaluation_mode = fields.Selection([
    ('in_person', 'Presencial (supervisado)'),
    ('remote',    'Remoto (Telegram)'),
], string='Modo de Evaluación')

ueipab_skill_score_gpt = fields.Float('Score GPT-4o (verificador)', default=0.0)

ueipab_eval_consensus = fields.Selection([
    ('high',   '✅ Alta (Δ≤15)'),
    ('medium', '⚠️ Media (Δ16–25)'),
    ('low',    '🔴 Baja (Δ>25) — revisar transcript'),
], string='Consenso IA')
```

**Confidence rule by mode + consensus:**

| Mode | Consensus | Action |
|------|-----------|--------|
| In-person | HIGH | Advance immediately |
| In-person | MEDIUM | Advance — note in record |
| In-person | LOW | Review transcript — unusual but possible |
| Remote | HIGH | Advance |
| Remote | MEDIUM | CEO reads key turns before advancing |
| Remote | LOW | **Hold** — do not advance without full transcript review |

### What "gaming" still cannot be prevented (honest limits)

- A knowledgeable friend physically present who whispers answers (in-person, extremely rare given cédula check)
- Someone who genuinely knows accounting but intends to under-deliver on the job (behavioral, not detectable by any AI)
- **Mitigation:** The confidence % gates access to the human interview. The interview is the final, unjammable layer.

---

## Required Odoo 17 Community Installation Commands

```bash
# These modules should already be installed; verify:
docker exec odoo-dev-web python3 -c "
import xmlrpc.client
url = 'http://localhost:8069'
db, user, pwd = 'testing', 'admin', 'admin'
uid = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common').authenticate(db, user, pwd, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
installed = models.execute_kw(db, uid, pwd, 'ir.module.module', 'search_read',
    [[['name', 'in', ['hr_recruitment','survey','hr_skills']], ['state','=','installed']]],
    {'fields': ['name','state']})
print(installed)
"

# Install if missing:
docker exec odoo-dev-web python3 -c "
# ... same auth ...
models.execute_kw(db, uid, pwd, 'ir.module.module', 'button_immediate_install',
    [[module_id]])
"
```

---

## Current Build Status (2026-06-07, session 2)

### DONE ✅
| Item | Where |
|------|-------|
| `ueipab_recruitment` module v2.0.0 installed in `testing` | `addons/ueipab_recruitment/` |
| `hr.applicant` custom fields — full set (cv_score, cv_tier, cv_salary_risk, cv_extract_method, eval_state, evaluation_mode, skill_score, skill_score_gpt, eval_consensus, confidence_pct, ai_eval_notes, freescout_conv_id) | `models/hr_applicant.py` |
| Confidence formula: `cv_score × 0.40 + glenda_score × 0.60` | `models/hr_applicant.py` |
| Evaluation panel — **"Evaluación IA" tab** in notebook alongside "Application Summary" (3 buttons: confirm, in-person invite, telegram invite) | `views/hr_applicant_views.xml` |
| Recruitment stages — 7-stage pipeline: New→Pre-Screening→Pre-Approved→Technical Evaluation→Interview→Hired/Rejected | `data/recruitment_stages.xml` + shell cleanup |
| `fs_cv_loader.py` — full CV sync processor (cron-ready) | `scripts/fs_cv_loader.py` |
| — Freescout REST API polling (mailbox 4, `_embedded.threads`, `_embedded.attachments`) | |
| — CV filter (date + domain + subject patterns + `ACTIVE` flag) | |
| — Attachment extraction: PDF text layer (pdfplumber), DOCX (python-docx), Claude Vision for image PDFs/images | |
| — Claude Haiku multimodal scoring (text + document + image content blocks) | |
| — Idempotent dedup: by `ueipab_freescout_conv_id` AND by `email_from + job_id` | |
| — State file `fs_cv_processor_state.json` after each run | |
| **29 applicants LIVE in Odoo testing** — 1 Tier A / 21 Tier B / 7 Tier C, 0 errors | testing DB |
| Daily cron `/etc/cron.d/fs_cv_processor` — 09:00 VET, idempotent | host |
| pip packages on host: `pdfplumber`, `python-docx` | host |
| Evaluation station account design — shared `recursoshumanos@` login, not per-candidate | this MD |
| Salary range real data + budget 26-27 projection documented | this MD |
| ~~Roster Survey (10 Qs)~~ — **Dropped**: CV AI score replaces the pre-screen layer | |

### NOT YET BUILT ⏳ — ordered by priority

| Item | Phase | Effort | Notes |
|------|-------|--------|-------|
| `recursoshumanos@ueipab.edu.ve` Odoo internal user created | Phase 1 | 5 min | CEO creates via UI → validate |
| **Send confirmation email** to Edglis Rondón (Tier A, 72/100, no salary risk) | Phase 1 | 5 min | Manual, personal email — do now |
| `action_send_in_person_invite()` — sends appointment email (date/time/address, no credentials) | Phase 1 | 30 min | Button on hr.applicant form |
| **New hr.applicant fields:** `ueipab_quiz_score` (Int 0–10), `ueipab_quiz_answers` (Text JSON), `ueipab_quiz_completed` (Boolean) | Phase 1 | 30 min | Phase 1 MCQ state tracking |
| **Form button trigger:** `action_start_eval()` on hr.applicant → writes `ir.config_parameter` eval session key → opens Discuss OdooBot chat | Phase 1 | 1h | Planned-session entry path |
| **Direct Discuss trigger:** Glenda detects keyword `evaluar` in OdooBot chat → asks candidate name → confirms vs hr.applicant → arms eval session | Phase 1 | 1h | Walk-in / ad-hoc entry path |
| **OdooBot `RECRUIT_EVAL` handler** in `mail_bot_glenda.py` — session state machine: Identity → Phase 1 MCQ (10 Qs, letter answers) → score gate → Phase 2 conversational (7 turns) → dual-AI scoring | Phase 1 | 4h | Core build — replaces generic Glenda when eval session armed |
| Dual-AI scoring at Phase 2 close (Claude + GPT-4o-mini on transcript) → writes `ueipab_skill_score`, `ueipab_skill_score_gpt`, `ueipab_eval_consensus` to `hr.applicant` | Phase 1 | 1h | Within OdooBot handler |
| CEO notification at eval complete — OdooBot DM with scorecard (Phase 1 MCQ score + Phase 2 AI score + consensus) | Phase 1 | 30 min | Within OdooBot handler |
| `RECRUIT_*` Telegram deep-link handler (Mode B fallback) | Phase 1 | 1h | After Mode A validated in practice |
| **Portal email CTA modal** — publish job page + replace apply form with Bootstrap modal directing to `recursoshumanos@` | Phase 1.5 | 2h | Deploy before publishing `is_published=True` on hr.job id=8 |
| Kanban confidence badge (tier + score visible in card) | Phase 2 | 1h | Deferred — Odoo 17 kanban QWeb strict |
| Deploy `ueipab_recruitment` to production | Phase 2 | 30 min | After first real evaluation complete |

### OPEN DECISIONS

| Decision | Status |
|----------|--------|
| Who conducts the final interview? | ❓ Open |
| What triggers "position filled" → `ACTIVE=False` in script + close job position? | ❓ Open |
| Mode B (remote Telegram) — build now or only if Mode A has a gap? | ❓ Recommend: Mode A first, Mode B only if candidate can't travel |

## Next Steps

1. **Review and approve Job Description** (edit draft above)
2. **Define salary range** → complete Roster Survey Section 3
3. **Run Phase 0** — Odoo Job Post + manual Roster Survey + confidence field
4. Publish job post and collect first 2–3 applicants
5. Debrief after first cycle → decide automation scope

---

*See also:* [AI Agent Module](AI_AGENT_MODULE.md) · [Glenda Technical Patterns](GLENDA_TECHNICAL_PATTERNS.md) · [Features](FEATURES.md)
