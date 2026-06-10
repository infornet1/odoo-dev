import json
import logging
import time

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class HrApplicantEval(models.Model):
    _inherit = 'hr.applicant'

    # ── Evaluation pipeline state ────────────────────────────────────────────
    ueipab_eval_state = fields.Selection([
        ('pending',       'Pendiente'),
        ('confirmed',     'Confirmó Interés'),
        ('eval_invited',  'Evaluación Invitada'),
        ('ai_evaluating', 'Evaluación en Progreso'),
        ('ai_done',       'Evaluación Completa'),
        ('interview',     'Entrevista'),
    ], string='Estado de Evaluación', default='pending', tracking=True)

    # ── CV scoring (Layer 1 — Freescout + Claude) ────────────────────────────
    ueipab_cv_score = fields.Float('Score CV (%)', default=0.0,
        help='0-100 score from Claude AI analysis of the candidate CV.')
    ueipab_cv_tier = fields.Char('Tier CV', size=1,
        help='A (>=70) / B (45-69) / C (<45)')
    ueipab_cv_salary_risk = fields.Boolean('Riesgo Salarial',
        help='Claude flagged potential salary expectation mismatch.')
    ueipab_cv_extract_method = fields.Char('Método Extracción CV', size=32,
        help='How CV text was extracted: text-extracted / vision-image / email-only / vision-pdf')

    # ── Freescout traceability ───────────────────────────────────────────────
    ueipab_freescout_conv_id = fields.Integer(
        'Freescout Conv. ID', default=0, index=True,
        help='Primary key of the Freescout conversation. Used for dedup in fs_cv_loader.py.',
    )
    ueipab_freescout_url = fields.Char(
        'Freescout URL', compute='_compute_freescout_url', store=False,
    )

    @api.depends('ueipab_freescout_conv_id')
    def _compute_freescout_url(self):
        base = 'https://freescout.ueipab.edu.ve/conversation/'
        for rec in self:
            rec.ueipab_freescout_url = f"{base}{rec.ueipab_freescout_conv_id}" if rec.ueipab_freescout_conv_id else ''

    # ── Glenda AI skill evaluation (Layer 2) ─────────────────────────────────
    ueipab_evaluation_mode = fields.Selection([
        ('in_person', 'Presencial (OdooBot)'),
        ('remote',    'Remoto (Telegram)'),
    ], string='Modo de Evaluación')
    ueipab_telegram_eval_conv_id = fields.Many2one(
        'ai.agent.conversation', string='Conversación Glenda (Evaluación)',
        copy=False,
    )
    ueipab_skill_score = fields.Float('Score Glenda (%)', default=0.0,
        help='0-100 score from Glenda AI skill evaluation session.')
    ueipab_skill_score_gpt = fields.Float('Score GPT Validador (%)', default=0.0,
        help='Independent GPT-4o-mini score on same transcript (anti-gaming validator).')
    ueipab_eval_consensus = fields.Selection([
        ('high',   'Alto (delta ≤15)'),
        ('medium', 'Medio (delta 16-25)'),
        ('low',    'Bajo (delta >25 — posible gaming)'),
        ('failed', 'Falla IA (un scorer no respondió — re-puntuar)'),
    ], string='Consenso IA')
    ueipab_ai_eval_notes = fields.Text('Notas de Evaluación IA')
    ueipab_manager_summary = fields.Text('Resumen Ejecutivo RRHH')

    # ── Composite confidence score ───────────────────────────────────────────
    ueipab_confidence_pct = fields.Float(
        'Confianza (%)',
        compute='_compute_confidence_pct',
        store=True,
        digits=(5, 1),
    )

    @api.depends('ueipab_cv_score', 'ueipab_skill_score')
    def _compute_confidence_pct(self):
        for rec in self:
            rec.ueipab_confidence_pct = (
                rec.ueipab_cv_score    * 0.40 +
                rec.ueipab_skill_score * 0.60
            )

    # ── In-person appointment confirmation ───────────────────────────────────
    ueipab_eval_invite_token     = fields.Char('Token Confirmación Cita', copy=False, index=True)
    ueipab_eval_confirmed        = fields.Boolean('Asistencia Confirmada', default=False)
    ueipab_eval_appointment_date = fields.Date('Fecha Cita')
    ueipab_eval_appointment_time = fields.Char('Hora Cita')
    ueipab_eval_appointment_addr = fields.Char('Dirección Cita')

    # ── Phase 1 MCQ quiz tracking ────────────────────────────────────────────
    ueipab_quiz_score = fields.Integer(
        'Score Quiz MCQ (/ 10)', default=0,
        help='Number of correct answers in the Phase 1 multiple-choice quiz (0–10).',
    )
    ueipab_quiz_answers = fields.Text(
        'Respuestas Quiz (JSON)',
        help='JSON array: [{q, given, correct, ok}, …] — full answer log from MCQ session.',
    )
    ueipab_quiz_completed = fields.Boolean('Quiz Completado', default=False)

    # ── Actions ──────────────────────────────────────────────────────────────
    def action_send_confirmation_email(self):
        self.ensure_one()
        self.ueipab_eval_state = 'confirmed'

    def action_invite_in_person_eval(self):
        """Open the wizard to send an in-person evaluation invitation."""
        self.ensure_one()
        return {
            'type':      'ir.actions.act_window',
            'name':      'Enviar Invitación Presencial',
            'res_model': 'hr.applicant.eval.invite.wizard',
            'view_mode': 'form',
            'target':    'new',
            'context':   {'default_applicant_id': self.id},
        }

    def action_start_eval(self):
        """Arm the OdooBot evaluation session for the current user and open Discuss."""
        self.ensure_one()
        ICP = self.env['ir.config_parameter'].sudo()
        session_key = f'recruit.eval.session.{self.env.user.id}'
        session = {
            'applicant_id':       self.id,
            'state':              'identity_prompt',
            'q_idx':              0,
            'answers':            [],
            'quiz_score':         None,
            'conv_turns':         [],
            'identity_confirmed': False,
            'identity_attempts':  0,
            'evaluation_mode':    'in_person',
            'created_at':         time.time(),  # TTL guard in mail_bot_recruit_eval
        }
        ICP.set_param(session_key, json.dumps(session))
        self.ueipab_evaluation_mode = 'in_person'
        self.ueipab_eval_state = 'ai_evaluating'
        _logger.info(
            "Eval session armed: applicant=%s user=%s key=%s",
            self.id, self.env.user.login, session_key,
        )
        self._post_eval_welcome_to_odoobot()
        return {
            'type': 'ir.actions.act_url',
            'url':  '/web#action=mail.action_discuss',
            'target': 'self',
        }

    def _post_eval_welcome_to_odoobot(self):
        """Post the evaluation welcome message to the OdooBot DM channel proactively."""
        bot_partner = self.env.ref('base.partner_root')
        user = self.env.user
        channel = self.env['discuss.channel'].sudo().search([
            ('channel_type', '=', 'chat'),
            ('channel_member_ids.partner_id', '=', user.partner_id.id),
            ('channel_member_ids.partner_id', '=', bot_partner.id),
        ], limit=1)
        if not channel:
            return
        job_name = self.job_id.name or 'el cargo solicitado'
        msg = (
            f"👋 Hola, soy <b>Glenda</b>, la asistente de evaluación de UEIPAB.<br><br>"
            f"Estás participando en la <b>evaluación técnica</b> para el cargo de "
            f"<b>{job_name}</b>.<br><br>"
            f"La evaluación tiene dos partes:<br>"
            f"▸ <b>Parte 1:</b> 10 preguntas de selección múltiple — responde con A, B, C o D<br>"
            f"▸ <b>Parte 2:</b> Preguntas de desarrollo sobre situaciones prácticas del colegio<br><br>"
            f"Tiempo estimado: <b>15–20 minutos</b>. Tus respuestas son confidenciales.<br><br>"
            f"Para comenzar, escribe tu <b>nombre completo</b> tal como aparece en tu cédula.<br>"
            f"<i>(El evaluador puede escribir 'cancelar' para abortar la sesión.)</i>"
        )
        channel.sudo().message_post(
            body=msg,
            message_type='comment',
            subtype_xmlid='mail.mt_comment',
            author_id=bot_partner.id,
        )

    def action_send_telegram_eval_invite(self):
        self.ensure_one()
        self.ueipab_evaluation_mode = 'remote'
        self.ueipab_eval_state = 'eval_invited'
