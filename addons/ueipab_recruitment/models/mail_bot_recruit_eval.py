"""
Glenda OdooBot — Recruitment Evaluation Handler
================================================
Extends mail.bot to intercept OdooBot DM sessions when a recruitment eval
session is armed (via hr.applicant action_start_eval or keyword trigger).

Architecture
------------
Phase 1 — MCQ quiz (10 questions, candidate types A/B/C/D)
  • Score 0–10; gate threshold ≥ 7 to proceed to Phase 2
Phase 2 — Conversational (7 turns, free text)
  • Dual-AI scoring: Claude Haiku (primary) + GPT-4o-mini (validator)
  • Writes ueipab_skill_score / ueipab_skill_score_gpt / ueipab_eval_consensus
  • CEO OdooBot DM with full scorecard

Session state — stored in ir.config_parameter key:
  recruit.eval.session.{uid}  →  JSON (see _new_session)

Question banks — keyed by job_key resolved from hr.job name.
Future upgrade: swap _load_quiz_questions() to read from
ueipab.recruitment.quiz ORM model (UI-editable, Phase 2 roadmap).
"""
import json
import logging
import re
import textwrap

import requests

from odoo import models

_logger = logging.getLogger(__name__)

# ── Scoring gate ────────────────────────────────────────────────────────────
_MCQ_PASS_THRESHOLD = 7   # out of 10 — change here to recalibrate

# ── Salary / compensation keyword detector ───────────────────────────────────
_SALARY_KEYWORDS = frozenset([
    'sueldo', 'salario', 'pago', 'cuanto ofrecen', 'cuánto ofrecen',
    'cuanto gana', 'cuánto gana', 'cuanto pagan', 'cuánto pagan',
    'compensaci', 'remuner', 'beneficio', 'ingreso mensual', 'cuanto cobra',
    'cuánto cobra', 'cuanto es el', 'cuánto es el',
])

# ── Keyword triggers for ad-hoc Discuss start ────────────────────────────────
_EVAL_KEYWORDS = {'evaluar', 'iniciar evaluacion', 'iniciar evaluación', 'eval'}

