from odoo import models, fields, api


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    data_collection_request_ids = fields.One2many(
        'hr.data.collection.request', 'employee_id',
        string='Solicitudes de Recoleccion',
    )
    data_collection_state = fields.Selection([
        ('none', 'Sin solicitud'),
        ('draft', 'Borrador'),
        ('in_progress', 'En Progreso'),
        ('partial', 'Parcial'),
        ('completed', 'Completada'),
        ('cancelled', 'Cancelada'),
    ], compute='_compute_data_collection_state', string='Estado Recoleccion',
        store=True,
    )

    @api.depends('data_collection_request_ids', 'data_collection_request_ids.state')
    def _compute_data_collection_state(self):
        for emp in self:
            requests = emp.data_collection_request_ids.sorted('create_date', reverse=True)
            if requests:
                emp.data_collection_state = requests[0].state
            else:
                emp.data_collection_state = 'none'
