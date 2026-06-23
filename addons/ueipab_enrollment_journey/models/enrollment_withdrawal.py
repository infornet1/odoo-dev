# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models
from odoo.exceptions import UserError

from .enrollment_journey import STEP_STATES, DONE_STATES

_logger = logging.getLogger(__name__)

# 5-step offboarding (egreso) checklist. Driven by this constant the same way
# enrollment.journey is driven by STEP_DEFS — reorder = no DB migration.
WITHDRAWAL_STEP_DEFS = [
    ('step1', 'Solvencia administrativa 2025-2026',
     'Carta de no deuda — mensualidades de julio y agosto del año escolar 2025-2026 canceladas.'),
    ('step2', 'Documentación de egreso preparada',
     'Reunir y preparar toda la documentación de egreso del/los estudiante(s).'),
    ('step3', 'Desincorporación de Akdemia',
     'Desincorporar al/los estudiante(s) de la plataforma Akdemia (edge.akdemia.com).'),
    ('step4', 'Liberación de SIGE',
     'Liberar al/los estudiante(s) del SIGE (Ministerio del Poder Popular para la Educación).'),
    ('step5', 'Suspensión de cuentas Gmail institucionales',
     'Suspender las cuentas @ueipab.edu.ve del/los estudiante(s).'),
]

# Steps 3-5 (Akdemia / SIGE / Gmail) require step 1 (solvencia) + step 2 (exit
# docs) to be done first — the legal/administrative gate.
WITHDRAWAL_GATE_STEPS = (1, 2)
N_STEPS = len(WITHDRAWAL_STEP_DEFS)


class EnrollmentWithdrawal(models.Model):
    _name = 'enrollment.withdrawal'
    _description = 'Enrollment Withdrawal / Egreso 2025-2026'
    _inherit = ['mail.thread']
    _order = 'create_date desc'
    _rec_name = 'display_name'

    journey_id = fields.Many2one(
        'enrollment.journey', string='Inscripción de origen',
        ondelete='set null', index=True)
    partner_id = fields.Many2one(
        'res.partner', string='Representante',
        related='journey_id.partner_id', store=True, index=True, readonly=True)
    student_ids = fields.One2many(
        related='journey_id.student_ids', string='Estudiantes', readonly=True)
    exit_reason = fields.Text(
        string='Motivo de retiro', related='journey_id.decline_reason', readonly=True)

    state = fields.Selection([
        ('in_progress', 'En proceso'),
        ('completed',   'Completado'),
    ], string='Estado', compute='_compute_state', store=True, index=True)
    progress_pct = fields.Integer(
        string='Progreso %', compute='_compute_state', store=True)

    # 5-step offboarding checklist
    step1_state = fields.Selection(STEP_STATES, default='pending', string='1. Solvencia')
    step2_state = fields.Selection(STEP_STATES, default='pending', string='2. Documentación')
    step3_state = fields.Selection(STEP_STATES, default='pending', string='3. Akdemia')
    step4_state = fields.Selection(STEP_STATES, default='pending', string='4. SIGE')
    step5_state = fields.Selection(STEP_STATES, default='pending', string='5. Gmail')

    step1_cleared_by = fields.Many2one('res.users', readonly=True)
    step2_cleared_by = fields.Many2one('res.users', readonly=True)
    step3_cleared_by = fields.Many2one('res.users', readonly=True)
    step4_cleared_by = fields.Many2one('res.users', readonly=True)
    step5_cleared_by = fields.Many2one('res.users', readonly=True)

    step1_cleared_at = fields.Datetime(readonly=True)
    step2_cleared_at = fields.Datetime(readonly=True)
    step3_cleared_at = fields.Datetime(readonly=True)
    step4_cleared_at = fields.Datetime(readonly=True)
    step5_cleared_at = fields.Datetime(readonly=True)

    # Regulatory audit references (decision D3)
    solvencia_ref = fields.Char(string='Ref. carta de solvencia')   # step 1
    sige_ref = fields.Char(string='Ref./constancia SIGE')           # step 4

    @api.depends('partner_id')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = 'Egreso — %s' % (rec.partner_id.name or '?')

    @api.depends('step1_state', 'step2_state', 'step3_state',
                 'step4_state', 'step5_state')
    def _compute_state(self):
        for rec in self:
            done = sum(1 for i in range(1, N_STEPS + 1)
                       if rec['step%d_state' % i] in DONE_STATES)
            rec.progress_pct = int(done * 100 / N_STEPS)
            rec.state = 'completed' if done == N_STEPS else 'in_progress'

    # -- staff one-click clearance + hard gate ----------------------------

    def _set_step(self, idx, state):
        """Mark step `idx` to `state`. Steps 3-5 are gated behind 1+2."""
        self.ensure_one()
        if not 1 <= idx <= N_STEPS:
            raise UserError('Paso de egreso inválido: %s' % idx)
        if state in DONE_STATES and idx >= 3:
            incomplete = [
                i for i in WITHDRAWAL_GATE_STEPS
                if self['step%d_state' % i] not in DONE_STATES
            ]
            if incomplete:
                raise UserError(
                    'Antes de desincorporar de plataformas/registros debe completar '
                    'la solvencia (paso 1) y la documentación de egreso (paso 2). '
                    'Pendiente(s): %s.' % ', '.join('#%d' % i for i in incomplete))
        prefix = 'step%d' % idx
        vals = {prefix + '_state': state}
        if state in DONE_STATES:
            vals[prefix + '_cleared_by'] = self.env.uid
            vals[prefix + '_cleared_at'] = fields.Datetime.now()
        else:
            vals[prefix + '_cleared_by'] = False
            vals[prefix + '_cleared_at'] = False
        self.write(vals)
        label = WITHDRAWAL_STEP_DEFS[idx - 1][1]
        self.message_post(
            body='Egreso · paso #%d (%s) → %s por %s.' % (
                idx, label, dict(STEP_STATES).get(state, state), self.env.user.name),
            message_type='comment', subtype_xmlid='mail.mt_note')

    def action_clear_step(self):
        self._set_step(self.env.context.get('step', 0), 'done_manual')

    def action_reopen_step(self):
        self._set_step(self.env.context.get('step', 0), 'pending')