# ── MCQ question banks (keyed by job_key) ────────────────────────────────────
# Each question: q=text shown to candidate, answer=correct letter, note=why.
# Options are embedded in q as a numbered line block.
_QUIZ_BANKS = {
    'contabilidad': [
        {
            'q': (
                "Pregunta 1 de 10:\n\n"
                "La institución recibe pagos de representantes. "
                "¿Cuál de estos medios NO es aceptado actualmente en Venezuela?\n\n"
                "A. Transferencia bancaria\n"
                "B. Pago Móvil\n"
                "C. Cheque personal\n"
                "D. Zelle\n\n"
                "Escribe la letra de tu respuesta:"
            ),
            'answer': 'C',
            'note': 'Los cheques están descontinuados en el sistema financiero venezolano.',
        },
        {
            'q': (
                "Pregunta 2 de 10:\n\n"
                "Al facturar la mensualidad escolar de un representante, "
                "¿qué aplica respecto al IVA?\n\n"
                "A. Se cobra 16% de IVA estándar\n"
                "B. Se cobra 8% de IVA reducido por ser servicio básico\n"
                "C. El servicio educativo privado está exento de IVA\n"
                "D. Solo pagan IVA los representantes que usan Zelle\n\n"
                "Escribe la letra de tu respuesta:"
            ),
            'answer': 'C',
            'note': 'Servicios educativos privados son exentos de IVA bajo la LIVA venezolana.',
        },
        {
            'q': (
                "Pregunta 3 de 10:\n\n"
                "Un representante paga su mensualidad vía Zelle en dólares. "
                "¿Qué impuesto adicional aplica sobre ese pago?\n\n"
                "A. IVA 16%\n"
                "B. IGTF 3% por pago en divisa\n"
                "C. ISR 10% sobre la transacción\n"
                "D. Ningún impuesto — servicios educativos son completamente exentos\n\n"
                "Escribe la letra de tu respuesta:"
            ),
            'answer': 'B',
            'note': (
                'IGTF (3%) aplica sobre pagos en divisas recibidos por personas jurídicas. '
                'La exención educativa cubre el IVA, no el IGTF.'
            ),
        },
        {
            'q': (
                "Pregunta 4 de 10:\n\n"
                "La institución recibe Bs. 200.000 por Pago Móvil por mensualidad. "
                "¿Cuál es el asiento contable correcto?\n\n"
                "A. Débito Cuentas por Cobrar / Crédito Banco\n"
                "B. Débito Banco / Crédito Ingresos por Servicios\n"
                "C. Débito Gastos Operativos / Crédito Banco\n"
                "D. Débito Ingresos / Crédito Cuentas por Pagar\n\n"
                "Escribe la letra de tu respuesta:"
            ),
            'answer': 'B',
            'note': 'El cobro aumenta el activo (Banco) y reconoce el ingreso.',
        },
        {
            'q': (
                "Pregunta 5 de 10:\n\n"
                "¿Qué información es OBLIGATORIA en una factura válida según el SENIAT?\n\n"
                "A. Nombre completo del estudiante y grado\n"
                "B. Número de control, RIF del emisor, fecha y monto\n"
                "C. Firma del representante y copia del pago\n"
                "D. Número de cuenta bancaria del colegio\n\n"
                "Escribe la letra de tu respuesta:"
            ),
            'answer': 'B',
            'note': 'Campos mínimos exigidos por el SENIAT para cualquier factura.',
        },
        {
            'q': (
                "Pregunta 6 de 10:\n\n"
                "UEIPAB paga una factura de un proveedor de mantenimiento: "
                "Bs. 500.000 más 16% IVA (Bs. 80.000). Si la institución es agente "
                "de retención IVA, ¿cuánto retiene de ese IVA y a quién lo paga?\n\n"
                "A. Retiene el 100% del IVA (Bs. 80.000) y lo entrega al SENIAT\n"
                "B. Retiene el 75% del IVA (Bs. 60.000) y lo entera al SENIAT; "
                "paga al proveedor solo Bs. 20.000 de IVA\n"
                "C. No retiene nada porque la institución está exenta de IVA\n"
                "D. Retiene el 16% sobre el total de la factura incluyendo el monto base\n\n"
                "Escribe la letra de tu respuesta:"
            ),
            'answer': 'B',
            'note': (
                'Agentes de retención IVA retienen 75% del IVA facturado y lo declaran al SENIAT. '
                'La exención educativa aplica a las ventas del colegio, no a sus compras.'
            ),
        },
        {
            'q': (
                "Pregunta 7 de 10:\n\n"
                "El colegio paga honorarios profesionales al contador externo. "
                "¿Qué obligación fiscal tiene UEIPAB sobre ese pago?\n\n"
                "A. Ninguna — el contador declara su propio ISLR como persona natural\n"
                "B. Retener ISLR según la tarifa aplicable, emitir comprobante de retención "
                "al proveedor y declararlo mensualmente al SENIAT\n"
                "C. Pagar el IVA correspondiente a los honorarios profesionales\n"
                "D. Solo reportarlo en el libro de ventas al cierre del año fiscal\n\n"
                "Escribe la letra de tu respuesta:"
            ),
            'answer': 'B',
            'note': (
                'Quien paga honorarios profesionales debe retener ISLR, emitir el comprobante '
                'de retención al proveedor y declararlo vía portal SENIAT mensualmente.'
            ),
        },
        {
            'q': (
                "Pregunta 8 de 10:\n\n"
                "Al conciliar el banco de octubre, el saldo contable en Odoo es Bs. 1.200.000 "
                "pero el extracto bancario muestra Bs. 1.350.000. ¿Cuál es el primer paso?\n\n"
                "A. Ajustar el saldo de Odoo al del banco sin investigar para cuadrar rápido\n"
                "B. Identificar todas las partidas en tránsito: transferencias no reflejadas "
                "en libros, depósitos no acreditados, y posibles errores de registro\n"
                "C. Emitir una nota de débito por la diferencia de Bs. 150.000\n"
                "D. Reportar el error directamente al SENIAT como discrepancia contable\n\n"
                "Escribe la letra de tu respuesta:"
            ),
            'answer': 'B',
            'note': (
                'La conciliación identifica y documenta cada diferencia antes de cualquier '
                'ajuste; el objetivo es explicar la diferencia, no igualar saldos sin entender la causa.'
            ),
        },
        {
            'q': (
                "Pregunta 9 de 10:\n\n"
                "¿Hasta qué fecha vencen las declaraciones de retenciones de IVA del período "
                "anterior para un contribuyente ordinario?\n\n"
                "A. El último día hábil del mismo mes en que ocurrieron\n"
                "B. El día 15 del mes siguiente al período declarado\n"
                "C. El primer día hábil del mes siguiente\n"
                "D. Solo se declaran de forma trimestral junto con el IVA propio\n\n"
                "Escribe la letra de tu respuesta:"
            ),
            'answer': 'B',
            'note': (
                'Las retenciones IVA se declaran y pagan hasta el día 15 del mes siguiente '
                '(contribuyentes ordinarios). Contribuyentes especiales tienen calendario escalonado.'
            ),
        },
        {
            'q': (
                "Pregunta 10 de 10:\n\n"
                "Además de descontar IVSS y FAOV del salario del trabajador, "
                "¿qué debe hacer la institución cada mes?\n\n"
                "A. Nada más — el descuento en nómina es suficiente obligación\n"
                "B. Pagar el aporte patronal correspondiente (IVSS 9-11%, FAOV 2%) "
                "y presentar la planilla ante el organismo dentro del plazo\n"
                "C. Solo reportarlo al SENIAT en el libro de compras al cierre del año\n"
                "D. Acumularlo durante el año y pagar junto con el ISLR en la declaración anual\n\n"
                "Escribe la letra de tu respuesta:"
            ),
            'answer': 'B',
            'note': (
                'El empleador aporta su parte patronal además de retener la del trabajador '
                'y debe presentar y pagar la planilla mensualmente. '
                'El incumplimiento impide obtener la Solvencia Laboral.'
            ),
        },
    ],
}

