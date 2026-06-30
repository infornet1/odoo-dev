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
    notice_key   = fields.Char(
        'Campaña / Encuesta',
        help='Si la llamada está ligada a una encuesta (p.ej. contingencia_academica_2026), '
             'Glenda puede registrar el voto del representante con record_survey_vote.')

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

    # --------------------------------------------- survey reminder call factory
    @api.model
    def create_contingencia_reminder(self, partner_id, phone=None,
                                     notice_key='contingencia_academica_2026'):
        """Create (not place) a voice call to remind a representative about the
        Contingencia Académica survey and capture their SÍ/NO live."""
        partner = self.env['res.partner'].browse(partner_id)
        name = partner.name or 'representante'
        dest = phone or partner.mobile or partner.phone or ''
        reason = (
            "LLAMADA DE RECORDATORIO DE ENCUESTA — sé BREVE y directa, SIN introducción larga. "
            "Confirma rápido que hablas con %s ('¿hablo con %s?') y ve al grano en 3 pasos cortos, "
            "una frase cada uno:\n"
            "1) CONTEXTO: 'Soy Glenda, del Colegio Andrés Bello. Le llamo porque aún no hemos "
            "recibido su respuesta a la encuesta del Plan de Contingencia Académica, que cierra "
            "mañana 1 de julio.'\n"
            "2) PREGUNTA: '¿Está usted de acuerdo con activar el plan bimodal —seguir las clases "
            "por Google Classroom y Google Meet si se interrumpen las clases presenciales—?'\n"
            "3) OPCIONES: 'Puede responder SÍ, estoy de acuerdo, o NO.'\n"
            "Cuando responda claramente SÍ o NO, REGÍSTRALO con record_survey_vote y confírmale "
            "en una frase que su voto quedó registrado. Si se despide, usa end_call.\n\n"
            "SOLO si la persona pide más detalle o duda, explica brevemente (no antes): el plan "
            "mantiene la continuidad académica desde casa, usando exclusivamente Google Classroom "
            "y Google Meet, si las autoridades exigen resguardar a los alumnos en sus hogares; se "
            "activa solo si la mayoría de la plantilla lo aprueba. Si prefiere responder por correo "
            "o WhatsApp, indícaselo. No repitas todo el contexto: sé concisa."
        ) % (name, name)
        return self.create({
            'partner_id': partner_id, 'phone': dest,
            'notice_key': notice_key, 'call_reason': reason,
        })

    @api.model
    def place_contingencia_reminder(self, partner_id, phone=None,
                                    notice_key='contingencia_academica_2026'):
        """Create + place a contingencia reminder in one shot. XML-RPC-safe
        (returns a dict, not a recordset). Used by the batch runner."""
        call = self.create_contingencia_reminder(partner_id, phone=phone, notice_key=notice_key)
        try:
            call.action_place_call()
        except Exception as e:
            return {'call_id': call.id, 'status': call.status, 'error': str(e)}
        return {'call_id': call.id, 'sid': call.twilio_sid or '', 'status': call.status}

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
    def voice_tool(self, name, arguments=None, odoo_call_id=None):
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
            if name == 'record_survey_vote':
                return self._tool_record_vote(odoo_call_id, args.get('decision'))
        except Exception as e:
            _logger.exception("voice_tool %s failed", name)
            return {'error': str(e)}
        return {'error': 'unknown_tool: %s' % name}

    @api.model
    def _tool_record_vote(self, odoo_call_id, decision):
        """Record a SÍ/NO survey vote against the called representative's ack record.

        Only fires for calls linked to a survey (notice_key + partner_id) and only
        when the record is still 'pending' (never overrides an existing vote).
        Stamped vote_channel='voice' + audit note for director review.
        """
        if not odoo_call_id:
            return {'recorded': False, 'error': 'no_call_context'}
        call = self.browse(int(odoo_call_id)).exists()
        if not call or not call.notice_key or not call.partner_id:
            return {'recorded': False, 'error': 'call_not_linked_to_survey'}
        d = (decision or '').strip().lower()
        if d in ('si', 'sí', 'yes', 'a', 'opcion_a', 'acuerdo', 'de_acuerdo'):
            state = 'continuing'
        elif d in ('no', 'b', 'opcion_b', 'desacuerdo'):
            state = 'leaving'
        else:
            return {'recorded': False, 'error': 'invalid_decision'}
        Ack = self.env['partner.communication.ack'].sudo()
        ack = Ack.search([('notice_key', '=', call.notice_key),
                          ('partner_id', '=', call.partner_id.id)], limit=1)
        if not ack:
            return {'recorded': False, 'error': 'no_ack_record'}
        if ack.state != 'pending':
            return {'recorded': False, 'already_voted': True, 'current_state': ack.state}
        now = fields.Datetime.now()
        ack.write({
            'state': state,
            'vote_channel': 'voice',
            'ack_date': now,
            'vote_notes': (ack.vote_notes or '') +
                          "\n[Glenda voz %s] decisión=%s · call #%s · tel %s" % (
                              now, state, call.id, call.phone or ''),
        })
        _logger.info("voice vote recorded: ack %s → %s (call %s)", ack.id, state, call.id)
        self._notify_vote_votacion(ack, call)
        return {'recorded': True, 'decision': state, 'partner': call.partner_id.name}

    @api.model
    def _notify_vote_votacion(self, ack, call):
        """Email votacion@ (CC) when a vote is captured by voice — mirrors the web/WA
        flow's confirmation so every voice vote is logged in the votacion@ inbox.
        Best-effort: never breaks the vote."""
        try:
            label = {'continuing': 'SÍ — Estoy de acuerdo', 'leaving': 'NO'}.get(
                ack.state, ack.state)
            name = ack.partner_name or (ack.partner_id.name if ack.partner_id else '')
            email = ack.partner_email or (ack.partner_id.email if ack.partner_id else '')
            phone = call.phone or ack.partner_phone or ''
            dt = ack.ack_date.strftime('%d/%m/%Y a las %H:%M') if ack.ack_date else ''
            campaign = ack.notice_label or ack.notice_key or 'Encuesta'
            subject = ("[Contingencia Académica] " if ack.notice_key ==
                       'contingencia_academica_2026' else "[Encuesta] ") + \
                      "%s — %s (voto por voz)" % (label, name)
            body = (
                "<div style=\"font-family:Arial,sans-serif;max-width:520px;\">"
                "<div style=\"background:#1a2c5b;color:#fff;padding:16px 22px;border-radius:8px 8px 0 0;\">"
                "<h2 style=\"margin:0;font-size:16px;\">&#128222; Voto registrado por llamada de voz (Glenda IA)</h2></div>"
                "<div style=\"background:#fff;border:1px solid #dde;padding:18px 22px;border-radius:0 0 8px 8px;font-size:13px;color:#333;\">"
                "<p style=\"margin:0 0 10px;\"><strong>Encuesta:</strong> %s</p>"
                "<p style=\"margin:0 0 10px;\"><strong>Representante:</strong> %s%s</p>"
                "<p style=\"margin:0 0 10px;\"><strong>Decisión:</strong> %s</p>"
                "<p style=\"margin:0 0 10px;\"><strong>Teléfono:</strong> %s</p>"
                "<p style=\"margin:0 0 10px;\"><strong>Fecha:</strong> %s</p>"
                "<p style=\"margin:14px 0 0;font-size:11px;color:#888;\">Capturado automáticamente por "
                "Glenda durante una llamada de voz saliente. Canal de voto: Llamada de voz (Glenda IA).</p>"
                "</div></div>"
            ) % (campaign, name, (' · ' + email) if email else '', label, phone, dt)
            inbox = 'votacion@ueipab.edu.ve'
            self.env['mail.mail'].sudo().create({
                'subject': subject,
                'email_from': 'Colegio Andrés Bello <votacion@ueipab.edu.ve>',
                'email_to': ('%s <%s>' % (name, email)) if email else inbox,
                'email_cc': inbox,
                'body_html': body,
                'state': 'outgoing',
            }).send()
            _logger.info("votacion@ voice-vote confirmation sent for ack %s", ack.id)
        except Exception:
            _logger.exception("votacion@ voice-vote confirmation failed for ack %s", ack.id)

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
