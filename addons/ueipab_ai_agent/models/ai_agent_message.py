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
    kapso_message_id = fields.Char(
        'Kapso wamid', index=True,
        help='Meta Cloud API message ID (wamid.*) when the message flows '
             'through the Kapso provider. Used for inbound webhook dedup.')

    _sql_constraints = [
        # DB-level dedup for Kapso inbound: two concurrent webhook workers
        # racing the same wamid — the loser blocks on the winner's uncommitted
        # row and raises, caught by the caller's savepoint. Postgres unique
        # ignores NULLs, so Massiva (Integer id) / Telegram rows (wamid NULL)
        # are unaffected.
        ('kapso_message_id_uniq', 'unique(kapso_message_id)',
         'Mensaje Kapso duplicado: este wamid ya fue registrado.'),
    ]

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