# ── Phase 2 conversational questions ─────────────────────────────────────────
# Turn index 2 is the follow-up probe — uses {prev_answer} placeholder filled
# from the candidate's Turn 1 (IGTF) response.
_CONV_QUESTIONS = [
    "Bien, empecemos. Descríbeme brevemente tu experiencia más reciente en contabilidad o administración.",
    (
        "Un representante realizó el pago de su mensualidad mediante Zelle en USD. "
        "¿Qué impuesto aplica sobre esa transacción, cuál es la tasa, y quién lo paga?"
    ),
    None,  # filled dynamically: follow-up on turn 1 answer
    (
        "Clasificá estas 3 transacciones y decime el asiento de débito y crédito para cada una:\n"
        "1. Pago de nómina del colegio\n"
        "2. Cobro de mensualidad de un representante\n"
        "3. Compra de papelería para la oficina"
    ),
    (
        "Descargaste el extracto bancario de octubre. El saldo en Odoo es Bs. 1.200.000 "
        "y el banco muestra Bs. 1.350.000. ¿Qué hacés paso a paso para encontrar y "
        "documentar la diferencia antes de que llegue el contador?"
    ),
    (
        "El contador externo llega el viernes para el cierre y necesita las facturas de "
        "compra de octubre con sus comprobantes de retención IVA y las planillas IVSS/FAOV "
        "pagadas ese mes. ¿Cómo tendrías organizado ese archivo y en cuánto tiempo lo encontrarías?"
    ),
    "¿Cuál es el área de contabilidad o cumplimiento fiscal donde sentís que tenés más por aprender?",
    "¿Tenés alguna pregunta sobre el cargo, el equipo o cómo sería tu primer mes?",
]

