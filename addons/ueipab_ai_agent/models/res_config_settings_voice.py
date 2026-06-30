from odoo import models, fields


class ResConfigSettingsVoice(models.TransientModel):
    _inherit = 'res.config.settings'

    # All persisted to ir.config_parameter (config_parameter= attr).
    voice_call_enabled = fields.Boolean(
        'Activar llamadas de voz',
        config_parameter='voice_call.enabled',
        help='Permite que Glenda realice llamadas de voz salientes.')
    voice_call_caller_id = fields.Char(
        'Caller ID (número origen)',
        config_parameter='voice_call.caller_id',
        help='Número Twilio o caller ID verificado que se mostrará a quien recibe.')
    voice_call_voice = fields.Char(
        'Voz (OpenAI Realtime)',
        config_parameter='voice_call.voice',
        default='sage',
        help='alloy, ash, ballad, coral, echo, sage, shimmer, verse, marin, cedar.')
    voice_call_realtime_model = fields.Char(
        'Modelo Realtime',
        config_parameter='voice_call.realtime_model',
        default='gpt-realtime-2')
    voice_call_gateway_url = fields.Char(
        'URL del Gateway de Voz',
        config_parameter='voice_call.gateway_url',
        help='Base URL donde Odoo contacta el gateway para colocar llamadas '
             '(p.ej. http://172.17.0.1:8090 desde el contenedor, o el host público).')
    voice_call_callback_base = fields.Char(
        'URL pública de Odoo (callbacks)',
        config_parameter='voice_call.callback_base',
        help='Base URL que el gateway usa para devolver estado/transcripción. '
             'Si se deja vacío se usa web.base.url.')
    voice_call_callback_token = fields.Char(
        'Token de callback',
        config_parameter='voice_call.callback_token',
        help='Secreto compartido validado en /ai-agent/voice/callback.')
