# Glenda UX Improvement Plan — "Habla Mucho"

**Status:** In Progress (v57.15–v57.17 deployed) | **Created:** 2026-05-23 | **Updated:** 2026-05-24 | **Priority:** High

## Problem Statement

User feedback from the El Tigre community:
> *"Glenda habla mucho"* / *"Glenda me carga loca"*

Parents are receiving walls of text on WhatsApp. They're not reading them. They drop off.

### Why this matters for El Tigre specifically

The school's parent community in El Tigre, Anzoátegui operates under:
- **Acute economic stress** — Venezuela's ongoing crisis hits PDVSA-adjacent communities hard
- **Emotional baseline**: many parents are anxious, overwhelmed, or already annoyed before they write
- **WA usage pattern**: people here send 2–5 word messages and expect the same back
- **Low tolerance for reading**: a 6-line response on a balance question is already too long
- **Trust gap with AI**: if Glenda sounds like a brochure, parents assume she can't actually help

A short, direct answer signals competence. A long answer signals avoidance.

---

## Baseline (Production Data — 2026-05-24, n=250 conversations)

| Metric | Pre-v57.15 Baseline | Target | Status |
|--------|---------------------|--------|--------|
| Avg first reply length | **861 chars** (median 830) | < 400 chars | Deploying |
| First replies > 800 chars | **65%** | < 20% | Deploying |
| First replies > 500 chars | **75%** | < 30% | Deploying |
| Resolution rate (short first reply ≤500c) | **66%** | baseline | Measuring |
| Resolution rate (long first reply >500c) | **45%** | — | Measuring |
| `max_tokens` ceiling | 1,024 | **512** ✅ | Done |
| Max single message observed | 2,506 chars | — | — |

**Key finding:** Conversations with first reply ≤500 chars resolve 21pp more often than long ones (66% vs 45%). This confirmed Angles 1+2+3 as highest priority.

**Pricing response audit (8 exchanges, pre-fix):** Promo $187 included 62%; Annual $101 included only 38%; both together 38%.

---

## Current Guardrails (What Already Exists)

These rules are already in `general_inquiry.py` `get_system_prompt()` but are too weak:

| Rule | Status | Problem |
|------|--------|---------|
| `"parrafo corto primero — ofrece detalle si lo pide"` | ✅ Exists | Buried, too vague |
| `"Un solo mensaje por turno"` | ✅ Exists | Working |
| `"PROHIBIDO terminar con ¿Hay algo más...?"` | ✅ Exists | Working |
| `"DESPEDIDA — REGLA ESTRICTA"` | ✅ Exists | Working |
| No explicit character/line limit | ❌ Missing | Main gap |
| No per-response-type budget | ❌ Missing | Main gap |
| Supervisor scores "concisa" as sub-criterion | ⚠️ Weak | Bundled with tone (criterion 4) |

---

## Angles of Attack

### Angle 1 — Hard length ceiling (immediate, highest impact)

**What:** Reduce `max_tokens` from 1024 to 512 in `claude_service.py`.

**Effect:** Claude physically cannot generate more than ~400 chars. Forces compression.

**Risk:** Rare complex responses (multi-student quotes with tables) may get cut. Mitigation: keep
`max_tokens=400` for the specific greetings flow (already done at line 896 in
`ai_agent_conversation.py`), set 512 globally.

**File:** `addons/ueipab_ai_agent/models/claude_service.py` line 56 + 81.

---

### Angle 2 — Stronger prompt rules (immediate, high impact)

Add to the `INSTRUCCIONES` block in `general_inquiry.py` `get_system_prompt()`:

```
LONGITUD DE RESPUESTA — REGLA CRÍTICA:
Estás en WhatsApp. Los padres en El Tigre leen en el móvil, con poco tiempo y mucho estrés.
Responde como lo haría una persona eficiente, no un manual.

Límites estrictos por tipo de mensaje:
- Saludo simple / sin consulta → menú (máx 8 líneas)
- Consulta de saldo → 2-3 líneas con el dato + próximo paso
- Pregunta de precio / tarifa → dato directo + una línea de contexto
- Dificultad económica / queja → 3-4 líneas, cálidas, sin enumerar pasos
- Despedida → 1 línea, nada más
- Cualquier otra consulta → máx 5 líneas

PROHIBIDO:
- Reintroducirte si ya te presentaste antes en la misma conversación
- Repetir la pregunta del cliente antes de responderla
- Dar contexto que no pedió
- Enumerar más de 3 cosas en una respuesta
- Usar más de un emoji por mensaje
```