# ── Phase 2 scoring prompt ────────────────────────────────────────────────────
_SCORING_PROMPT = textwrap.dedent("""\
    Evaluate this recruitment conversation for "Auxiliar de Contabilidad y Administración"
    at UEIPAB, a Venezuelan private school. Score 0-100 on:

    - Technical accuracy (40%): accounting knowledge, Venezuelan fiscal awareness.
      CRITICAL CONTEXT: educational services are IVA-EXEMPT (LIVA); the applicable
      tax on foreign-currency payments is IGTF 3%, not IVA. The LOE prohibits
      interest charges on late educational service balances. Correct answers must
      reflect Venezuelan practice, not generic Latin American accounting.

    - Reasoning quality (30%): explains WHY, not just WHAT. Shows process thinking.
      Describes steps, not just outcomes.

    - Communication clarity (20%): professional, organized Spanish. Appropriate
      tone for a school environment.

    - Self-awareness (10%): honest about knowledge gaps, not overconfident.

    SCORING INSTRUCTION: Penalize answers that are textbook-perfect but lack applied
    specificity or Venezuelan context. Real practitioners say "depende" and make small
    errors. AI-generated answers are over-structured and complete. Reward genuine
    struggle and practical examples from real experience.

    Return ONLY valid JSON (no markdown fences):
    {
      "score": <int 0-100>,
      "strengths": ["...", "..."],
      "gaps": ["...", "..."],
      "summary": "<2 sentences in Spanish>",
      "manager_summary": "<plain-language decision aid for HR manager in Spanish, 4-6 bullet lines using • character, covering: (1) confidence level and what it means, (2) 2 key strengths, (3) 1-2 red flags, (4) bottom-line hiring recommendation>"
    }
""")


