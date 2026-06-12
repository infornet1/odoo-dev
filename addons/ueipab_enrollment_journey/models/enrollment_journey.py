# -*- coding: utf-8 -*-
import uuid

from odoo import api, fields, models

STEP_STATES = [
    ('pending', 'Pendiente'),
    ('in_progress', 'En proceso'),
    ('done_auto', 'Completado (auto)'),
    ('done_manual', 'Completado (manual)'),
    ('blocked', 'Bloqueado'),
]

DONE_STATES = ('done_auto', 'done_manual')

# (field prefix, customer-facing title, customer-facing hint while current)
STEP_DEFS = [
    ('step1', 'Cotización confirmada',
     'Tu cotización de inscripción ha sido registrada y confirmada por el equipo de ventas.'),
    ('step2', 'Acuerdo de Inscripción firmado',
     'Firma el Acuerdo de Inscripción (incluye los Términos y Condiciones del convenio) y entrégalo a Atención al Representante.'),
    ('step3', 'Registro Akdemia completo',
     'Completa los pasos de inscripción en la plataforma Akdemia. Nuestro equipo de soporte verificará tu registro.'),
    ('step4', 'Cuenta de correo @ueipab.edu.ve',
     'Activamos o actualizamos la cuenta institucional de cada estudiante en Google Workspace.'),
    ('step5', 'Google Classroom',
     'Inscribimos a cada estudiante en los Google Classroom de sus profesores según su grado y sección.'),
    ('step6', 'Contrato educativo final',
     'Al completar tu cronograma de pagos, firmarás el Contrato de Servicio Educativo que cierra el proceso.'),
]


class EnrollmentJourney(models.Model):
    _name = 'enrollment.journey'
    _description = 'Enrollment Journey 2026-2027'
    _order = 'create_date desc'
    _rec_name = 'display_name'

    partner_id = fields.Many2one('res.partner', string='Representante', required=True, index=True)
    order_id = fields.Many2one('sale.order', string='Cotización')
    access_token = fields.Char(string='Token', index=True, copy=False)
    academic_year = fields.Char(default='2026-2027')
    active = fields.Boolean(default=True)

    student_ids = fields.One2many('enrollment.journey.student', 'journey_id', string='Estudiantes')

    step1_state = fields.Selection(STEP_STATES, default='pending', string='1. Cotización')
    step2_state = fields.Selection(STEP_STATES, default='pending', string='2. Acuerdo firmado')
    step3_state = fields.Selection(STEP_STATES, default='pending', string='3. Akdemia')
    step4_state = fields.Selection(STEP_STATES, default='pending', string='4. Correo @ueipab')
    step5_state = fields.Selection(STEP_STATES, default='pending', string='5. Classroom')
    step6_state = fields.Selection(STEP_STATES, default='pending', string='6. Contrato final')

    step1_cleared_by = fields.Many2one('res.users', readonly=True)
    step2_cleared_by = fields.Many2one('res.users', readonly=True)
    step3_cleared_by = fields.Many2one('res.users', readonly=True)
    step4_cleared_by = fields.Many2one('res.users', readonly=True)
    step5_cleared_by = fields.Many2one('res.users', readonly=True)
    step6_cleared_by = fields.Many2one('res.users', readonly=True)

    step1_cleared_at = fields.Datetime(readonly=True)
    step2_cleared_at = fields.Datetime(readonly=True)
    step3_cleared_at = fields.Datetime(readonly=True)
    step4_cleared_at = fields.Datetime(readonly=True)
    step5_cleared_at = fields.Datetime(readonly=True)
    step6_cleared_at = fields.Datetime(readonly=True)

    current_step = fields.Integer(compute='_compute_progress', store=True)
    progress_pct = fields.Integer(compute='_compute_progress', store=True, string='Progreso %')
    journey_url = fields.Char(compute='_compute_journey_url', string='Página del Representante')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('access_token'):
                vals['access_token'] = str(uuid.uuid4())
        return super().create(vals_list)

    @api.depends('partner_id', 'academic_year')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = '%s — %s' % (rec.partner_id.name or '?', rec.academic_year)

    @api.depends('step1_state', 'step2_state', 'step3_state',
                 'step4_state', 'step5_state', 'step6_state')
    def _compute_progress(self):
        for rec in self:
            done = 0
            current = 0
            for idx, (prefix, _t, _h) in enumerate(STEP_DEFS, start=1):
                if rec[prefix + '_state'] in DONE_STATES:
                    done += 1
                elif not current:
                    current = idx
            rec.progress_pct = int(done * 100 / len(STEP_DEFS))
            rec.current_step = current or len(STEP_DEFS)

    def _compute_journey_url(self):
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for rec in self:
            rec.journey_url = '%s/enrollment-journey/%s' % (base, rec.access_token)

    # -- staff one-click clearance ------------------------------------
    def _set_step(self, idx, state):
        self.ensure_one()
        prefix = 'step%d' % idx
        vals = {prefix + '_state': state}
        if state in DONE_STATES:
            vals[prefix + '_cleared_by'] = self.env.uid
            vals[prefix + '_cleared_at'] = fields.Datetime.now()
        self.write(vals)

    def action_clear_step(self):
        self._set_step(self.env.context.get('step', 0), 'done_manual')

    def action_reopen_step(self):
        self._set_step(self.env.context.get('step', 0), 'in_progress')

    def action_open_journey_page(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_url', 'url': self.journey_url, 'target': 'new'}

    # -- soft checks (skeleton: step 1 only; steps 4/6 in Phase 2) ----
    def action_run_soft_checks(self):
        for rec in self:
            if rec.order_id and rec.order_id.state == 'sale' \
                    and rec.step1_state not in DONE_STATES:
                rec.step1_state = 'done_auto'
                rec.step1_cleared_at = fields.Datetime.now()


class EnrollmentJourneyStudent(models.Model):
    _name = 'enrollment.journey.student'
    _description = 'Enrollment Journey Student'

    journey_id = fields.Many2one('enrollment.journey', required=True, ondelete='cascade')
    name = fields.Char(string='Estudiante', required=True)
    grade = fields.Char(string='Grado/Año')
    institutional_email = fields.Char(string='Correo @ueipab')
    insurance_policy = fields.Char(string='Nº Póliza Seguro')
