# Glenda Calibration Programme

**Status:** Active | **Module:** `ueipab_ai_agent` v17.0.1.32.0 | **Started:** 2026-05-11

## Overview

Internal employee testing programme for Glenda (AI agent). 20 enrolled employees test
Glenda's capabilities via WhatsApp and submit improvement suggestions. Participants who
reach the bonus threshold receive a cash bonus.

## Bonus Criteria

| Requirement | Threshold |
|-------------|-----------|
| Conversations with Glenda | ≥ 3 |
| Suggestions submitted | ≥ 1 |
| Deadline | **Friday 30 May 2026** |

## Enrolment

- **Total seats:** 20 (closed — no new enrolments this round)
- **Round 1 enrolled:** 20 employees via `glenda_calibracion_v1` notice_key
- **Pending (YUDELYS BRITO):** submitted institutional number — correction email sent 2026-05-11; awaiting personal WA re-submission
- **Next round:** announce via HR when capacity opens

### Enrolled participants (Round 1)

| Employee | WA | Status |
|----------|----|--------|
| ALEJANDRA LOPEZ | +58 416 4664427 | ✓ Email sent |
| ARCIDES ARZOLA | +58 412 4840948 | ✓ Email sent |
| Daniel Bongianni | +58 424 8024456 | ✓ Email sent |
| DAVID HERNANDEZ | +58 414 8014910 | ✓ Email sent |
| FLORMAR HERNANDEZ | +58 424 9005590 | ✓ Email sent |
| GLADYS BRITO CALZADILLA | +58 412 3394333 | ✓ Email sent |
| Gustavo Perdomo | +58 414 2337463 | ✓ Pilot |
| HEYDI RON | +58 424 8440445 | ✓ Email sent |
| Jessica Bolivar | +58 424 8873639 | ✓ Email sent |
| JOSEFINA RODRIGUEZ | +58 412 5837109 | ✓ Email sent |
| LUIS RODRIGUEZ | +58 412 1842465 | ✓ Email sent |
| LUISA ELENA ABREU | +58 424 8985056 | ✓ Email sent |
| MAGYELYS MATA | +58 414 5427506 | ✓ Email sent |
| MAIRELSY MOTTA | +58 412 1106077 | ✓ Email sent |
| MARIA NIETO | +58 414 5426892 | ✓ Email sent |
| Maria Figuera | +58 424 8592864 | ✓ Email sent |
| NIDYA LIRA | +58 424 8532157 | ✓ Email sent |
| ROBERT QUIJADA | +58 424 8981642 | ✓ Email sent |
| YARITZA BRUCES | +58 424 8795332 | ✓ Email sent |
| YUDELYS BRITO | — | ⚠️ Pending personal WA |

## Status as of 2026-05-12 (Day 2)

- 14/20 started (at least 1 conversation with Glenda)
- 6/20 not started yet: ARCIDES ARZOLA, DAVID HERNANDEZ, Daniel Bongianni, MAGYELYS MATA, MARIA NIETO, ROBERT QUIJADA
- 3 suggestions logged: LUISA ELENA ABREU (conocimiento + asistencia), Maria Figuera (flujo)
- 0/20 bonus-eligible (deadline May 30)
- Closest to bonus: JOSEFINA RODRIGUEZ (3 convs, needs 1 suggestion), Maria Figuera (2 convs + 1 suggestion, needs 1 conv)
- Group status report emailed 2026-05-12 to all participants via `recursoshumanos@ueipab.edu.ve`

## Status as of 2026-05-11 (Day 1)

- 13/20 testers already contacted Glenda (before guide email — from enrolment flow)
- 0 formal suggestions logged (guide emails just delivered)
- 0/20 bonus-eligible (early stage — deadline May 30)
- Most active: JOSEFINA RODRIGUEZ, Maria Figuera, NIDYA LIRA, YARITZA BRUCES (2 convs each)

## Tracking (Odoo)

- **Suggestions:** `AI Agent → Programa Calibración → Sugerencias`
- **Bonus tracker:** `AI Agent → Programa Calibración → Seguimiento de Bono`
- Auto-flag: `bonus_eligible = True` when ≥3 convs + ≥1 feedback

## Testing Scenarios (sent to employees)

1. Saludo y presentación — observe Glenda's self-introduction
2. Tasa BCV — "¿Cuál es la tasa BCV?" / "$100 en bolívares?"
3. Consulta de asistencia — attendance report or correction request
4. Información institucional — fees, schedules, extracurriculars
5. Pregunta difícil — something they think Glenda can't answer
6. Sugerencia — "tengo una sugerencia: ..." (auto-logged)
7. Escenario representante — act as a parent seeking enrollment info

## Technical Architecture

### `ai.agent.feedback` model (new in v17.0.1.32.0)

Fields: `employee_id`, `conversation_id`, `wa_number`, `category`, `suggestion`, `state`, `date`, `notes`

Categories: `flujo`, `respuesta`, `idioma`, `asistencia`, `conocimiento`, `tecnico`, `otro`

States: `pending` → `reviewed` → `implemented` / `rejected`

### Calibration mode in `general_inquiry` skill

- `get_context()` checks conversation phone digits against `glenda_calibracion_v1` ack records
- If match → `is_calibration_tester=True` injected into context
- `get_system_prompt()` adds transparent testing-mode block:
  - Glenda greets by name, can admit she's an AI, acknowledges limitations
  - Instructs `ACTION:LOG_FEEDBACK:category|suggestion` capture
- `process_ai_response()` → `_handle_log_feedback()` creates `ai.agent.feedback` record

### `hr.notice.acknowledgment` computed fields (v17.0.1.32.0)

Inherited in `ueipab_ai_agent` (`hr_notice_ack_calibration.py`):
- `calibration_conversation_count` — counts `general_inquiry` convs by WA digits
- `calibration_feedback_count` — counts `ai.agent.feedback` by employee
- `bonus_eligible` — computed bool

### Send script

`scripts/send_calibration_programme_email.py` — set `PILOT_ONLY=False`, `ALREADY_SENT` to re-run for new batches. Always requires `env.cr.commit()` (Odoo shell does not auto-commit).

### Status report script

`scripts/send_calibration_status_report.py` — queries production via XML-RPC, builds an HTML group progress report in Spanish, and queues it to `recursoshumanos@ueipab.edu.ve`. Run any time to send an updated scoreboard to HR (then forward manually to all participants). Includes: KPI chips, scoreboard table per participant (color-coded), and feedback suggestions received.

## WA Number Convention

All enrolled employees stored in `+58 XXX XXXXXXX` format (space-separated) on both:
- `hr.notice.acknowledgment.wa_number`
- `hr.employee.mobile_phone`

Phone matching uses digit-only comparison (`re.sub(r'\D', '', phone)`) to handle format variations from MassivaMóvil API.

## Key Dates

| Date | Event |
|------|-------|
| 2026-05-10 | Enrolment emails sent (calibration form) |
| 2026-05-11 | 20 employees enrolled, WA numbers normalized |
| 2026-05-11 | `ueipab_ai_agent` v17.0.1.32.0 deployed to production |
| 2026-05-11 | Guide emails sent to 19 employees (YUDELYS BRITO pending) |
| 2026-05-12 | Day 2 group status report sent to all participants (14/20 started, 3 suggestions) |
| 2026-05-30 | **Bonus deadline** |
