import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class HrDataCollectionRequest(models.Model):
    _name = 'hr.data.collection.request'
    _description = 'HR Data Collection Request'
    _inherit = ['mail.thread']
    _order = 'create_date desc'

    name = fields.Char(
        'Referencia', compute='_compute_name', store=True,
    )
    employee_id = fields.Many2one(
        'hr.employee', string='Empleado', required=True,
        ondelete='restrict', tracking=True,
    )
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('in_progress', 'En Progreso'),
        ('partial', 'Parcial'),
        ('completed', 'Completada'),
        ('cancelled', 'Cancelada'),
    ], default='draft', tracking=True, string='Estado')

    ai_conversation_id = fields.Many2one(
        'ai.agent.conversation', string='Conversacion AI',
        readonly=True, ondelete='set null',
    )
    ai_conversation_state = fields.Selection(
        related='ai_conversation_id.state', string='Estado Conversacion',
    )
    batch_id = fields.Many2one(
        'hr.payslip.run', string='Lote de Nomina',
        help='Lote de nomina de donde se extrajo el empleado',
    )
    channel = fields.Selection([
        ('whatsapp', 'WhatsApp'),
        ('email', 'Email'),
    ], default='whatsapp', string='Canal de Contacto')

    # --- Phase 1: Phone ---
    phone_confirmed = fields.Boolean('Telefono Confirmado', default=False)
    phone_confirmed_date = fields.Datetime('Fecha Confirmacion Telefono')
    phone_value = fields.Char('Telefono Confirmado (+58 format)')

    # --- Phase 2: Cedula ---
    cedula_confirmed = fields.Boolean('Cedula Confirmada', default=False)
    cedula_confirmed_date = fields.Datetime('Fecha Confirmacion Cedula')
    cedula_number = fields.Char('Numero Cedula (e.g. V15128008)')
    cedula_expiry_date = fields.Date('Vencimiento Cedula')
    cedula_photo_received = fields.Boolean('Foto Cedula Recibida', default=False)
    cedula_photo_date = fields.Datetime('Fecha Foto Cedula')

    # --- Phase 3: RIF ---
    rif_number_confirmed = fields.Boolean('RIF Confirmado', default=False)
    rif_confirmed_date = fields.Datetime('Fecha Confirmacion RIF')
    rif_number_value = fields.Char('Numero RIF (e.g. V-15128008-9)')
    rif_expiry_date = fields.Date('Vencimiento RIF')
    rif_photo_received = fields.Boolean('Foto RIF Recibida', default=False)
    rif_photo_date = fields.Datetime('Fecha Foto RIF')

    # --- Phase 4: Address ---
    address_confirmed = fields.Boolean('Direccion Confirmada', default=False)
    address_confirmed_date = fields.Datetime('Fecha Confirmacion Direccion')
    address_value = fields.Text('Direccion Confirmada')

    # --- Phase 5: Emergency ---
    emergency_confirmed = fields.Boolean('Emergencia Confirmada', default=False)
    emergency_confirmed_date = fields.Datetime('Fecha Confirmacion Emergencia')
    emergency_name = fields.Char('Nombre Contacto Emergencia')
    emergency_phone = fields.Char('Telefono Emergencia (+58 format)')

    # --- Progress ---
    phases_completed = fields.Integer(
        'Fases Completadas', compute='_compute_phases_completed', store=True,
    )
    progress = fields.Float(
        'Progreso (%)', compute='_compute_phases_completed', store=True,
    )

    # --- Tracking ---
    attempt_count = fields.Integer('Intentos de Contacto', default=0)
    last_attempt_date = fields.Datetime('Ultimo Intento')
    notes = fields.Text('Notas')

    @api.depends('employee_id.name')
    def _compute_name(self):
        for rec in self:
            emp_name = rec.employee_id.name or 'Sin empleado'
            rec.name = f"Recoleccion - {emp_name}"

    @api.depends(
        'phone_confirmed', 'cedula_confirmed', 'rif_number_confirmed',
        'address_confirmed', 'emergency_confirmed',
    )
    def _compute_phases_completed(self):
        for rec in self:
            count = sum([
                rec.phone_confirmed,
                rec.cedula_confirmed,
                rec.rif_number_confirmed,
                rec.address_confirmed,
                rec.emergency_confirmed,
            ])
            rec.phases_completed = count
            rec.progress = (count / 5.0) * 100

    def action_start(self):
        """Start the data collection conversation."""
        self.ensure_one()
        if self.state not in ('draft', 'partial'):
            return
        self.write({
            'state': 'in_progress',
            'attempt_count': self.attempt_count + 1,
            'last_attempt_date': fields.Datetime.now(),
        })

    def action_mark_partial(self):
        """Mark as partial when some but not all phases are done."""
        self.ensure_one()
        if self.phases_completed > 0 and self.phases_completed < 5:
            self.state = 'partial'

    def action_mark_completed(self):
        """Mark as completed when all 5 phases are done."""
        self.ensure_one()
        if self.phases_completed == 5:
            self.state = 'completed'

    def action_cancel(self):
        """Cancel the collection request."""
        self.ensure_one()
        self.state = 'cancelled'

    def action_reset_draft(self):
        """Reset a cancelled request back to draft."""
        self.ensure_one()
        if self.state == 'cancelled':
            self.state = 'draft'