class MailBotRecruitEval(models.AbstractModel):
    _inherit = 'mail.bot'

    # ── Entry point ──────────────────────────────────────────────────────────

    def _get_answer(self, record, body, values, command):
        if not (hasattr(record, 'channel_type') and record.channel_type == 'chat'):
            return super()._get_answer(record, body, values, command)

        ICP = self.env['ir.config_parameter'].sudo()
        session_key = f'recruit.eval.session.{self.env.user.id}'
        session_json = ICP.get_param(session_key, False)

        # Active eval session — route to handler regardless of dry_run
        if session_json:
            try:
                session = json.loads(session_json)
                return self._eval_dispatch(record, body, ICP, session_key, session)
            except Exception:
                _logger.exception("Recruit eval dispatch error — clearing session")
                ICP.set_param(session_key, '')
                return (
                    "Ocurrió un error en la sesión de evaluación. "
                    "Por favor, inicia de nuevo desde el formulario del candidato."
                )

        # Keyword trigger for ad-hoc start from Discuss
        plain = _plain(body)
        if plain.strip().lower() in _EVAL_KEYWORDS:
            return self._eval_keyword_start(ICP, session_key)

        return super()._get_answer(record, body, values, command)

    # ── Keyword-triggered setup ──────────────────────────────────────────────

    def _eval_keyword_start(self, ICP, session_key):
        """HR typed 'evaluar' without using the form button — guided setup."""
        pending_key = f'recruit.eval.setup.{self.env.user.id}'
        ICP.set_param(pending_key, 'awaiting_name')
        return (
            "Entendido, vamos a iniciar una evaluación.\n\n"
            "¿Cuál es el nombre completo del candidato que vas a evaluar?"
        )

    def _eval_dispatch(self, record, body, ICP, session_key, session):
        plain = _plain(body)
        state = session.get('state', 'identity_prompt')

        # Check if this is the second step of keyword setup (candidate name lookup)
        pending_key = f'recruit.eval.setup.{self.env.user.id}'
        pending = ICP.get_param(pending_key, False)
        if pending == 'awaiting_name' and not session_json_armed(session):
            return self._eval_setup_lookup(ICP, session_key, pending_key, plain)

        if state == 'identity_prompt':
            return self._eval_identity(ICP, session_key, session, plain)
        if state == 'mcq':
            return self._eval_mcq(ICP, session_key, session, plain)
        if state == 'phase2_gate':
            return self._eval_phase2_gate(ICP, session_key, session, plain)
        if state == 'conv':
            return self._eval_conv(record, ICP, session_key, session, plain)
        return "Sesión de evaluación en estado desconocido. Contacta al administrador."

    # ── Setup via keyword: find applicant by name ────────────────────────────

    def _eval_setup_lookup(self, ICP, session_key, pending_key, name_text):
        Applicant = self.env['hr.applicant'].sudo()
        candidates = Applicant.search([
            ('partner_name', 'ilike', name_text),
            ('stage_id.name', 'not in', ['Hired', 'Rejected']),
        ], limit=5)

        ICP.set_param(pending_key, '')

        if not candidates:
            return (
                f"No encontré ningún candidato activo con el nombre '{name_text}'.\n"
                "Verifica el nombre en el Kanban de Reclutamiento e intenta de nuevo con 'evaluar'."
            )

        if len(candidates) == 1:
            c = candidates[0]
            session = _new_session(c.id, 'in_person')
            ICP.set_param(session_key, json.dumps(session))
            c.sudo().write({
                'ueipab_evaluation_mode': 'in_person',
                'ueipab_eval_state': 'ai_evaluating',
            })
            return (
                f"Encontré a {c.partner_name} — {c.job_id.name or 'sin cargo'}.\n\n"
                "Sesión armada. Entrega el teclado al candidato.\n\n"
                + _identity_prompt()
            )

        lines = "\n".join(
            f"{i+1}. {c.partner_name} ({c.job_id.name or 'sin cargo'})"
            for i, c in enumerate(candidates)
        )
        ICP.set_param(f'recruit.eval.setup.candidates.{self.env.user.id}',
                      json.dumps([c.id for c in candidates]))
        ICP.set_param(pending_key, 'awaiting_choice')
        return (
            f"Encontré varios candidatos con ese nombre:\n\n{lines}\n\n"
            "Responde con el número (1, 2, …) para seleccionar."
        )

    # ── Identity confirmation ────────────────────────────────────────────────

    def _eval_identity(self, ICP, session_key, session, plain):
        applicant_id = session['applicant_id']
        applicant = self.env['hr.applicant'].sudo().browse(applicant_id)

        # Simple name match — supervisor already verified physical ID
        candidate_name = (applicant.partner_name or '').lower()
        words = [w for w in candidate_name.split() if len(w) > 2]
        matched = sum(1 for w in words if w in plain.lower())

        if matched >= 1 or len(plain) > 5:
            # Accept — in-person mode trusts the supervisor's physical check
            session['identity_confirmed'] = True
            session['state'] = 'mcq'
            session['q_idx'] = 0
            ICP.set_param(session_key, json.dumps(session))
            job_key = _resolve_job_key(applicant)
            questions = _load_quiz_questions(job_key)
            return (
                f"Perfecto, {applicant.partner_name.split()[0]}. Bienvenido/a a la evaluación técnica de UEIPAB.\n\n"
                "Responde cada pregunta con la letra correcta: A, B, C o D.\n"
                "No se muestran las respuestas hasta terminar. ¡Empecemos!\n\n"
                + questions[0]['q']
            )

        session['identity_attempts'] = session.get('identity_attempts', 0) + 1
        if session['identity_attempts'] >= 3:
            ICP.set_param(session_key, '')
            return (
                "No pude verificar tu identidad. La sesión ha sido cerrada. "
                "Por favor, contacta al evaluador."
            )
        ICP.set_param(session_key, json.dumps(session))
        return "No pude confirmar tu nombre. Por favor, escribe tu nombre completo tal como aparece en tu cédula."

    # ── MCQ state machine ────────────────────────────────────────────────────

    def _eval_mcq(self, ICP, session_key, session, plain):
        applicant_id = session['applicant_id']
        applicant = self.env['hr.applicant'].sudo().browse(applicant_id)
        job_key = _resolve_job_key(applicant)
        questions = _load_quiz_questions(job_key)
        q_idx = session['q_idx']

        letter = plain.strip().upper()
        if letter not in ('A', 'B', 'C', 'D'):
            return (
                "Por favor responde solo con la letra de tu opción: A, B, C o D."
            )

        correct = questions[q_idx]['answer']
        session['answers'].append({
            'q': q_idx,
            'given': letter,
            'correct': correct,
            'ok': letter == correct,
        })
        q_idx += 1
        session['q_idx'] = q_idx

        if q_idx < len(questions):
            ICP.set_param(session_key, json.dumps(session))
            return questions[q_idx]['q']

        # All questions answered — calculate score
        score = sum(1 for a in session['answers'] if a['ok'])
        session['quiz_score'] = score
        session['state'] = 'phase2_gate'
        ICP.set_param(session_key, json.dumps(session))

        # Write quiz results to applicant immediately
        applicant.sudo().write({
            'ueipab_quiz_score': score,
            'ueipab_quiz_answers': json.dumps(session['answers']),
            'ueipab_quiz_completed': True,
        })

        if score >= _MCQ_PASS_THRESHOLD:
            return (
                f"¡Terminaste el quiz! Obtuviste {score}/10 respuestas correctas.\n\n"
                "Bien hecho. Pasamos a una segunda parte más práctica: "
                "respuestas abiertas sobre situaciones reales del colegio.\n\n"
                "Escribe 'continuar' cuando estés listo/a."
            )
        else:
            # Below threshold — close session
            ICP.set_param(session_key, '')
            applicant.sudo().write({'ueipab_eval_state': 'ai_done'})
            _logger.info(
                "Eval session closed — below threshold: applicant=%s score=%s/%s",
                applicant_id, score, len(questions),
            )
            return (
                f"Gracias por completar la evaluación. Obtuviste {score}/10.\n\n"
                "Nuestro equipo revisará los resultados y estará en contacto contigo.\n"
                "Puedes entregar el teclado al evaluador."
            )

    # ── Phase 2 gate ─────────────────────────────────────────────────────────

    def _eval_phase2_gate(self, ICP, session_key, session, plain):
        if plain.strip().lower() in ('continuar', 'si', 'sí', 'listo', 'ok', 's'):
            session['state'] = 'conv'
            session['q_idx'] = 0
            session['conv_turns'] = []
            ICP.set_param(session_key, json.dumps(session))
            return _CONV_QUESTIONS[0]
        return "Escribe 'continuar' cuando estés listo/a para la segunda parte."

    # ── Phase 2 conversational ────────────────────────────────────────────────

    def _eval_conv(self, record, ICP, session_key, session, plain):
        turn_idx = session['q_idx']

        # Record this answer
        session['conv_turns'].append({'role': 'user', 'content': plain})
        turn_idx += 1
        session['q_idx'] = turn_idx
        ICP.set_param(session_key, json.dumps(session))

        if turn_idx < len(_CONV_QUESTIONS):
            q = _CONV_QUESTIONS[turn_idx]
            # Turn 2 is the follow-up probe — reference the IGTF turn answer
            if q is None:
                prev = session['conv_turns'][-1]['content'] if session['conv_turns'] else ''
                q = (
                    f"Mencionaste: \"{prev[:120]}{'...' if len(prev) > 120 else ''}\"\n\n"
                    "¿En qué situación ese impuesto NO aplicaría? Dame un ejemplo concreto."
                )
            session['conv_turns'].append({'role': 'assistant', 'content': q})
            ICP.set_param(session_key, json.dumps(session))
            return q

        # All conversational turns done — score
        session['state'] = 'scoring'
        if _is_salary_question(plain):
            session['last_was_salary_q'] = True
        ICP.set_param(session_key, json.dumps(session))
        return self._eval_score_and_close(ICP, session_key, session)

    # ── Dual-AI scoring ───────────────────────────────────────────────────────

    def _eval_score_and_close(self, ICP, session_key, session):
        applicant_id = session['applicant_id']
        applicant = self.env['hr.applicant'].sudo().browse(applicant_id)

        transcript = _build_transcript(session['conv_turns'])
        messages = [{'role': 'user', 'content': transcript}]

        # ── Claude score ──
        claude_score = 0
        claude_summary = ''
        claude_data = {}
        try:
            result = self.env['ai.agent.claude.service'].generate_response(
                system_prompt=_SCORING_PROMPT,
                messages=messages,
                model='claude-haiku-4-5-20251001',
            )
            claude_data = _parse_json_response(result.get('content', ''))
            claude_score = int(claude_data.get('score', 0))
            claude_summary = claude_data.get('summary', '')
            _logger.info("Eval Claude score: applicant=%s score=%s", applicant_id, claude_score)
        except Exception:
            _logger.exception("Claude scoring failed for applicant=%s", applicant_id)

        # ── GPT-4o-mini score ──
        gpt_score = 0
        try:
            gpt_score = _call_gpt_scoring(ICP, transcript)
            _logger.info("Eval GPT score: applicant=%s score=%s", applicant_id, gpt_score)
        except Exception:
            _logger.exception("GPT scoring failed for applicant=%s", applicant_id)

        # ── Consensus ──
        delta = abs(claude_score - gpt_score)
        if delta <= 15:
            consensus = 'high'
        elif delta <= 25:
            consensus = 'medium'
        else:
            consensus = 'low'

        quiz_score = session.get('quiz_score', 0)
        notes = (
            f"Quiz MCQ: {quiz_score}/10 | "
            f"Evaluación conversacional: Claude={claude_score}/100 GPT={gpt_score}/100 "
            f"Consenso={'Alta' if consensus == 'high' else 'Media' if consensus == 'medium' else 'Baja'} (Δ={delta})\n\n"
            + claude_summary
        )

        manager_summary = claude_data.get('manager_summary', '')

        applicant.sudo().write({
            'ueipab_skill_score':       float(claude_score),
            'ueipab_skill_score_gpt':   float(gpt_score),
            'ueipab_eval_consensus':    consensus,
            'ueipab_ai_eval_notes':     notes,
            'ueipab_manager_summary':   manager_summary,
            'ueipab_eval_state':        'ai_done',
        })

        ICP.set_param(session_key, '')
        _logger.info(
            "Eval complete: applicant=%s quiz=%s/10 claude=%s gpt=%s consensus=%s",
            applicant_id, quiz_score, claude_score, gpt_score, consensus,
        )

        self._eval_notify_ceo(applicant, quiz_score, claude_score, gpt_score, consensus, delta)

        salary_ack = ''
        if session.get('last_was_salary_q'):
            salary_ack = (
                "Sobre tu pregunta de compensación: los detalles de sueldo y beneficios "
                "los conversaremos en la siguiente etapa del proceso, si avanzás en la selección.\n\n"
            )

        return (
            salary_ack
            + "Gracias, hemos terminado la evaluación técnica.\n\n"
            "El equipo de UEIPAB revisará los resultados y se pondrá en contacto contigo "
            "a la brevedad.\n\n"
            "Puedes entregar el teclado al evaluador."
        )

    # ── CEO OdooBot notification ──────────────────────────────────────────────

    def _eval_notify_ceo(self, applicant, quiz_score, claude_score, gpt_score, consensus, delta):
        try:
            ICP = self.env['ir.config_parameter'].sudo()
            ceo_email = ICP.get_param('wa_monitor.ceo_email', '')
            if not ceo_email:
                return
            ceo_user = self.env['res.users'].sudo().search(
                [('email', '=', ceo_email)], limit=1
            )
            if not ceo_user:
                return

            conf_pct = applicant.ueipab_confidence_pct
            consensus_label = {
                'high': '✅ Alta',
                'medium': '⚠️ Media',
                'low': '🔴 Baja — revisar transcript',
            }.get(consensus, consensus)

            msg = (
                f"📋 Evaluación completa: {applicant.partner_name}\n"
                f"Cargo: {applicant.job_id.name or '—'}\n\n"
                f"Quiz MCQ:       {quiz_score}/10\n"
                f"Score Claude:   {claude_score}/100\n"
                f"Score GPT:      {gpt_score}/100\n"
                f"Consenso IA:    {consensus_label} (Δ={delta})\n"
                f"Confianza total: {conf_pct:.1f}%\n\n"
                f"Ver candidato: /web#id={applicant.id}&model=hr.applicant"
            )

            # Send via OdooBot DM
            channel = self.env['discuss.channel'].sudo().search([
                ('channel_type', '=', 'chat'),
                ('channel_member_ids.partner_id', '=', ceo_user.partner_id.id),
                ('channel_member_ids.partner_id', '=',
                 self.env.ref('base.partner_root').id),
            ], limit=1)
            if channel:
                channel.sudo().message_post(
                    body=msg,
                    message_type='comment',
                    subtype_xmlid='mail.mt_comment',
                )
        except Exception:
            _logger.exception("CEO eval notification failed — non-critical")


