from odoo import models, fields, api


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
    ], string='Consenso IA')
    ueipab_ai_eval_notes = fields.Text('Notas de Evaluación IA')

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

    # ── Actions ──────────────────────────────────────────────────────────────
    def action_send_confirmation_email(self):
        """Send 3-question confirmation email to interested candidate."""
        self.ensure_one()
        self.ueipab_eval_state = 'confirmed'
        # TODO Phase 1: email template with 3 questions + OdooBot invite instructions

    def action_invite_in_person_eval(self):
        """Schedule in-person OdooBot evaluation session."""
        self.ensure_one()
        self.ueipab_evaluation_mode = 'in_person'
        self.ueipab_eval_state = 'eval_invited'
        # TODO Phase 1: create portal user, send credentials via email

    def action_send_telegram_eval_invite(self):
        """Send Glenda Telegram deep-link for remote skill evaluation."""
        self.ensure_one()
        self.ueipab_evaluation_mode = 'remote'
        self.ueipab_eval_state = 'eval_invited'
        # TODO Phase 1: generate t.me/GlendaUeipabBot?start=RECRUIT_{self.id}
