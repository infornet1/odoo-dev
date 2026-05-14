# Glenda Calibration Feedback — Implementation Plan

**Source:** Programa de Calibración Glenda (Round 1)  
**Period:** 2026-05-11 → 2026-05-14  
**Testers:** 8 employees | **Total suggestions:** 23 | **Done:** 3 (audio transcription)  
**Status:** 20 pending

---

## Summary by Category

| Category | Count | Top Theme |
|----------|-------|-----------|
| `flujo` | 12 | Conversation closure — repeated/redundant messages |
| `conocimiento` | 6 | Missing policies: mora, enrollment docs, bachillerato tracks |
| `tecnico` | 4 | Audio transcription (✅ already done) |
| `asistencia` | 2 | Cashea visibility |

---

## Priority 1 — Critical UX (flujo) — Most Mentioned

**8 testers flagged the same problem:** Glenda sends multiple messages at the end of a conversation,
repeats farewells, and keeps asking "¿Hay algo más?" after the user has clearly finished.

### Suggestion consolidation

| # | Tester | Suggestion |
|---|--------|------------|
| 1 | Maria Figuera | No repetir múltiples mensajes — respuestas prioritarias, sin redundancias |
| 4 | NIDYA LIRA | Evitar mensajes seguidos, despedida clara sin preguntas abiertas repetitivas |
| 5 | NIDYA LIRA | Evitar mensajes seguidos — cerrar sin dejar preguntas abiertas innecesarias |
| 6 | GLADYS BRITO | Reducir insistencia en despedidas — una sola línea es suficiente |
| 7 | MAIRELSY MOTTA | No enviar mensajes adicionales después de cerrar el tema |
| 8 | MAIRELSY MOTTA | Detectar despedidas ("feliz día", "gracias", "no es todo") y cerrar automáticamente |
| 13 | JOSEFINA RODRIGUEZ | Respuestas más directas y concisas sin redundancias |
| 14 | JOSEFINA RODRIGUEZ | No repetir información ya proporcionada en la conversación |

### What to implement

**A. Strengthen the farewell detection rule** (system prompt, `general_inquiry.py`):

Add explicit trigger phrases to detect conversation end without requiring "adiós":
- `"gracias"`, `"feliz día"`, `"hasta luego"`, `"no es todo"`, `"eso es todo"`,
  `"listo"`, `"ok gracias"`, `"perfecto"`, `"excelente"` → one short farewell, stop

**B. Hard limit: one closing message, zero follow-up questions after farewell**

Current rule already exists (`REGLAS DE COMUNICACIÓN` v17.0.1.34.0) but is not enforced
firmly enough. Reinforce with explicit negative examples:

> ❌ NEVER do: "¡Hasta pronto! ¿Puedo ayudarte en algo más? Que tengas un excelente día. ¡Cuídate mucho!"  
> ✅ DO: "¡Hasta pronto!"