# ── Helpers ──────────────────────────────────────────────────────────────────

def _plain(html):
    if not html:
        return ''
    text = re.sub(r'<[^>]+>', ' ', html)
    from html import unescape
    return ' '.join(unescape(text).split())


def session_json_armed(session):
    return bool(session.get('applicant_id'))


def _new_session(applicant_id, mode):
    return {
        'applicant_id':       applicant_id,
        'state':              'identity_prompt',
        'q_idx':              0,
        'answers':            [],
        'quiz_score':         None,
        'conv_turns':         [],
        'identity_confirmed': False,
        'identity_attempts':  0,
        'evaluation_mode':    mode,
    }


def _identity_prompt():
    return (
        "Hola, soy Glenda, la asistente de UEIPAB.\n\n"
        "Para comenzar la evaluación, ¿me confirmas tu nombre completo?"
    )


def _resolve_job_key(applicant):
    name = (applicant.job_id.name or '').lower()
    if any(k in name for k in ('contab', 'administ', 'auxiliar')):
        return 'contabilidad'
    return 'contabilidad'  # default bank until more banks exist


def _load_quiz_questions(job_key):
    """Load MCQ question bank by job key.

    Future upgrade: read from ueipab.recruitment.quiz ORM model
    (UI-editable per job position — Phase 2 roadmap).
    """
    return _QUIZ_BANKS.get(job_key, _QUIZ_BANKS['contabilidad'])


