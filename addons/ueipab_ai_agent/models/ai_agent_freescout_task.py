import json
import logging
import re

import requests

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AiAgentFreescoutTask(models.Model):
    _name = 'ai.agent.freescout.task'
    _description = 'Freescout Pagos@ Task — Glenda Processing Log'
    _order = 'last_processed_at desc, id desc'
    _rec_name = 'fs_subject'

    fs_conv_id       = fields.Integer('Freescout Conv #', index=True, required=True)
    fs_subject       = fields.Char('Asunto')
    sender_email     = fields.Char('Email remitente')
    partner_id       = fields.Many2one('res.partner', string='Cliente Odoo', ondelete='set null')
    sheet_match      = fields.Char('Nombre en hoja Customers')
    status           = fields.Selection([
        ('pending',    'Pendiente'),
        ('identified', 'Identificado'),
        ('no_partner', 'Sin cliente'),
        ('no_receipt', 'Sin comprobante'),
        ('duplicate',  'Duplicado'),
        ('success',    'Procesado ✓'),
        ('error',      'Error'),
    ], string='Estado', default='pending', required=True)
    extracted_json   = fields.Text('Datos extraídos (JSON)')
    payment_odoo_id  = fields.Integer('ID Pago Odoo')
    retry_count      = fields.Integer('Reintentos', default=0)
    last_processed_at = fields.Datetime('Último proceso')
    notes            = fields.Text('Notas')
    fs_url           = fields.Char('URL Freescout', compute='_compute_fs_url', store=False)

    @api.depends('fs_conv_id')
    def _compute_fs_url(self):
        for rec in self:
            rec.fs_url = (
                f'https://freescout.ueipab.edu.ve/conversation/{rec.fs_conv_id}'
                if rec.fs_conv_id else ''
            )

    def action_open_freescout(self):
        self.ensure_one()
        if not self.fs_conv_id:
            raise UserError(_("No hay ID de conversación Freescout."))
        return {
            'type': 'ir.actions.act_url',
            'url':  self.fs_url,
            'target': 'new',
        }

    def _load_fs_config(self):
        """Load Freescout API config from JSON file. Returns (headers, api_url)."""
        try:
            with open('/opt/odoo-dev/config/freescout_api.json') as f:
                fs_cfg = json.load(f)
        except Exception as e:
            raise UserError(_(f"No se pudo cargar config Freescout: {e}"))
        headers = {
            'X-FreeScout-API-Key': fs_cfg['api_key'],
            'Content-Type': 'application/json',
        }
        return headers, fs_cfg['api_url']

    def action_reprocess(self):
        """Re-fetch the Freescout conv and re-run the payment extraction pipeline."""
        self.ensure_one()

        fs_headers, api_url = self._load_fs_config()

        # Fetch conversation from Freescout API
        try:
            r = requests.get(
                f"{api_url}/conversations/{self.fs_conv_id}",
                headers=fs_headers, timeout=15)
            r.raise_for_status()
            conv = r.json()
        except Exception as e:
            raise UserError(_(f"Error al obtener conversación FS#{self.fs_conv_id}: {e}"))

        threads = conv.get('_embedded', {}).get('threads', [])
        customer_threads = [t for t in threads if t.get('type') == 'customer']
        if not customer_threads:
            raise UserError(_("No se encontraron mensajes del cliente en esta conversación."))

        thread = customer_threads[-1]
        subject = conv.get('subject', '')
        customer = conv.get('customer') or {}
        customer_email = customer.get('email', '')
        conv_number = conv.get('number', self.fs_conv_id)

        # Partner resolution: use overridden partner_id on the task, or look up by email
        partner = None
        if self.partner_id:
            partner_rows = self.env['res.partner'].sudo().search_read(
                [('id', '=', self.partner_id.id)],
                ['id', 'name', 'email', 'vat', 'child_ids'], limit=1)
            partner = partner_rows[0] if partner_rows else None

        if not partner and customer_email:
            partner_rows = self.env['res.partner'].sudo().search_read(
                [('email', '=ilike', customer_email), ('customer_rank', '>', 0)],
                ['id', 'name', 'email', 'vat', 'child_ids'], limit=1)
            partner = partner_rows[0] if partner_rows else None

        # Extract body text
        body_html = thread.get('body', '')
        body_text = re.sub(r'<[^>]+>', ' ', body_html)
        body_text = re.sub(r'\s+', ' ', body_text).strip()

        # Build note based on outcome
        new_subject = (
            f"[GLENDA] {subject}"
            if not subject.startswith('[GLENDA]') else subject
        )

        if not partner:
            note = (
                f'<p><b>🔄 Glenda — Re-procesado manualmente</b></p>'
                f'<p>Email <code>{customer_email}</code> no encontrado en Odoo.</p>'
                f'<p>Vincule el cliente en el campo <em>Cliente Odoo</em> del formulario '
                f'y haga clic en Re-procesar nuevamente.</p>'
                f'<p><small>Freescout #{conv_number} · re-procesado desde Odoo</small></p>'
            )
            status = 'no_partner'
        else:
            note = (
                f'<p><b>🔄 Glenda — Re-procesado manualmente</b></p>'
                f'<p>Cliente: <b>{partner["name"]}</b></p>'
                f'<p>Cuerpo del mensaje analizado:</p>'
                f'<pre style="font-size:11px;background:#f5f5f5;padding:8px">'
                f'{body_text[:600]}</pre>'
                f'<p><em>Revise el mensaje original en Freescout y registre el pago manualmente '
                f'si se confirma el comprobante.</em></p>'
                f'<p><small>Freescout #{conv_number} · re-procesado desde Odoo</small></p>'
            )
            status = 'identified'

        # Post note to Freescout via API
        try:
            requests.post(
                f"{api_url}/conversations/{self.fs_conv_id}/threads",
                json={'type': 'note', 'text': note, 'user': 1},
                headers=fs_headers, timeout=15).raise_for_status()
            requests.put(
                f"{api_url}/conversations/{self.fs_conv_id}",
                json={'subject': new_subject, 'byUser': 1},
                headers=fs_headers, timeout=15).raise_for_status()
        except Exception as e:
            _logger.warning("action_reprocess: FS API error: %s", e)

        # Update bridge record
        self.write({
            'status': status,
            'partner_id': partner['id'] if partner else (self.partner_id.id or False),
            'retry_count': self.retry_count + 1,
            'last_processed_at': fields.Datetime.now(),
            'notes': f"Re-procesado manualmente. Estado: {status}",
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Re-procesado'),
                'message': _(
                    f'FS#{self.fs_conv_id} — {status}. '
                    f'Nota publicada en Freescout.'
                ),
                'type': 'success' if status == 'identified' else 'warning',
                'sticky': False,
            },
        }