**C. Auto-close after inactivity** (Nidya #5, Mairelsy #7, #8):

After the human sends a clear farewell, the next AI turn should be the LAST.
Set `conversation.state = 'resolved'` immediately — do not wait for the 72h timeout.
This requires a small logic addition in `action_process_reply()`:

```python
FAREWELL_TRIGGERS = ['gracias', 'hasta luego', 'feliz día', 'no es todo',
                     'eso es todo', 'listo gracias', 'ok gracias', 'perfecto gracias']

if any(t in last_customer_msg.lower() for t in FAREWELL_TRIGGERS):
    conversation.state = 'resolved'
```

---

## Priority 2 — Knowledge Gaps (conocimiento)

### 2A — Mora & Sanctions Policy

**Testers:** LUISA ELENA ABREU (#3, #15, #16), AUDREY GARCIA (#18)  

Glenda currently responds to mora questions with empathy + redirect to pagos@,
but has NO information about what actually happens when a family doesn't pay for
3+ months. Staff and families ask this.

**What to add to `_INSTITUTIONAL_KNOWLEDGE`:**
- After how many months does a student risk suspension?
- Is there a formal payment plan process?
- What is the reinstatement process after falling behind?
- Are there any grace period policies?

> **⚠ Action required:** Confirm the official policy with Dirección/Pagos before adding.
> Once confirmed, add a `POLÍTICA DE MORA Y CONSECUENCIAS` block to the knowledge.

### 2B — Enrollment Documentation (inscripción) ✅ DONE (v17.0.1.41.2, 2026-05-14)

**Tester:** AUDREY GARCIA (#18)

**Implemented:** Enrollment process is fully online via Akdemia. Glenda now provides the direct link when anyone asks about documents, steps, or how to enroll:
- Link: https://edge.akdemia.com/admissions/09f8190d36eef4ea/start
- The Akdemia platform guides applicants step by step — no need for a static document checklist.
- For additional questions: soporte@ueipab.edu.ve

### 2C — Bachillerato Tracks & Mentions ✅ DONE (v17.0.1.41.1, 2026-05-14)

**Tester:** AUDREY GARCIA (#21)

**Implemented** from official MPPE document "Propuesta Juntos por la educación del futuro" (BachilleTIC.pdf):
- Diploma: **Bachiller en Ciencias y Tecnología** (replaces old Ciencias/Humanidades)
- 5 years, 10 subject areas, max 40 h/week
- Componente General: Lengua/Lit, Idiomas, Matemáticas, Ed. Física, Biología/Amb/Tec, Física, Química, Geo/Hist/Ciudadanía
- Componente Productivo: Orientación Vocacional + Innovación Tecnológica y Productiva (6 h/sem)
- Enables university access (all careers) AND direct workforce entry
- Bachillerato Virtual via Dawere (flexible/online) — details via soporte@
- **IB clarification added**: school does NOT offer IB Geneva — offers Venezuelan national diploma only

### 2D — Diagnostic Exam for Foreign Students

**Tester:** LUISA ELENA ABREU (#20)

Students arriving from abroad may be placed in wrong grade without level verification.

**What to add:** Whether the school offers or requires an academic diagnostic test
for transfer/foreign students before assigning a grade level.

> **⚠ Action required:** Confirm policy with Dirección Académica.

---

## Priority 3 — Payment Visibility (asistencia)

**Testers:** LUISA ELENA ABREU (#2), Jessica Bolivar (#9)

### Cashea — more proactive, not just reactive

Cashea is already in the knowledge block but Glenda only mentions it when asked.
Both testers want it offered proactively when a family mentions payment difficulty.

**What to add to instructions:**
> When a family mentions difficulty paying, dificultad económica, or asks about
> financing options — proactively mention Cashea as an available payment option
> alongside the standard methods. Always direct to pagos@ueipab.edu.ve to get the link.

---

## Priority 4 — Satisfaction Rating System

**Tester:** NIDYA LIRA (#5)

Request: a thumbs-up/thumbs-down rating after each conversation for improvement metrics.

**Implementation idea:**
- At conversation resolution, Glenda sends: "¿Cómo calificarías mi atención? Responde 1 (excelente), 2 (buena) o 3 (mejorable)"
- Store rating on `ai.agent.conversation` (new field: `rating`)
- Show in daily digest and conversation list view

**Effort:** Medium — new field, new turn after resolution, digest update.

---

## Priority 5 — Future Features (complex, later)

| # | Tester | Request | Effort |
|---|--------|---------|--------|
| 22 | Jessica Bolivar | Course comparison table (schedules, costs, materials in one view) | High |
| 23 | Jessica Bolivar | Circular summarizer: new amount + effective date + reason in 3 bullets | Medium |
| 17 | LUISA ELENA ABREU | Optimize return-from-break logistics (operational, not Glenda) | Out of scope |

---

## Already Done ✅

| # | Tester | Request | Version |
|---|--------|---------|---------|
| 10, 11, 12 | Maria Figuera | Audio transcription / voice note support | v17.0.1.40.0 |
| 19 | Gustavo Perdomo | Audio transcription | v17.0.1.40.0 |
| 1, 4, 5, 6, 7, 8, 13, 14 | Multiple (8/8) | Farewell auto-close + single closing message | v17.0.1.41.0 |
| 2, 9 | Luisa Abreu, Jessica Bolivar | Cashea proactive mention on payment difficulty | v17.0.1.41.0 |
| 21 | AUDREY GARCIA | Bachillerato tracks/menciones + IB clarification | v17.0.1.41.1 |
| 18 | AUDREY GARCIA | Enrollment docs → Akdemia online admissions link | v17.0.1.41.2 |

---

## Implementation Roadmap

```
Week 1 (quick wins — system prompt only, no DB changes)
  ├── P1: Strengthen farewell detection + hard single-farewell rule
  ├── P1: Auto-close on detected farewell phrases
  └── P3: Cashea proactive mention on payment difficulty

Week 2 (knowledge additions — pending admin confirmation)
  ├── P2A: Mora & sanctions policy block
  ├── P2B: Enrollment documentation checklist
  └── P2C: Bachillerato tracks / menciones

Week 3-4 (features)
  └── P4: Satisfaction rating system (new field + post-resolution turn)

Backlog
  ├── P5: Course comparison table
  └── P5: Circular summarizer
```

---

## Testers Who Contributed

| Tester | Suggestions | Categories |
|--------|------------|------------|
| LUISA ELENA ABREU | 5 | conocimiento, asistencia, flujo |
| Maria Figuera | 4 | flujo, tecnico |
| NIDYA LIRA | 2 | flujo |
| MAIRELSY MOTTA | 2 | flujo |
| JOSEFINA RODRIGUEZ | 2 | flujo |
| Jessica Bolivar | 3 | flujo, asistencia |
| AUDREY GARCIA | 2 | conocimiento |
| Gustavo Perdomo | 1 | tecnico |

---

## Notes for Admin Before Implementation

Before adding knowledge in P2A–P2D, the following must be confirmed with school leadership:

- [ ] **Mora policy:** exact timeline and consequences for non-payment (3 months? 6?)
- [ ] **Enrollment docs:** official checklist from Secretaría for new + returning students
- [ ] **Bachillerato menciones:** which tracks does the school offer formally?
- [ ] **Bachillerato Internacional:** is this offered or just the virtual program?
- [ ] **Foreign student diagnostic:** is there an official policy / test?
