# -*- coding: utf-8 -*-
import uuid

from odoo import api, fields, models
from odoo.exceptions import UserError

STEP_STATES = [
    ('pending', 'Pendiente'),
    ('in_progress', 'En proceso'),
    ('done_auto', 'Completado (auto)'),
    ('done_manual', 'Completado (manual)'),
    ('blocked', 'Bloqueado'),
]

DONE_STATES = ('done_auto', 'done_manual')

# Steps that form Block 1 — must all be done before Block 2/3 can be cleared
BLOCK1_STEPS = (1, 2, 3)

# (field prefix, customer-facing title, customer-facing hint while current)
STEP_DEFS = [
    # Block 1 — Inscripción Formal (support, single enrollment visit)
    ('step1', 'Cotización confirmada',
     'Tu cotización de inscripción ha sido registrada y confirmada por el equipo de ventas.'),
    ('step2', 'Acuerdo de Inscripción firmado',
     'Firma el Acuerdo de Inscripción (incluye los Términos y Condiciones del convenio) '
     'y entrégalo a Atención al Representante.'),
    ('step3', 'Contrato Educativo firmado',
     'Firma el Contrato de Servicio Educativo en nuestras instalaciones. '
     'El documento quedará en resguardo hasta completar el plan de pagos establecido.'),
    # Block 2 — Activación de Plataformas (IT + academic, 1-3 weeks after visit)
    ('step4', 'Registro Akdemia completo',
     'Completa los pasos de inscripción en la plataforma Akdemia. '
     'Nuestro equipo de soporte verificará tu registro.'),
    ('step5', 'Cuenta Dawere habilitada',
     'El equipo de IT habilitará la cuenta de cada estudiante en Dawere. '
     'Recibirás las credenciales de acceso por correo.'),
    ('step6', 'Cuenta @ueipab.edu.ve actualizada',
     'Activamos o actualizamos la cuenta institucional de Google Workspace de cada estudiante.'),
    ('step7', 'Google Classroom',
     'Inscribimos a cada estudiante en los Google Classroom de sus profesores '
     'según su grado y sección.'),
    # Block 3 — Cierre Administrativo (support/admin, within first week)
    ('step8', 'Guía de Inglés entregada',
     'Confirma haber recibido la guía del programa de inglés para el año escolar 2026-2027.'),
    ('step9', 'Expediente físico actualizado',
     'Nuestro equipo verificará que el expediente físico de cada estudiante esté '
     'completo y actualizado con toda la documentación requerida.'),
]