**Why this works better than current:** Gives Claude a number (5 lines, 3 items), not a vague adjective. Numbers survive long prompts. Adjectives don't.

---

### Angle 3 — Venezuelan context injection (medium impact)

Add a dedicated context block early in the system prompt (before the institutional knowledge):

```
CONTEXTO DE LA COMUNIDAD:
Hablas con padres y representantes de El Tigre, Anzoátegui, Venezuela.
Esta comunidad vive una situación económica muy difícil. Muchos de los padres
que te escriben están preocupados, cansados o bajo presión cuando lo hacen.

Tu objetivo es hacer que se sientan ATENDIDOS, no INFORMADOS.
Un padre que recibe una respuesta corta y precisa se siente respetado.
Un padre que recibe 6 párrafos siente que la máquina no lo está escuchando.

Comunica como lo haría una persona de confianza: directo, cálido, sin florituras.
```

This reframes the task for Claude at a values level, not just a formatting level.

---

### Angle 4 — Supervisor scoring enhancement (medium-term)

Current supervisor criterion 4: *"Tono cálido y profesional, respuesta concisa"* — bundled.

**Proposed change to `glenda_supervisor.py` scoring prompt:**

```
1. Datos correctos (precios, fechas, nombres de empresa, enlaces)
2. Respondió la pregunta real sin desviarse ni pedir info innecesaria
3. Aprovechó oportunidades comerciales cuando era pertinente
4. Tono cálido, empático, apropiado para el contexto venezolano
5. Brevedad: respuesta concisa, sin introducción innecesaria, sin preguntas de cierre
   ESPECIALMENTE: ¿la respuesta de Glenda tiene más de 5 líneas donde bastaban 2?
```

Also add to the digest: average character length of Glenda's outbound messages in the reviewed
conversation. Flag conversations where any single Glenda message exceeds 600 chars.

---

### Angle 5 — Conversation dropout analysis (diagnostic, before tuning)

Before making prompt changes, baseline the current state:

**Query to run against production:**
```python
# ai.agent.conversation grouped by state — compare message lengths in
# resolved vs timeout/failed conversations
# Hypothesis: longer Glenda messages correlate with parent dropoff
```

This tells you whether brevity is THE problem or one of several. The supervisor log already
captures some signal (`/var/log/glenda_supervisor.log`) — check for patterns in low-score
conversations.

**Key questions to answer:**
1. Do conversations where Glenda sends > 500 chars on the first reply have lower resolution rates?
2. Do parents who drop off (timeout) receive longer messages than those who resolve?
3. Which skills generate the longest messages? (general_inquiry vs billing_support?)

If the data shows strong correlation → Angle 1+2 are the priority.
If the data is mixed → the problem may be knowledge accuracy, not length.

---

### Angle 6 — Style assessment via conversation review (if needed)

If automated data doesn't give enough signal, do a manual audit:

1. Pull 20–30 conversations from production (mix of resolved / timeout / failed)
2. For each: rate Glenda's response on (a) accuracy, (b) length appropriateness, (c) empathy
3. Look for patterns: what types of queries trigger the longest responses?
4. Use findings to write specific examples in the system prompt ("❌ MAL / ✅ BIEN")

The system prompt already uses this pattern for farewell rules and it works well.
The same approach should be applied to length:

```
❌ MAL (consulta de saldo):
"Hola María 👋 Entiendo que deseas conocer tu estado de cuenta. Con mucho gusto
te ayudo con esa consulta. Según nuestros registros, tienes un saldo pendiente de
$394,76 correspondiente a los meses de marzo y abril. Te recomendamos ponerte al
día lo antes posible para poder inscribir para el próximo año escolar..."

✅ BIEN (misma consulta):
"Hola María. Tienes $394,76 pendiente (meses de marzo y abril).
Para coordinar el pago: pagos@ueipab.edu.ve 😊"
```