def _build_transcript(conv_turns):
    lines = []
    for turn in conv_turns:
        role = 'Candidato' if turn['role'] == 'user' else 'Evaluador'
        lines.append(f"{role}: {turn['content']}")
    return '\n\n'.join(lines)


def _parse_json_response(text):
    text = text.strip()
    # Strip markdown fences wherever they appear (Claude sometimes wraps despite instructions)
    text = re.sub(r'```(?:json)?\s*', '', text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Balanced-brace extraction — handles leading/trailing prose around the JSON object
    start = text.find('{')
    if start >= 0:
        depth = 0
        for i, c in enumerate(text[start:], start):
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i + 1])
                    except json.JSONDecodeError:
                        break
    _logger.warning("Could not parse AI scoring JSON: %s", text[:200])
    return {}


def _is_salary_question(text):
    t = text.lower()
    return any(k in t for k in _SALARY_KEYWORDS)


def _call_gpt_scoring(ICP, transcript):
    """Call GPT-4o-mini independently for dual-AI consensus scoring."""
    api_key = ICP.get_param('ai_agent.openai_api_key', '')
    if not api_key:
        _logger.warning("GPT scoring skipped — no openai_api_key configured")
        return 0

    messages = [
        {'role': 'system', 'content': _SCORING_PROMPT},
        {'role': 'user',   'content': transcript},
    ]
    resp = requests.post(
        'https://api.openai.com/v1/chat/completions',
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type':  'application/json',
        },
        json={
            'model':      ICP.get_param('ai_agent.openai_model', 'gpt-4o-mini'),
            'max_tokens': 512,
            'messages':   messages,
        },
        timeout=60,
    )
    resp.raise_for_status()
    content = resp.json()['choices'][0]['message']['content']
    data = _parse_json_response(content)
    return int(data.get('score', 0))
