import logging

from odoo import models, fields, api, _

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
        return res

    @api.onchange('payslip_run_id')
    def _onchange_payslip_run_id(self):
        """Re-populate lines when batch changes (standalone mode)."""
        if self.payslip_run_id:
            lines_data = self._prepare_lines(self.payslip_run_id)
            self.line_ids = [(5, 0, 0)] + lines_data
        else:
            self.line_ids = [(5, 0, 0)]

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

    def action_select_all(self):
        self.ensure_one()
        self.line_ids.write({'selected': True})
        return self._reopen()

    def action_deselect_all(self):
        self.ensure_one()
        self.line_ids.write({'selected': False})
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

        self.write({
            'state': 'done',
            'created_count': created,
        })
        _logger.info(
            "Created %d HR data collection requests from batch %s",
            created, self.payslip_run_id.name)
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
