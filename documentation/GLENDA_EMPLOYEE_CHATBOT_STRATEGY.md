# Glenda Employee Chatbot Strategy — Three-Layer Plan

**Status:** Planned | **Date:** 2026-05-14  
**Context:** OdooBot private DM bridge (Layer 1) already live in production as of 2026-05-14.

---

## Overview

Three progressive layers of AI-assisted employee interaction, each building on the previous.
All layers reuse the same `mail.bot` inheritance pattern and `_INSTITUTIONAL_KNOWLEDGE` block.

```
┌─────────────────────────────────────────────────────────────────┐
│  Layer 3 — Chatter with Record Context      (Future, ~3 days)   │
│  Payslip / attendance / contract chatter → Glenda sees data     │
├─────────────────────────────────────────────────────────────────┤
│  Layer 2 — Group Channel @mention           (Next, ~1 day)      │
│  #consultas-glenda channel → team Q&A, shared answers           │
├─────────────────────────────────────────────────────────────────┤
│  Layer 1 — Private OdooBot DM               (Done ✅)           │
│  Any employee → OdooBot sidebar → private chat                  │
└─────────────────────────────────────────────────────────────────┘
```

**Excluded:** Email alias/reply-to chatbot (Option B) — inferior UX vs real-time
chat for employees who already have Odoo access. Complex to implement correctly.

---

## Layer 1 — Private OdooBot DM (Done ✅)

**File:** `addons/ueipab_ai_agent/models/mail_bot_glenda.py`  
**Since:** v17.0.1.40.2 (2026-05-14)

Any internal Odoo user opens OdooBot in the Discuss sidebar and chats privately.
Glenda answers general questions: pricing, policies, payment methods, discounts.

**Limitation:** Glenda has no context about who is asking or what record they are viewing.
Answers are general, not personalised to the employee's data.

---

## Layer 2 — Group Channel @mention

**Estimated effort:** 1 day  
**Change:** Extend `_get_answer` to also handle `channel_type == 'channel'` when OdooBot is @mentioned.

### How It Works

```
HR creates a Discuss channel: #consultas-glenda (or #rrhh)
        ↓
Employee types: "@OdooBot ¿cuánto cuesta la inscripción para 2 hijos?"
        ↓
_get_answer() fires (channel_type='channel', OdooBot was mentioned)
        ↓
Glenda responds publicly in the channel
        ↓
All team members see the question + answer
```

### Why This Matters

- One employee asks → 20 employees learn — reduces repeated questions to HR
- Natural for policy Q&A, pricing doubts, general institutional knowledge
- Same precedent as Slack AI, Microsoft Teams Copilot, ChatGPT in Slack

### Implementation

```python
# In mail_bot_glenda.py — extend the channel_type check
GLENDA_CHANNEL_TYPES = ('chat', 'livechat', 'channel')

def _get_answer(self, record, body, values, command):
    channel_type = getattr(record, 'channel_type', None)
    if channel_type not in GLENDA_CHANNEL_TYPES:
        return super()._get_answer(record, body, values, command)

    # For group channels, only fire if OdooBot was @mentioned
    if channel_type == 'channel':
        bot_partner_id = self.env.ref('base.partner_root').id
        if bot_partner_id not in (values.get('partner_ids') or []):
            return super()._get_answer(record, body, values, command)
    ...
```

### Configuration

1. Create a Discuss channel: `#consultas-glenda`
2. Add OdooBot as a member
3. Announce to staff: "@OdooBot [your question]" in this channel

---

## Layer 3 — Chatter with Record Context (Highest Value)

**Estimated effort:** 3 days  
**Pattern:** Override `_message_post_after_hook` on specific HR models.

### How It Works

```
Employee opens their payslip in Odoo
        ↓
Types a question in the chatter: "¿Por qué cambió mi monto este mes?"
        ↓
Hook fires — Glenda reads:
  • Payslip lines (rule codes, amounts)
  • Employee name, contract type (V2/V1)
  • Batch period, structure
        ↓
Glenda responds contextually in the chatter:
  "Tu quincena fue $207.94 porque se aplicó el 5% de descuento
   hermano sobre la base $218.88 (1er alumno inscrito 2026-2027).
   Si hay un error, escribe a recursoshumanos@ueipab.edu.ve."
```

### Models to Support (Priority Order)

| Model | Employee Question Type | Context Glenda Reads |
|-------|----------------------|---------------------|
| `hr.payslip` | "¿Por qué cambió mi monto?" | Lines, structure, period, gross/net |
| `hr.attendance.report` | "¿Por qué me marca ausente?" | Attendance records, correction status |
| `hr.leave` / vacation | "¿Cuántos días me quedan?" | Leave balance, approved/pending |
| `hr.contract` | "¿Cuál es mi salario base?" | Contract fields, V2 salary |

### Scoping — Critical Constraint

Must fire ONLY on HR models. The `_message_post_after_hook` is on `mail.thread`
which covers ALL Odoo records. Wrong scoping = Glenda fires on sales orders,
invoices, purchase orders — unacceptable.

**Safe pattern:**

```python
class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def _message_post_after_hook(self, message, msg_vals):
        super()._message_post_after_hook(message, msg_vals)
        # Only if the author is a human employee (not a bot, not admin)
        if self._should_glenda_respond(message):
            self._glenda_respond_in_chatter(message)
```

### System Prompt Enrichment (Per Model)

```python
def _build_payslip_context(self):
    lines = {l.code: l.total for l in self.line_ids}
    return (
        f"NÓMINA EN CONTEXTO:\n"
        f"- Empleado: {self.employee_id.name}\n"
        f"- Período: {self.date_from} — {self.date_to}\n"
        f"- Estructura: {self.struct_id.code}\n"
        f"- Salario bruto: ${lines.get('GROSS', 0):,.2f}\n"
        f"- Neto a pagar: ${lines.get('VE_NET_V2', lines.get('NET', 0)):,.2f}\n"
        f"- Estado: {self.state}\n"
    )
```

---

## Comparison Table

| Aspect | Layer 1 (Done) | Layer 2 (Next) | Layer 3 (Future) |
|--------|---------------|----------------|------------------|
| Context-aware | No | No | **Yes** |
| Private | Yes | No (public channel) | Yes (chatter) |
| Team knowledge sharing | No | **Yes** | No |
| Setup effort | Done | 1 day | 3 days |
| Claude cost | ~$0.002/conv | ~$0.002/conv | ~$0.003/conv (longer prompt) |
| MassivaMóvil cost | $0 | $0 | $0 |
| Best for | General Q&A | Policy/pricing FAQ | Payslip/attendance help |

---

## Explicitly Out of Scope

**Email alias / reply-to chatbot** — not recommended:
- Email is async (minutes, not seconds)
- Odoo incoming mail has edge cases (threading, bounces, duplicates)
- Employees have Odoo access — real-time chat is always better UX
- Complex alias + routing infrastructure for inferior result

---

## Related Files

| File | Role |
|------|------|
| `addons/ueipab_ai_agent/models/mail_bot_glenda.py` | Layer 1 & 2 — extend here |
| `addons/ueipab_ai_agent/skills/general_inquiry.py` | `_INSTITUTIONAL_KNOWLEDGE` shared |
| `documentation/LIVECHAT_GLENDA_CUSTOMER_PLAN.md` | Customer-facing livechat plan |
| `documentation/AI_AGENT_MODULE.md` | Full module reference |
