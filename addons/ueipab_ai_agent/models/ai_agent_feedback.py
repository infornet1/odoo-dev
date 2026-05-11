import re
import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

CATEGORIES = [
    ('flujo',        'Flujo de conversación'),
    ('respuesta',    'Calidad de respuesta'),
    ('idioma',       'Lenguaje / Tono'),
    ('asistencia',   'Asistencia de RRHH'),
    ('conocimiento', 'Conocimiento institucional'),
    ('tecnico',      'Problema técnico'),
    ('otro',         'Otro'),
]

STATES = [
    ('pending',     'Pendiente'),
    ('reviewed',    'Revisada'),
    ('implemented', 'Implementada'),
    ('rejected',    'Descartada'),
]


class AiAgentFeedback(models.Model):
    _name = 'ai.agent.feedback'
    _description = 'Glenda Calibration Feedback'
    _order = 'date desc'
    _rec_name = 'suggestion'

    employee_id    = fields.Many2one('hr.employee', string='Empleado', index=True, ondelete='set null')
    conversation_id = fields.Many2one('ai.agent.conversation', string='Conversación', ondelete='set null')
    wa_number      = fields.Char('WhatsApp')
    category       = fields.Selection(CATEGORIES, string='Categoría', default='otro', required=True)
    suggestion     = fields.Text('Sugerencia', required=True)
    state          = fields.Selection(STATES, string='Estado', default='pending', required=True)
    date           = fields.Datetime('Fecha', default=fields.Datetime.now, index=True)
    notes          = fields.Text('Notas internas')

    @api.model
    def _get_employee_by_phone(self, phone):
        """Resolve a WA phone number to an enrolled calibration employee."""
        if not phone:
            return None
        digits = re.sub(r'\D', '', phone)
        acks = self.env['hr.notice.acknowledgment'].sudo().search([
            ('notice_key', '=', 'glenda_calibracion_v1'),
            ('state', '=', 'acknowledged'),
        ])
        for ack in acks:
            if re.sub(r'\D', '', ack.wa_number or '') == digits:
                return ack.employee_id
        return None

    @api.model
    def log_from_conversation(self, conversation, category, suggestion):
        """Create a feedback record from a calibration conversation."""
        employee = self._get_employee_by_phone(conversation.phone)
        vals = {
            'wa_number':       conversation.phone,
            'conversation_id': conversation.id,
            'category':        category if category in dict(CATEGORIES) else 'otro',
            'suggestion':      suggestion,
            'employee_id':     employee.id if employee else False,
        }
        record = self.create(vals)
        _logger.info(
            "Calibration feedback logged — employee=%s category=%s id=%s",
            employee.name if employee else conversation.phone, category, record.id
        )
        return record