# Block definitions used by the customer page renderer
BLOCK_DEFS = [
    ('🏛️ Inscripción Formal', list(range(1, 4))),
    ('💻 Activación de Plataformas', list(range(4, 8))),
    ('📁 Cierre Administrativo', list(range(8, 10))),
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

    contract_number = fields.Char(string='Nro. de Control', copy=False, readonly=True)
    contract_date = fields.Date(string='Fecha del Contrato', copy=False)
    contract_retained = fields.Boolean(
        string='Contrato en custodia', default=False,
        help='El contrato fue firmado pero permanece retenido hasta completar el cronograma de pagos.')
    contract_released_date = fields.Date(
        string='Fecha de entrega del contrato', readonly=True, copy=False)

    # Block 1 — Inscripción Formal
    step1_state = fields.Selection(STEP_STATES, default='pending', string='1. Cotización')
    step2_state = fields.Selection(STEP_STATES, default='pending', string='2. Acuerdo firmado')
    step3_state = fields.Selection(STEP_STATES, default='pending', string='3. Contrato firmado')
    # Block 2 — Activación de Plataformas
    step4_state = fields.Selection(STEP_STATES, default='pending', string='4. Akdemia')
    step5_state = fields.Selection(STEP_STATES, default='pending', string='5. Dawere')
    step6_state = fields.Selection(STEP_STATES, default='pending', string='6. Correo @ueipab')
    step7_state = fields.Selection(STEP_STATES, default='pending', string='7. Classroom')
    # Block 3 — Cierre Administrativo
    step8_state = fields.Selection(STEP_STATES, default='pending', string='8. Guía Inglés')
    step9_state = fields.Selection(STEP_STATES, default='pending', string='9. Expediente')

    step1_cleared_by = fields.Many2one('res.users', readonly=True)
    step2_cleared_by = fields.Many2one('res.users', readonly=True)
    step3_cleared_by = fields.Many2one('res.users', readonly=True)
    step4_cleared_by = fields.Many2one('res.users', readonly=True)
    step5_cleared_by = fields.Many2one('res.users', readonly=True)
    step6_cleared_by = fields.Many2one('res.users', readonly=True)
    step7_cleared_by = fields.Many2one('res.users', readonly=True)
    step8_cleared_by = fields.Many2one('res.users', readonly=True)
    step9_cleared_by = fields.Many2one('res.users', readonly=True)

    step1_cleared_at = fields.Datetime(readonly=True)
    step2_cleared_at = fields.Datetime(readonly=True)
    step3_cleared_at = fields.Datetime(readonly=True)
    step4_cleared_at = fields.Datetime(readonly=True)
    step5_cleared_at = fields.Datetime(readonly=True)
    step6_cleared_at = fields.Datetime(readonly=True)
    step7_cleared_at = fields.Datetime(readonly=True)
    step8_cleared_at = fields.Datetime(readonly=True)
    step9_cleared_at = fields.Datetime(readonly=True)

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
                 'step4_state', 'step5_state', 'step6_state',
                 'step7_state', 'step8_state', 'step9_state')
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
        # Hard gate: Block 2 and 3 steps require Block 1 fully complete
        if state in DONE_STATES and idx >= 4:
            incomplete = [
                i for i in BLOCK1_STEPS
                if self['step%d_state' % i] not in DONE_STATES
            ]
            if incomplete:
                raise UserError(
                    'Completa primero el Bloque 1 — Inscripción Formal. '
                    'Los pasos %s aún no están completados.'
                    % ', '.join('#%d' % i for i in incomplete)
                )
        prefix = 'step%d' % idx
        vals = {prefix + '_state': state}
        if state in DONE_STATES:
            vals[prefix + '_cleared_by'] = self.env.uid
            vals[prefix + '_cleared_at'] = fields.Datetime.now()
            if idx == 3:
                vals['contract_retained'] = True
        elif idx == 3:
            vals['contract_retained'] = False
            vals['contract_released_date'] = False
        self.write(vals)

    def action_clear_step(self):
        self._set_step(self.env.context.get('step', 0), 'done_manual')

    def action_reopen_step(self):
        self._set_step(self.env.context.get('step', 0), 'in_progress')

    def action_release_contract(self):
        self.ensure_one()
        self.write({
            'contract_retained': False,
            'contract_released_date': fields.Date.context_today(self),
        })

    def action_open_journey_page(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_url', 'url': self.journey_url, 'target': 'new'}

    def action_print_contract(self):
        for rec in self:
            if not rec.contract_number:
                rec.contract_number = self.env['ir.sequence'].next_by_code('enrollment.contract')
            if not rec.contract_date:
                rec.contract_date = fields.Date.context_today(rec)
        return self.env.ref(
            'ueipab_enrollment_journey.action_report_enrollment_contract').report_action(self)

    # -- soft checks --------------------------------------------------
    def action_run_soft_checks(self):
        for rec in self:
            # Step 1: order confirmed
            if rec.order_id and rec.order_id.state == 'sale' \
                    and rec.step1_state not in DONE_STATES:
                rec.step1_state = 'done_auto'
                rec.step1_cleared_at = fields.Datetime.now()

            # Step 3 contract release: all posted invoices fully paid
            if rec.step3_state in DONE_STATES and rec.contract_retained and rec.order_id:
                invoices = rec.order_id.invoice_ids.filtered(
                    lambda inv: inv.state == 'posted'
                    and inv.move_type in ('out_invoice', 'out_refund')
                )
                if invoices and all(inv.amount_residual == 0 for inv in invoices):
                    rec.contract_retained = False
                    rec.contract_released_date = fields.Date.context_today(rec)


class EnrollmentJourneyStudent(models.Model):
    _name = 'enrollment.journey.student'
    _description = 'Enrollment Journey Student'

    journey_id = fields.Many2one('enrollment.journey', required=True, ondelete='cascade')
    name = fields.Char(string='Estudiante', required=True)
    cedula = fields.Char(string='Cédula/Cédula Escolar')
    grade = fields.Char(string='Grado/Año')
    institutional_email = fields.Char(string='Correo @ueipab')
    insurance_policy = fields.Char(string='Nº Póliza Seguro')
