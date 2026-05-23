# Glenda UX Improvement Plan — "Habla Mucho"

**Status:** Planning | **Created:** 2026-05-23 | **Priority:** High

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

## Current State (Production Data — 2026-05-23)

| Metric | Value |
|--------|-------|
| Total conversations | 248 |
| Total outbound messages | 542 |
| Avg outbound message length | **468 chars** |
| Messages > 500 chars | ~37% of last 30 |
| Messages > 800 chars | ~23% of last 30 |
| Max observed AI response | ~830 chars (AI-generated) |
| Claude `max_tokens` ceiling | **1,024 tokens ≈ 800 chars** |

### Real examples of verbose responses

Glenda answering a balance query (typically > 500 chars):
- Greets with full name + bot intro (again, even mid-conversation)
- Restates the question before answering
- Gives the answer
- Adds context nobody asked for
- Offers 3 next steps
- Ends with... a question

The system prompt already says `"parrafo corto primero"` but it's line 12 in a 200-line prompt. Claude buries it.

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

## Implementation Priority

| # | Action | Effort | Impact | When |
|---|--------|--------|--------|------|
| 1 | Add Venezuelan context block to system prompt | 30 min | High | Immediate |
| 2 | Add explicit line limits to INSTRUCCIONES block | 1h | High | Immediate |
| 3 | Reduce `max_tokens` 1024 → 512 | 5 min | Medium-High | Immediate |
| 4 | Run dropout correlation query | 1h | Diagnostic | Before #1-3 ideally |
| 5 | Update supervisor to score brevity separately | 2h | Medium | Sprint 2 |
| 6 | Add char_count metric to supervisor digest | 1h | Medium | Sprint 2 |
| 7 | Manual conversation audit (20–30 samples) | 2–3h | Diagnostic | If data unclear |
| 8 | Add MAL/BIEN examples to system prompt | 2h | High | After audit |

---

## Files to Change

| File | Change | Angle |
|------|--------|-------|
| `skills/general_inquiry.py` | Add brevity rules + Venezuelan context block | 2, 3 |
| `models/claude_service.py` | `max_tokens` 1024 → 512 | 1 |
| `scripts/glenda_supervisor.py` | Split brevity criterion; add char_count metric | 4, 5 |

---

## Success Metrics

After changes are deployed, measure via supervisor log over 2 weeks:

| Metric | Baseline (now) | Target |
|--------|---------------|--------|
| Avg outbound message length | 468 chars | < 300 chars |
| Messages > 500 chars | ~37% | < 15% |
| Supervisor avg score | TBD (pull from logs) | ≥ 4.0 |
| Conversation resolution rate | TBD | +5–10% vs baseline |

---

## Related Files

- System prompt: `addons/ueipab_ai_agent/skills/general_inquiry.py` → `get_system_prompt()`
- Supervisor: `scripts/glenda_supervisor.py`
- Supervisor log: `/var/log/glenda_supervisor.log`
- Technical patterns: [GLENDA_TECHNICAL_PATTERNS.md](GLENDA_TECHNICAL_PATTERNS.md)
- Module overview: [GLENDA_AI_AGENT_OVERVIEW.md](GLENDA_AI_AGENT_OVERVIEW.md)
- AI Agent module: [AI_AGENT_MODULE.md](AI_AGENT_MODULE.md)
