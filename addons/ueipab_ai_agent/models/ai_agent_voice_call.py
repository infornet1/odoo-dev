import json
import logging
import re

import requests

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AiAgentVoiceCall(models.Model):
    _name = 'ai.agent.voice.call'
    _description = 'Glenda Voice Call (Twilio ↔ OpenAI Realtime)'
    _order = 'create_date desc, id desc'
    _rec_name = 'display_name'

    display_name = fields.Char('Llamada', compute='_compute_display_name', store=True)
    partner_id   = fields.Many2one('res.partner', string='Contacto', ondelete='set null')
    phone        = fields.Char('Teléfono destino', required=True)
    direction    = fields.Selection([
        ('outbound', 'Saliente'),
        ('inbound',  'Entrante'),
    ], string='Dirección', default='outbound', required=True)
    call_reason  = fields.Text(
        'Motivo de la llamada',
        help='Texto que Glenda usa para presentar el motivo al inicio de la llamada.')

    status = fields.Selection([
        ('draft',       'Borrador'),
        ('queued',      'En cola'),
        ('initiated',   'Iniciada'),
        ('ringing',     'Timbrando'),
        ('in_progress', 'En curso'),
        ('completed',   'Completada'),
        ('busy',        'Ocupado'),
        ('no_answer',   'Sin respuesta'),
        ('failed',      'Fallida'),
        ('canceled',    'Cancelada'),
    ], string='Estado', default='draft', required=True, index=True)

    twilio_sid   = fields.Char('Twilio Call SID', index=True, copy=False)
    caller_id    = fields.Char('Caller ID usado')
    voice        = fields.Char('Voz')
    realtime_model = fields.Char('Modelo')
    duration     = fields.Integer('Duración (s)')
    price        = fields.Float('Costo Twilio')
    price_unit   = fields.Char('Moneda')

    transcript   = fields.Text('Transcripción')
    disposition  = fields.Selection([
        ('no_outcome',       'Sin resultado'),
        ('info_provided',    'Información entregada'),
        ('committed_to_pay', 'Se compromete a pagar'),
        ('callback',         'Solicita devolución de llamada'),
        ('not_interested',   'No interesado'),
        ('voicemail',        'Buzón de voz'),
        ('wrong_number',     'Número equivocado'),
    ], string='Resultado')
    recording_url = fields.Char('Grabación (URL)')

    started_at    = fields.Datetime('Inicio')
    ended_at      = fields.Datetime('Fin')
    error_message = fields.Text('Mensaje de error')
    notes         = fields.Text('Notas')

    @api.depends('partner_id', 'phone', 'create_date')
    def _compute_display_name(self):
        for rec in self:
            who = rec.partner_id.name or rec.phone or _('Llamada')
            rec.display_name = f"{who} · {rec.phone or ''}".strip(' ·')

    # ----------------------------------------------------------------- helpers
    @api.model
    def _icp(self, key, default=''):
        return self.env['ir.config_parameter'].sudo().get_param(key, default)

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id and not self.phone:
            self.phone = self.partner_id.mobile or self.partner_id.phone or ''

    # ------------------------------------------------------------- place a call
    def action_place_call(self):
        """Ask the voice gateway to dial this contact and bridge Glenda."""
        self.ensure_one()
        if self._icp('voice_call.enabled', 'False') != 'True':
            raise UserError(_("Las llamadas de voz están desactivadas. Actívalas en "
                              "AI Agent → Configuración → Ajustes de Voz."))
        gateway = (self._icp('voice_call.gateway_url') or '').rstrip('/')
        if not gateway:
            raise UserError(_("Falta la URL del gateway de voz (Configuración → Ajustes de Voz)."))
        if not self.phone:
            raise UserError(_("El contacto no tiene teléfono destino."))

        callback_base = (self._icp('voice_call.callback_base') or
                         self._icp('web.base.url') or '').rstrip('/')
        payload = {
            'to': self.phone,
            'reason': self.call_reason or '',
            'caller_id': self._icp('voice_call.caller_id') or None,
            'voice': self._icp('voice_call.voice') or None,
            'model': self._icp('voice_call.realtime_model') or None,
            'odoo_call_id': self.id,
            'callback_url': f"{callback_base}/ai-agent/voice/callback" if callback_base else None,
            'tool_url': f"{callback_base}/ai-agent/voice/tool" if callback_base else None,
            'callback_token': self._icp('voice_call.callback_token') or None,
        }
        try:
            resp = requests.post(f"{gateway}/place-call", json=payload, timeout=20)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            self.write({'status': 'failed', 'error_message': str(e)})
            raise UserError(_("No se pudo contactar el gateway de voz: %s") % e)

        self.write({
            'twilio_sid': data.get('sid'),
            'caller_id':  data.get('from') or payload['caller_id'],
            'voice':      payload['voice'],
            'realtime_model': payload['model'],
            'status': 'queued',
            'error_message': False,
        })
        return True

    # --------------------------------------------------- ingest gateway updates
    @api.model
    def ingest_callback(self, vals):
        """Update a call record from a gateway/Twilio callback.

        Matched by odoo_call_id first, else twilio_sid. Only known fields applied.
        """
        rec = False
        if vals.get('odoo_call_id'):
            rec = self.browse(int(vals['odoo_call_id'])).exists()
        if not rec and vals.get('twilio_sid'):
            rec = self.search([('twilio_sid', '=', vals['twilio_sid'])], limit=1)
        if not rec:
            _logger.warning("voice callback: no matching call for %s", vals)
            return False

        writable = {}
        for k in ('status', 'duration', 'price', 'price_unit', 'transcript',
                  'recording_url', 'error_message', 'twilio_sid'):
            if k in vals and vals[k] is not None:
                writable[k] = vals[k]
        if vals.get('started_at'):
            writable['started_at'] = vals['started_at']
        if vals.get('ended_at'):
            writable['ended_at'] = vals['ended_at']
        rec.write(writable)
        _logger.info("voice callback applied to call %s: %s", rec.id, list(writable))
        return rec.id

    # ----------------------------------------------- realtime function tools
    @api.model
    def voice_tool(self, name, arguments=None):
        """Dispatch a function-tool call from the realtime session (via gateway).

        Returns a JSON-serialisable dict the model speaks back. Live data only —
        static facts (payment methods, tone) live in the gateway's voice prompt.
        """
        args = arguments or {}
        try:
            if name == 'get_pricing':
                return {'pricing_es': self.env['sale.order'].sudo().get_pricing_ground_truth()}
            if name == 'get_balance':
                return self._tool_get_balance(args.get('cedula'))
        except Exception as e:
            _logger.exception("voice_tool %s failed", name)
            return {'error': str(e)}
        return {'error': 'unknown_tool: %s' % name}

    @api.model
    def _tool_get_balance(self, cedula):
        """Outstanding posted-invoice balance for a representative by cédula (VAT)."""
        if not cedula:
            return {'found': False, 'error': 'cedula_required'}
        raw = re.sub(r'[^0-9VvEeJjGgPp]', '', cedula).upper()
        if raw and not raw[0].isalpha():
            raw = 'V' + raw
        Partner = self.env['res.partner'].sudo()
        partner = (Partner.search([('vat', '=', raw)], limit=1) or
                   Partner.search([('vat', 'ilike', raw[-7:])], limit=1))
        if not partner:
            return {'found': False}
        partner_ids = [partner.id] + partner.child_ids.ids
        invoices = self.env['account.move'].sudo().search([
            ('partner_id', 'in', partner_ids),
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ('not_paid', 'partial')),
            ('amount_residual_signed', '>', 0),
        ])
        total = sum(float(i.amount_residual_signed) for i in invoices)
        return {
            'found': True,
            'name': partner.name,
            'total_usd': round(total, 2),
            'invoice_count': len(invoices),
            'has_balance': total > 0,
        }
