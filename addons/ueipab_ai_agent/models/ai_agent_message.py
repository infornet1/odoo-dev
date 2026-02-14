from odoo import models, fields


class AiAgentMessage(models.Model):
    _name = 'ai.agent.message'
    _description = 'AI Agent Message'
    _order = 'timestamp asc'

    conversation_id = fields.Many2one(
        'ai.agent.conversation', required=True, ondelete='cascade', string='Conversacion')
    direction = fields.Selection([
        ('outbound', 'Enviado'),
        ('inbound', 'Recibido'),
    ], required=True, string='Direccion')
    body = fields.Text('Mensaje')
    timestamp = fields.Datetime('Fecha', default=fields.Datetime.now)

    # WhatsApp tracking
    whatsapp_message_id = fields.Integer('MassivaMóvil ID')

    # AI metadata (for outbound messages)
    ai_input_tokens = fields.Integer('Tokens Entrada')
    ai_output_tokens = fields.Integer('Tokens Salida')

    # Attachment support
    attachment_url = fields.Char(
        'URL Adjunto',
        help='URL publica del archivo adjunto (MassivaMóvil)')
    attachment_type = fields.Selection([
        ('image', 'Imagen'),
        ('document', 'Documento'),
        ('audio', 'Audio'),
        ('video', 'Video'),
    ], string='Tipo Adjunto')
    attachment_id = fields.Many2one(
        'ir.attachment', string='Archivo Archivado',
        ondelete='set null',
        help='Copia local del adjunto descargado de MassivaMóvil')