---

## Traceability: What Logs Exist

### Glenda Supervisor (already running)
- **Log:** `/var/log/glenda_supervisor.log`
- **Runs:** every 2h weekdays 07:00–21:00 VET
- **Captures:** scores 1–5 per conversation, issues, highlights
- **Limitation:** reviews last 2h window only; no cumulative brevity metric
- **Access:** `tail -200 /var/log/glenda_supervisor.log`

### Production Conversation Records
- **Model:** `ai.agent.conversation` + `ai.agent.message`
- **248 conversations** (all-time), **542 outbound** messages as of 2026-05-23
- **Access via XML-RPC** (config in `config/production.json`)
- **Queryable fields:** `body` (text), `create_date`, `direction`, `conversation_id.state`
- **Current gap:** no `char_count` field, no per-message scoring

### What's NOT tracked yet
- Response length per message (no field, must calculate from `body`)
- Parent read/reaction signal (WhatsApp read receipts not captured)
- Drop-off point within a conversation (which message was last before timeout)

---

## Implementation Log

| # | Action | Version | Status | Date |
|---|--------|---------|--------|------|
| 1 | Venezuelan community context block | v57.15 | ✅ Done | 2026-05-24 |
| 2 | Explicit line-limit rules + MAL/BIEN examples | v57.15 | ✅ Done | 2026-05-24 |
| 3 | `max_tokens` 1024 → 512 | v57.15 | ✅ Done | 2026-05-24 |
| 4 | Dropout correlation analysis (`glenda_dropout_analysis.py`) | — | ✅ Done | 2026-05-24 |
| 5 | Pricing response template (promo + annual costs mandatory) | v57.16 | ✅ Done | 2026-05-24 |
| 6 | Context-aware menu (returning contacts skip full menu) | v57.17 | ✅ Done | 2026-05-24 |
| 7 | Supervisor brevity criterion (split from tone) | — | ⏳ Sprint 2 | — |
| 8 | Char_count metric in supervisor digest | — | ⏳ Sprint 2 | — |
| 9 | Weekly dropout metric snapshot (scheduled script) | — | ⏳ Sprint 2 | — |
| 10 | Budget results content update (pricing + Seguro) | — | 🔒 2026-05-26 | — |

---

## Files Changed

| File | Change | Version |
|------|--------|---------|
| `skills/general_inquiry.py` | Community block, line-limit rules, pricing template, context-aware menu | v57.15–17 |
| `models/claude_service.py` | `max_tokens` 1024 → 512 (Claude + OpenAI paths) | v57.15 |
| `scripts/glenda_dropout_analysis.py` | New — dropout correlation analysis tool | — |

**Pending:**
| File | Change | Version |
|------|--------|---------|
| `scripts/glenda_supervisor.py` | Split brevity criterion; add char_count metric | Sprint 2 |

---

## Success Metrics

Measure via `glenda_dropout_analysis.py` at 2-week mark (re-run 2026-06-07):

| Metric | Baseline (pre-v57.15) | Target |
|--------|----------------------|--------|
| Avg first reply length | 861 chars | < 450 chars |
| First replies > 800 chars | 65% | < 25% |
| Resolution rate (all convs) | 49% (123/250) | > 55% |
| Pricing responses with promo + annual | 38% | > 90% |

---

## Related Files

- System prompt: `addons/ueipab_ai_agent/skills/general_inquiry.py` → `get_system_prompt()`
- Supervisor: `scripts/glenda_supervisor.py`
- Supervisor log: `/var/log/glenda_supervisor.log`
- Technical patterns: [GLENDA_TECHNICAL_PATTERNS.md](GLENDA_TECHNICAL_PATTERNS.md)
- Module overview: [GLENDA_AI_AGENT_OVERVIEW.md](GLENDA_AI_AGENT_OVERVIEW.md)
- AI Agent module: [AI_AGENT_MODULE.md](AI_AGENT_MODULE.md)
