import logging

from odoo import models, fields, api, _
from ..skills import normalize_ve_phone

_logger = logging.getLogger(__name__)


class CreateCollectionWizard(models.TransientModel):
    _name = 'hr.data.collection.create.wizard'
    _description = 'Crear Solicitudes de Recoleccion de Datos'

    payslip_run_id = fields.Many2one(
        'hr.payslip.run', string='Lote de Nomina', required=True,
    )
    state = fields.Selection([
        ('select', 'Seleccion'),
        ('done', 'Completado'),
    ], default='select')
    line_ids = fields.One2many(
        'hr.data.collection.create.line', 'wizard_id', string='Empleados',
    )
    total_count = fields.Integer(
        'Total Empleados', compute='_compute_counts',
    )
    selected_count = fields.Integer(
        'Seleccionados', compute='_compute_counts',
    )
    excluded_count = fields.Integer(
        'Excluidos', compute='_compute_counts',
    )
    created_count = fields.Integer('Solicitudes Creadas', default=0)

    # ── Tab 2: Payslip Ack Reminders ──────────────────────────────────
    ack_line_ids = fields.One2many(
        'hr.data.collection.create.ack.line', 'wizard_id', string='Conformidades Pendientes',
    )
    ack_total_count = fields.Integer('Total', compute='_compute_ack_counts')
    ack_selected_count = fields.Integer('Seleccionados', compute='_compute_ack_counts')
    ack_created_count = fields.Integer('Recordatorios Creados', default=0)
    done_mode = fields.Selection([
        ('hr', 'Solicitudes RRHH'),
        ('ack', 'Recordatorios de Conformidad'),
    ], default='hr')

    @api.depends('ack_line_ids', 'ack_line_ids.selected')
    def _compute_ack_counts(self):
        for wiz in self:
            lines = wiz.ack_line_ids
            wiz.ack_total_count = len(lines)
            wiz.ack_selected_count = len(lines.filtered('selected'))

    @api.depends('line_ids', 'line_ids.selected')
    def _compute_counts(self):
        for wiz in self:
            lines = wiz.line_ids
            wiz.total_count = len(lines)
            wiz.selected_count = len(lines.filtered('selected'))
            wiz.excluded_count = wiz.total_count - wiz.selected_count

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        run_id = self.env.context.get('default_payslip_run_id')
        if run_id:
            res['payslip_run_id'] = run_id
            run = self.env['hr.payslip.run'].browse(run_id)
            res['line_ids'] = self._prepare_lines(run)
            res['ack_line_ids'] = self._prepare_ack_lines(run)
        return res

    @api.onchange('payslip_run_id')
    def _onchange_payslip_run_id(self):
        """Re-populate lines when batch changes (standalone mode)."""
        if self.payslip_run_id:
            self.line_ids = [(5, 0, 0)] + self._prepare_lines(self.payslip_run_id)
            self.ack_line_ids = [(5, 0, 0)] + self._prepare_ack_lines(self.payslip_run_id)
        else:
            self.line_ids = [(5, 0, 0)]
            self.ack_line_ids = [(5, 0, 0)]

    def _prepare_lines(self, run):
        """Build One2many create commands from payslip batch employees."""
        # Deduplicate employees from payslips
        seen = set()
        lines = []
        Request = self.env['hr.data.collection.request']
        for slip in run.slip_ids:
            emp = slip.employee_id
            if emp.id in seen:
                continue
            seen.add(emp.id)

            # Check existing request
            existing = Request.search([
                ('employee_id', '=', emp.id),
                ('state', 'not in', ('cancelled',)),
            ], limit=1)

            has_existing = bool(existing)
            existing_state = existing.state if existing else False

            # Status indicators
            has_phone = bool(emp.mobile_phone or emp.work_phone)
            has_cedula = bool(emp.identification_id)
            has_address = bool(emp.private_street)

            lines.append((0, 0, {
                'employee_id': emp.id,
                'employee_name': emp.name,
                'selected': not has_existing,
                'has_phone': has_phone,
                'has_cedula': has_cedula,
                'has_address': has_address,
                'has_existing_request': has_existing,
                'existing_request_state': existing_state,
            }))
        return lines

    def _prepare_ack_lines(self, run):
        """Build ack reminder lines from payslips with is_acknowledged=False."""
        Conversation = self.env['ai.agent.conversation']
        skill = self.env['ai.agent.skill'].search(
            [('code', '=', 'payslip_ack_reminder')], limit=1)

        lines = []
        seen_employees = set()
        for slip in run.slip_ids.filtered(lambda s: s.state == 'done' and not s.is_acknowledged):
            emp = slip.employee_id
            if slip.id in seen_employees:
                continue
            seen_employees.add(slip.id)

            # Check for existing active reminder conversation for this payslip
            existing = False
            existing_state = False
            if skill:
                conv = Conversation.search([
                    ('skill_id', '=', skill.id),
                    ('source_model', '=', 'hr.payslip'),
                    ('source_id', '=', slip.id),
                    ('state', 'in', ('draft', 'active', 'waiting')),
                ], limit=1)
                if conv:
                    existing = True
                    existing_state = conv.state

            has_phone = bool(emp.mobile_phone or emp.work_phone)

            lines.append((0, 0, {
                'employee_id': emp.id,
                'payslip_id': slip.id,
                'employee_name': emp.name,
                'payslip_number': slip.number or slip.name or '',
                'selected': has_phone and not existing,
                'has_phone': has_phone,
                'has_existing_reminder': existing,
                'existing_reminder_state': existing_state,
            }))
        return lines

    def action_select_all(self):
        self.ensure_one()
        self.line_ids.write({'selected': True})
        return self._reopen()

    def action_deselect_all(self):
        self.ensure_one()
        self.line_ids.write({'selected': False})
        return self._reopen()

    def action_select_all_ack(self):
        self.ensure_one()
        self.ack_line_ids.filtered(lambda l: l.has_phone and not l.has_existing_reminder).write(
            {'selected': True})
        return self._reopen()

    def action_deselect_all_ack(self):
        self.ensure_one()
        self.ack_line_ids.write({'selected': False})
        return self._reopen()

    def action_create_requests(self):
        """Create hr.data.collection.request for each selected employee."""
        self.ensure_one()
        Request = self.env['hr.data.collection.request']
        selected = self.line_ids.filtered('selected')
        created = 0
        for line in selected:
            Request.create({
                'employee_id': line.employee_id.id,
                'batch_id': self.payslip_run_id.id,
                'state': 'draft',
            })
            created += 1

        self.write({'state': 'done', 'created_count': created, 'done_mode': 'hr'})
        _logger.info("Created %d HR data collection requests from batch %s",
                     created, self.payslip_run_id.name)
        return self._reopen()

    def action_create_ack_reminders(self):
        """Create draft payslip_ack_reminder conversations for selected payslips."""
        self.ensure_one()
        skill = self.env['ai.agent.skill'].search(
            [('code', '=', 'payslip_ack_reminder')], limit=1)
        if not skill:
            raise Exception("Skill 'payslip_ack_reminder' not found. Please upgrade the module.")

        Conversation = self.env['ai.agent.conversation']
        selected = self.ack_line_ids.filtered('selected')
        created = 0
        skipped = 0

        for line in selected:
            emp = line.employee_id
            raw_phone = emp.mobile_phone or emp.work_phone
            if not raw_phone:
                _logger.warning("Ack reminder: skipping %s — no phone", emp.name)
                skipped += 1
                continue

            phone = normalize_ve_phone(raw_phone)
            if not phone:
                _logger.warning("Ack reminder: skipping %s — cannot normalize phone %s",
                                emp.name, raw_phone)
                skipped += 1
                continue

            partner = emp.user_partner_id or emp.address_home_id
            Conversation.create({
                'skill_id': skill.id,
                'partner_id': partner.id if partner else False,
                'phone': phone,
                'source_model': 'hr.payslip',
                'source_id': line.payslip_id.id,
                'state': 'draft',
            })
            created += 1

        self.write({'state': 'done', 'ack_created_count': created, 'done_mode': 'ack'})
        _logger.info("Created %d payslip ack reminder conversations from batch %s (%d skipped)",
                     created, self.payslip_run_id.name, skipped)
        return self._reopen()

    def action_view_requests(self):
        """Open tree view filtered by batch_id."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Solicitudes de Recoleccion'),
            'res_model': 'hr.data.collection.request',
            'view_mode': 'tree,form',
            'domain': [('batch_id', '=', self.payslip_run_id.id)],
            'target': 'current',
        }

    def action_view_ack_conversations(self):
        """Open ack reminder conversations for payslips in this batch."""
        self.ensure_one()
        payslip_ids = self.payslip_run_id.slip_ids.ids
        skill = self.env['ai.agent.skill'].search(
            [('code', '=', 'payslip_ack_reminder')], limit=1)
        return {
            'type': 'ir.actions.act_window',
            'name': _('Recordatorios de Conformidad'),
            'res_model': 'ai.agent.conversation',
            'view_mode': 'tree,form',
            'domain': [
                ('skill_id', '=', skill.id if skill else False),
                ('source_model', '=', 'hr.payslip'),
                ('source_id', 'in', payslip_ids),
            ],
            'target': 'current',
        }

    def _reopen(self):
        """Return action to reopen this wizard (keep form open after actions)."""
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }


class CreateCollectionLine(models.TransientModel):
    _name = 'hr.data.collection.create.line'
    _description = 'Linea de Wizard de Recoleccion'

    wizard_id = fields.Many2one(
        'hr.data.collection.create.wizard', required=True, ondelete='cascade',
    )
    employee_id = fields.Many2one('hr.employee', string='Empleado', required=True)
    employee_name = fields.Char('Nombre', related='employee_id.name', readonly=True)
    selected = fields.Boolean('Seleccionar', default=True)

    # Status indicators
    has_phone = fields.Boolean('Tiene Telefono', readonly=True)
    has_cedula = fields.Boolean('Tiene Cedula', readonly=True)
    has_address = fields.Boolean('Tiene Direccion', readonly=True)
    has_existing_request = fields.Boolean('Solicitud Existente', readonly=True)
    existing_request_state = fields.Selection([
        ('draft', 'Borrador'),
        ('in_progress', 'En Progreso'),
        ('partial', 'Parcial'),
        ('completed', 'Completada'),
        ('cancelled', 'Cancelada'),
    ], string='Estado Solicitud', readonly=True)


class CreateCollectionAckLine(models.TransientModel):
    _name = 'hr.data.collection.create.ack.line'
    _description = 'Linea de Recordatorio de Conformidad'

    wizard_id = fields.Many2one(
        'hr.data.collection.create.wizard', ondelete='cascade',
    )
    employee_id = fields.Many2one('hr.employee', string='Empleado', required=True)
    payslip_id = fields.Many2one('hr.payslip', string='Recibo', required=True)
    employee_name = fields.Char('Empleado', related='employee_id.name', readonly=True)
    payslip_number = fields.Char('Nro. Recibo', readonly=True)
    selected = fields.Boolean('Seleccionar', default=True)
    has_phone = fields.Boolean('Tiene Telefono', readonly=True)
    has_existing_reminder = fields.Boolean('Recordatorio Activo', readonly=True)
    existing_reminder_state = fields.Selection([
        ('draft', 'Borrador'),
        ('active', 'Activa'),
        ('waiting', 'Esperando'),
    ], string='Estado', readonly=True)
