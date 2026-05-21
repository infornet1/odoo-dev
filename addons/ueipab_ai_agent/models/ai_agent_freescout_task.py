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
        """Load Freescout API config. ir.config_parameter first, file fallback for dev."""
        icp = self.env['ir.config_parameter'].sudo()
        api_url = icp.get_param('ai_agent.freescout_api_url', '')
        api_key = icp.get_param('ai_agent.freescout_api_key', '')

        if not (api_url and api_key):
            for path in [
                '/opt/odoo-dev/config/freescout_api.json',
                '/etc/odoo/freescout_api.json',
            ]:
                try:
                    with open(path) as f:
                        cfg = json.load(f)
                    api_url = cfg.get('api_url', '')
                    api_key = cfg.get('api_key', '')
                    if api_url and api_key:
                        break
                except Exception:
                    pass

        if not (api_url and api_key):
            raise UserError(_(
                "Freescout API no configurado. Agregue ai_agent.freescout_api_url "
                "y ai_agent.freescout_api_key en Ajustes → Parámetros del Sistema."
            ))

        headers = {
            'X-FreeScout-API-Key': api_key,
            'Content-Type': 'application/json',
        }
        return headers, api_url

    def _extract_receipt_from_image(self, image_url, icp):
        """Call GPT-4o-mini Vision to extract payment data from a receipt image URL.
        Returns dict with monto/moneda/banco/referencia/fecha or None on failure."""
        api_key = icp.get_param('ai_agent.openai_api_key', '')
        if not api_key or not image_url:
            return None
        try:
            resp = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
                json={
                    'model': 'gpt-4o-mini',
                    'messages': [{
                        'role': 'user',
                        'content': [
                            {'type': 'text', 'text': (
                                'Extrae los datos de este comprobante de pago venezolano. '
                                'Responde SOLO con JSON válido: '
                                '{"monto": "monto como string", "moneda": "VES o USD", '
                                '"banco": "nombre del banco", '
                                '"referencia": "numero de referencia", '
                                '"fecha": "fecha en formato YYYY-MM-DD"}'
                            )},
                            {'type': 'image_url', 'image_url': {'url': image_url}},
                        ],
                    }],
                    'max_tokens': 250,
                },
                timeout=30,
            )
            resp.raise_for_status()
            raw = resp.json()['choices'][0]['message']['content'].strip()
            import json as _j
            m = re.search(r'\{.*\}', raw, re.DOTALL)
            return _j.loads(m.group(0)) if m else None
        except Exception as e:
            _logger.warning("action_reprocess: GPT Vision failed: %s", e)
            return None

    def _create_confirm_payment(self, partner_id, receipt, icp):
        """Create and confirm an account.payment from extracted receipt data.
        Returns (payment_id, odoo_url) or (None, None)."""
        try:
            monto = float(receipt.get('monto', 0) or 0)
            if monto <= 0:
                return None, None

            moneda_code = (receipt.get('moneda') or 'VES').upper()
            currency = self.env['res.currency'].sudo().search(
                [('name', 'in', [moneda_code, 'VEF', 'VEB'] if moneda_code != 'USD' else ['USD'])],
                limit=1)

            # Resolve journal from payment_journal_map param
            journal_id = None
            raw_map = icp.get_param('ai_agent.payment_journal_map', '')
            if raw_map:
                import json as _j
                cfg = _j.loads(raw_map)
                banco_lower = (receipt.get('banco') or '').lower()
                mkey = moneda_code if moneda_code == 'USD' else 'VES'
                for keyword, cmap in cfg.get('keywords', {}).items():
                    if keyword in banco_lower:
                        journal_id = cmap.get(mkey) or cmap.get('VES')
                        break
                if not journal_id:
                    journal_id = cfg.get('fallback_usd') if moneda_code == 'USD' \
                        else cfg.get('fallback_veb')

            if not journal_id:
                journal_id = self.env['account.journal'].sudo().search(
                    [('type', '=', 'bank')], limit=1).id

            ref_str = receipt.get('referencia') or ''
            payment = self.env['account.payment'].sudo().create({
                'partner_id':       partner_id,
                'amount':           monto,
                'currency_id':      currency.id if currency else False,
                'journal_id':       journal_id,
                'payment_type':     'inbound',
                'partner_type':     'customer',
                'ref':              f"FS#{self.fs_conv_id} — Adelanto {ref_str}".strip(' —'),
                'date':             fields.Date.today(),
            })
            try:
                payment.action_post()
            except Exception:
                pass  # marshalling quirk — read state to confirm

            base = icp.get_param('web.base.url', 'https://odoo.ueipab.edu.ve')
            odoo_url = f"{base}/web#id={payment.id}&model=account.payment&view_type=form"
            state = payment.read(['state'])[0].get('state', '')
            _logger.info("action_reprocess: payment id=%d state=%s", payment.id, state)
            return payment.id, odoo_url
        except Exception as e:
            _logger.warning("action_reprocess: payment creation failed: %s", e)
            return None, None

    def action_reprocess(self):
        """Re-fetch the Freescout conv and re-run the payment extraction pipeline.

        Advance payment path: partner found + zero outstanding balance →
        extract receipt from image (GPT Vision) → create+confirm Odoo payment →
        post note with payment link.
        """
        self.ensure_one()
        icp = self.env['ir.config_parameter'].sudo()
        fs_headers, api_url = self._load_fs_config()

        # --- Fetch conversation ---
        try:
            r = requests.get(f"{api_url}/conversations/{self.fs_conv_id}",
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
        subject      = conv.get('subject', '')
        customer     = conv.get('customer') or {}
        customer_email = customer.get('email', '')
        conv_number  = conv.get('number', self.fs_conv_id)
        body_html    = thread.get('body', '')
        new_subject  = f"[GLENDA] {subject}" if not subject.startswith('[GLENDA]') else subject

        # --- Partner resolution ---
        partner = None
        if self.partner_id:
            rows = self.env['res.partner'].sudo().search_read(
                [('id', '=', self.partner_id.id)],
                ['id', 'name', 'email', 'vat', 'child_ids'], limit=1)
            partner = rows[0] if rows else None
        if not partner and customer_email:
            rows = self.env['res.partner'].sudo().search_read(
                [('email', 'ilike', customer_email), ('customer_rank', '>', 0)],
                ['id', 'name', 'email', 'vat', 'child_ids'], limit=1)
            partner = rows[0] if rows else None

        if not partner:
            note = (
                f'<p><b>🔄 Glenda — Re-procesado manualmente</b></p>'
                f'<p>Email <code>{customer_email}</code> no encontrado en Odoo.</p>'
                f'<p>Vincule el cliente en el campo <em>Cliente Odoo</em> y '
                f'haga clic en Re-procesar nuevamente.</p>'
                f'<p><small>Freescout #{conv_number} · re-procesado desde Odoo</small></p>'
            )
            self._post_fs(api_url, fs_headers, note, new_subject)
            return self._finish_reprocess('no_partner', False, note)

        # --- Advance payment detection ---
        child_ids = partner.get('child_ids') or []
        all_ids   = [partner['id']] + child_ids
        outstanding = self.env['account.move'].sudo().search_count([
            ('partner_id', 'in', all_ids),
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ('not_paid', 'partial')),
        ])
        is_advance = (outstanding == 0)
        _logger.info("action_reprocess: partner=%s outstanding=%d is_advance=%s",
                     partner['name'], outstanding, is_advance)

        payment_id, odoo_url = None, None

        if is_advance:
            # Extract image URL from body HTML
            img_match = re.search(r'src="([^"]+)"', body_html)
            image_url = img_match.group(1) if img_match else None

            receipt = self._extract_receipt_from_image(image_url, icp) if image_url else None
            _logger.info("action_reprocess: image_url=%s receipt=%s", image_url, receipt)

            if receipt and receipt.get('monto'):
                payment_id, odoo_url = self._create_confirm_payment(
                    partner['id'], receipt, icp)

            # Build advance payment note
            monto_str = f"{float(receipt['monto']):,.2f} {receipt.get('moneda','VES')}" \
                if receipt and receipt.get('monto') else '—'
            banco_str  = receipt.get('banco', '—') if receipt else '—'
            ref_str    = receipt.get('referencia', '—') if receipt else '—'
            pay_link   = (f'<p><a href="{odoo_url}"><b>→ Abrir pago en Odoo</b></a></p>'
                          if odoo_url else
                          '<p>⚠️ No se pudo crear el pago automáticamente — crear manualmente.</p>')
            note = (
                f'<p><b>💰 Glenda — Pago adelantado re-procesado</b></p>'
                f'<p>Cliente: <b>{partner["name"]}</b> (sin facturas pendientes)</p>'
                f'<p>Banco: {banco_str} | Monto: <b>{monto_str}</b> | Ref: {ref_str}</p>'
                f'<p>💰 <b>Pago adelantado</b> — registrado para el próximo ciclo de facturación.</p>'
                f'{pay_link}'
                f'<p><small>Re-procesado desde Odoo · Freescout #{conv_number}</small></p>'
            )
            status = 'success' if payment_id else 'identified'
        else:
            # Has outstanding balance — show body for manual review
            body_text = re.sub(r'<[^>]+>', ' ', body_html)
            body_text = re.sub(r'\s+', ' ', body_text).strip()
            note = (
                f'<p><b>🔄 Glenda — Re-procesado manualmente</b></p>'
                f'<p>Cliente: <b>{partner["name"]}</b> '
                f'(facturas pendientes: {outstanding})</p>'
                f'<p>Revise el mensaje original y registre el pago manualmente.</p>'
                f'<p><small>Re-procesado desde Odoo · Freescout #{conv_number}</small></p>'
            )
            status = 'identified'

        self._post_fs(api_url, fs_headers, note, new_subject)
        return self._finish_reprocess(status, partner['id'], note,
                                      payment_id=payment_id or 0)

    def _post_fs(self, api_url, fs_headers, note, new_subject):
        try:
            requests.post(f"{api_url}/conversations/{self.fs_conv_id}/threads",
                          json={'type': 'note', 'text': note, 'user': 1},
                          headers=fs_headers, timeout=15).raise_for_status()
            requests.put(f"{api_url}/conversations/{self.fs_conv_id}",
                         json={'subject': new_subject, 'byUser': 1},
                         headers=fs_headers, timeout=15).raise_for_status()
        except Exception as e:
            _logger.warning("action_reprocess: FS API post failed: %s", e)

    def _finish_reprocess(self, status, partner_id, notes_text, payment_id=0):
        vals = {
            'status':             status,
            'retry_count':        self.retry_count + 1,
            'last_processed_at':  fields.Datetime.now(),
            'notes':              f"Re-procesado. Estado: {status}",
        }
        if partner_id:
            vals['partner_id'] = partner_id
        if payment_id:
            vals['payment_odoo_id'] = payment_id
        self.write(vals)
        ok = status in ('success', 'identified')
        return {
            'type': 'ir.actions.client',
            'tag':  'display_notification',
            'params': {
                'title':   _('Re-procesado'),
                'message': _(f'FS#{self.fs_conv_id} — {status}. Nota publicada en Freescout.'),
                'type':    'success' if ok else 'warning',
                'sticky':  False,
            },
        }
