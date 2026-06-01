# -*- coding: utf-8 -*-
import logging
from collections import defaultdict
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

TAG_REP   = 25
TAG_PDVSA = 26
TAG_VIP   = 30
MIN_BALANCE = 1.00
LOGO_URL  = 'https://odoo.ueipab.edu.ve/web/image/res.company/1/logo'
RATE_URL  = 'https://odoo.ueipab.edu.ve/tasas-de-cambios'
WA_TRIGGER_PARAM = 'wa_invoice_reminder.trigger_at'
MONTHS_ES = {1:'enero',2:'febrero',3:'marzo',4:'abril',5:'mayo',6:'junio',
             7:'julio',8:'agosto',9:'septiembre',10:'octubre',11:'noviembre',12:'diciembre'}


def _fmt_usd(n):
    return f'${n:,.2f} USD'


def _fmt_date(d):
    if not d:
        return '—'
    return f'{MONTHS_ES[d.month].capitalize()} {d.year}'


class InvoiceReminderWizard(models.TransientModel):
    _name = 'account.invoice.reminder.wizard'
    _description = 'Invoice Balance Reminder Wizard'

    tag_filter = fields.Selection([
        ('both',  'Representante + PDVSA'),
        ('rep',   'Representante Only'),
        ('pdvsa', 'PDVSA Only'),
    ], string='Segment', default='both', required=True)

    include_vip = fields.Boolean(
        string='Include VIP Customers',
        default=False,
        help='VIP customers are excluded from automated sends. '
             'Enable this to include them in a manual send.',
    )

    line_ids = fields.One2many(
        'account.invoice.reminder.line', 'wizard_id',
        string='Partners',
    )

    partner_count = fields.Integer(
        string='Will Send', compute='_compute_stats')
    total_balance = fields.Float(
        string='Total Balance', compute='_compute_stats', digits=(16, 2))
    skipped_count = fields.Integer(
        string='Skipped', compute='_compute_stats')

    state = fields.Selection([
        ('preview', 'Preview'),
        ('done',    'Done'),
    ], default='preview')

    sent_count    = fields.Integer(string='Sent',    default=0)
    failed_count  = fields.Integer(string='Failed',  default=0)
    no_email_count = fields.Integer(string='No Email', default=0)

    wa_queued_at  = fields.Datetime(string='WA en cola desde', readonly=True)
    wa_count      = fields.Integer(string='WA: enviarán', compute='_compute_stats')

    # ── Computed ──────────────────────────────────────────────────────────

    @api.depends('line_ids.will_send', 'line_ids.wa_will_send', 'line_ids.balance', 'line_ids.selected')
    def _compute_stats(self):
        for wiz in self:
            sendable = wiz.line_ids.filtered(lambda l: l.will_send and l.selected)
            wiz.partner_count = len(sendable)
            wiz.total_balance = sum(sendable.mapped('balance'))
            wiz.skipped_count = len(wiz.line_ids) - len(sendable)
            wiz.wa_count = len(wiz.line_ids.filtered(lambda l: l.wa_will_send and l.selected))

    # ── Default / onchange ────────────────────────────────────────────────

    @api.model
    def default_get(self, fields_list):
        return super().default_get(fields_list)

    @api.onchange('tag_filter', 'include_vip')
    def _onchange_tag_filter(self):
        self.line_ids = [(5, 0, 0)] + self._compute_lines(
            self.tag_filter or 'both', include_vip=self.include_vip or False)

    def _compute_lines(self, tag_filter, include_vip=False):
        tags = {
            'both':  [TAG_REP, TAG_PDVSA],
            'rep':   [TAG_REP],
            'pdvsa': [TAG_PDVSA],
        }[tag_filter]

        partners = self.env['res.partner'].search([
            ('category_id', 'in', tags),
            ('active', '=', True),
        ])
        if not partners:
            return []

        # Employee VATs to exclude
        employee_vats = set(
            self.env['hr.employee'].search([
                ('active', '=', True),
                ('identification_id', '!=', False),
            ]).mapped(lambda e: (e.identification_id or '').strip().upper())
        )

        # All unpaid invoices — balance
        unpaid = self.env['account.move'].search([
            ('partner_id', 'in', partners.ids),
            ('move_type', 'in', ['out_invoice', 'out_receipt']),
            ('state', '=', 'posted'),
            ('payment_state', 'not in', ['paid', 'reversed']),
        ])
        balance_map = defaultdict(float)
        for inv in unpaid:
            balance_map[inv.partner_id.id] += inv.amount_residual_signed

        # All posted invoices — find latest per partner
        all_posted = self.env['account.move'].search([
            ('partner_id', 'in', partners.ids),
            ('move_type', 'in', ['out_invoice', 'out_receipt']),
            ('state', '=', 'posted'),
        ])
        latest_map = {}
        for inv in all_posted:
            pid = inv.partner_id.id
            if pid not in latest_map or (inv.invoice_date and inv.invoice_date > latest_map[pid]['date']):
                latest_map[pid] = {
                    'date':          inv.invoice_date,
                    'fiscal_check':  inv.fiscal_check,
                    'amount_total':  inv.amount_total,
                    'amount_residual': inv.amount_residual,
                    'payment_state': inv.payment_state,
                }

        lines = []
        for p in partners:
            pid      = p.id
            vat      = (p.vat or '').strip().upper()
            balance  = balance_map.get(pid, 0.0)
            is_pdvsa = TAG_PDVSA in p.category_id.ids
            tag_label = 'PDVSA' if is_pdvsa else 'REP'
            latest   = latest_map.get(pid, {})
            is_vip   = TAG_VIP in p.category_id.ids

            # Business logic exclusions — apply to both email and WA
            biz_skip = False
            if is_vip and not include_vip:
                biz_skip = 'VIP_EXCLUDED'
            elif vat and vat in employee_vats:
                biz_skip = 'IS_EMPLOYEE'
            elif is_pdvsa and latest.get('fiscal_check'):
                biz_skip = 'PDVSA_FISCAL_EXCLUDED'
            elif is_pdvsa and latest.get('payment_state') == 'partial':
                total    = latest.get('amount_total') or 0.0
                residual = latest.get('amount_residual') or 0.0
                if total > 0 and ((total - residual) / total * 100) >= 30.0:
                    biz_skip = 'PDVSA_ADVANCE_PAID'
            if not biz_skip and balance < MIN_BALANCE:
                biz_skip = 'BELOW_THRESHOLD'

            # Channel eligibility (independent)
            will_send    = not biz_skip and bool(p.email)
            wa_will_send = not biz_skip and bool(p.mobile)

            # Display skip reason: business reason takes priority
            skip_reason = biz_skip
            if not biz_skip and not p.email and not p.mobile:
                skip_reason = 'NO_CONTACT'
            elif not biz_skip and not p.email:
                skip_reason = 'NO_EMAIL'
            elif not biz_skip and not p.mobile:
                skip_reason = 'NO_MOBILE'

            lines.append((0, 0, {
                'partner_id':    pid,
                'tag':           tag_label,
                'balance':       balance,
                'email':         p.email or '',
                'mobile':        p.mobile or '',
                'will_send':     will_send,
                'wa_will_send':  wa_will_send,
                'skip_reason':   skip_reason or '',
                'selected':      will_send or wa_will_send,
                'status':        'pending',
            }))

        return lines

    # ── Actions ───────────────────────────────────────────────────────────

    def action_refresh(self):
        self.line_ids = [(5, 0, 0)] + self._compute_lines(
            self.tag_filter, include_vip=self.include_vip)
        return {'type': 'ir.actions.act_window', 'res_model': self._name,
                'res_id': self.id, 'view_mode': 'form', 'target': 'new'}

    def action_send(self):
        self.ensure_one()
        to_send = self.line_ids.filtered(lambda l: l.will_send and l.selected)
        if not to_send:
            raise UserError(_('No partners selected to send.'))

        sent = failed = no_email = 0

        for line in to_send:
            partner = line.partner_id
            if not partner.email:
                line.status = 'no_email'
                no_email += 1
                continue

            try:
                html = self._build_email_html(partner)
                mail = self.env['mail.mail'].create({
                    'subject':    'Recordatorio de Saldo Pendiente — Colegio Andrés Bello',
                    'email_from': 'Colegio Andrés Bello - Pagos <finanzas@ueipab.edu.ve>',
                    'reply_to':   'pagos@ueipab.edu.ve',
                    'email_to':   partner.email,
                    'email_cc':   'pagos@ueipab.edu.ve',
                    'body_html':  html,
                    'state':      'outgoing',
                })
                mail.send()
                line.status = 'sent'
                sent += 1
                _logger.info("Invoice reminder sent to %s <%s>", partner.name, partner.email)
            except Exception as e:
                _logger.error("Invoice reminder failed for %s: %s", partner.name, e)
                line.status = 'failed'
                line.error_msg = str(e)[:200]
                failed += 1

        self.write({
            'state':         'done',
            'sent_count':    sent,
            'failed_count':  failed,
            'no_email_count': no_email,
        })
        return {'type': 'ir.actions.act_window', 'res_model': self._name,
                'res_id': self.id, 'view_mode': 'form', 'target': 'new'}

    def action_send_wa(self):
        self.ensure_one()
        wa_eligible = self.line_ids.filtered(lambda l: l.wa_will_send and l.selected)
        if not wa_eligible:
            raise UserError(_('No hay partners con número móvil elegibles para WA.'))
        # Write trigger param — dev server poller picks this up within 5 min and runs the script
        self.env['ir.config_parameter'].sudo().set_param(
            WA_TRIGGER_PARAM,
            fields.Datetime.now().isoformat(),
        )
        self.wa_queued_at = fields.Datetime.now()
        return {'type': 'ir.actions.act_window', 'res_model': self._name,
                'res_id': self.id, 'view_mode': 'form', 'target': 'new'}

    def action_select_all(self):
        self.line_ids.filtered('will_send').write({'selected': True})
        return {'type': 'ir.actions.act_window', 'res_model': self._name,
                'res_id': self.id, 'view_mode': 'form', 'target': 'new'}

    def action_deselect_all(self):
        self.line_ids.write({'selected': False})
        return {'type': 'ir.actions.act_window', 'res_model': self._name,
                'res_id': self.id, 'view_mode': 'form', 'target': 'new'}

    # ── Email builder ─────────────────────────────────────────────────────

    def _build_email_html(self, partner):
        invoices = self.env['account.move'].search([
            ('partner_id', '=', partner.id),
            ('move_type', 'in', ['out_invoice', 'out_receipt']),
            ('state', '=', 'posted'),
            ('payment_state', 'not in', ['paid', 'reversed']),
        ], order='invoice_date desc')

        total_due = sum(invoices.mapped('amount_residual'))
        rows_html = ''
        for inv in invoices:
            badge = (
                '<span style="background:#fff3cd;color:#856404;padding:2px 9px;'
                'border-radius:10px;font-size:11px;font-weight:600;">Parcial</span>'
                if inv.payment_state == 'partial' else
                '<span style="background:#f8d7da;color:#721c24;padding:2px 9px;'
                'border-radius:10px;font-size:11px;font-weight:600;">Pendiente</span>'
            )
            rows_html += f'''<tr>
              <td style="padding:10px 14px;border-bottom:1px solid #e8ecf0;color:#333;font-size:13px;">{inv.name}</td>
              <td style="padding:10px 14px;border-bottom:1px solid #e8ecf0;color:#333;font-size:13px;">{_fmt_date(inv.invoice_date)}</td>
              <td style="padding:10px 14px;border-bottom:1px solid #e8ecf0;text-align:right;color:#333;font-size:13px;">{_fmt_usd(inv.amount_total)}</td>
              <td style="padding:10px 14px;border-bottom:1px solid #e8ecf0;text-align:right;font-weight:600;color:#c0392b;font-size:13px;">{_fmt_usd(inv.amount_residual)}</td>
              <td style="padding:10px 14px;border-bottom:1px solid #e8ecf0;text-align:center;">{badge}</td>
            </tr>'''

        return f'''<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f0f4fa;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f4fa;padding:30px 0;">
<tr><td align="center">
<table width="640" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 3px 12px rgba(0,0,0,0.10);">
  <tr><td style="background:#1a2c5b;padding:24px 36px;text-align:center;">
    <img src="{LOGO_URL}" alt="Colegio Andrés Bello" height="64"
         style="display:block;margin:0 auto 12px;border-radius:6px;background:#fff;padding:4px;"/>
    <div style="color:#fff;font-size:20px;font-weight:bold;letter-spacing:0.5px;">Colegio Andrés Bello</div>
    <div style="color:#a8c4e0;font-size:12px;margin-top:4px;">Sistema de Cobranzas — Aviso de Saldo Pendiente</div>
  </td></tr>
  <tr><td style="background:#2471a3;height:4px;"></td></tr>
  <tr><td style="padding:30px 36px 10px;">
    <p style="color:#1a2c5b;font-size:16px;margin:0 0 6px;">Estimado/a <strong>{partner.name}</strong>,</p>
    <p style="color:#555;font-size:14px;line-height:1.6;margin:0 0 24px;">
      Le informamos que tiene facturas con saldo pendiente de pago. A continuación el detalle actualizado de su cuenta:
    </p>
    <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;border:1px solid #dde4ef;font-size:13px;">
      <thead><tr style="background:#1a2c5b;">
        <th style="padding:11px 14px;color:#fff;text-align:left;font-weight:600;">Factura</th>
        <th style="padding:11px 14px;color:#fff;text-align:left;font-weight:600;">Período</th>
        <th style="padding:11px 14px;color:#fff;text-align:right;font-weight:600;">Monto Total</th>
        <th style="padding:11px 14px;color:#fff;text-align:right;font-weight:600;">Saldo Pendiente</th>
        <th style="padding:11px 14px;color:#fff;text-align:center;font-weight:600;">Estado</th>
      </tr></thead>
      <tbody>
        {rows_html}
        <tr style="background:#eaf0f8;">
          <td colspan="3" style="padding:13px 14px;font-weight:700;color:#1a2c5b;font-size:14px;">TOTAL A PAGAR</td>
          <td style="padding:13px 14px;font-weight:700;color:#c0392b;font-size:17px;text-align:right;">{_fmt_usd(total_due)}</td>
          <td></td>
        </tr>
      </tbody>
    </table>
    <p style="color:#888;font-size:12px;margin:10px 0 28px;text-align:right;">
      Aquí puede consultar la tasa de cambio oficial —
      <a href="{RATE_URL}" style="color:#2471a3;font-weight:600;">Ver tasas de cambio</a>
    </p>
    <div style="border:1px solid #dde4ef;border-radius:8px;overflow:hidden;margin-bottom:28px;">
      <div style="background:#2471a3;padding:12px 18px;">
        <span style="color:#fff;font-weight:700;font-size:14px;">&#128179; Opciones de Pago Disponibles</span>
      </div>
      <div style="padding:18px;">
        <p style="margin:0 0 8px;font-weight:700;color:#1a2c5b;font-size:13px;">&#127974; Transferencia Bancaria</p>
        <table width="100%" cellpadding="0" cellspacing="0" style="font-size:12px;border-collapse:collapse;margin-bottom:16px;">
          <tr style="background:#f0f4fa;">
            <th style="padding:7px 10px;text-align:left;color:#1a2c5b;border-bottom:1px solid #dde4ef;">Banco</th>
            <th style="padding:7px 10px;text-align:left;color:#1a2c5b;border-bottom:1px solid #dde4ef;">Tipo</th>
            <th style="padding:7px 10px;text-align:left;color:#1a2c5b;border-bottom:1px solid #dde4ef;">Número de Cuenta</th>
          </tr>
          <tr><td style="padding:7px 10px;border-bottom:1px solid #f0f4fa;color:#333;">Banco de Venezuela</td><td style="padding:7px 10px;color:#555;">Corriente</td><td style="padding:7px 10px;color:#333;font-family:monospace;">0102-0445-34-0007673100</td></tr>
          <tr style="background:#fafbfd;"><td style="padding:7px 10px;border-bottom:1px solid #f0f4fa;color:#333;">Banco Mercantil</td><td style="padding:7px 10px;color:#555;">Corriente</td><td style="padding:7px 10px;color:#333;font-family:monospace;">0105-0069-93-1069377856</td></tr>
          <tr><td style="padding:7px 10px;border-bottom:1px solid #f0f4fa;color:#333;">BanPlus</td><td style="padding:7px 10px;color:#555;">Corriente</td><td style="padding:7px 10px;color:#333;font-family:monospace;">0174-0127-12-1274138559</td></tr>
          <tr style="background:#fafbfd;"><td style="padding:7px 10px;border-bottom:1px solid #f0f4fa;color:#333;">Banco Plaza</td><td style="padding:7px 10px;color:#555;">Corriente</td><td style="padding:7px 10px;color:#333;font-family:monospace;">0138-0032-47-0320013870</td></tr>
          <tr><td style="padding:7px 10px;color:#333;">Bancamiga</td><td style="padding:7px 10px;color:#555;">Corriente</td><td style="padding:7px 10px;color:#333;font-family:monospace;">0172-0702-44-7024976891</td></tr>
        </table>
        <p style="margin:0 0 6px;font-weight:700;color:#1a2c5b;font-size:13px;">&#128241; Pago Móvil</p>
        <p style="margin:0 0 16px;color:#555;font-size:12px;line-height:1.7;">
          Teléfono: <strong>04141906296</strong> &nbsp;|&nbsp; RIF: <strong>J-08008617-1</strong><br>
          Bancos: Venezuela (0102) &bull; Mercantil (0105) &bull; BanPlus (0174)
        </p>
        <p style="margin:0 0 6px;font-weight:700;color:#1a2c5b;font-size:13px;">&#127760; Pagos Digitales</p>
        <p style="margin:0 0 16px;color:#555;font-size:12px;line-height:1.8;">
          <strong>Zelle:</strong> pagos@ueipab.edu.ve<br>
          <strong>Binance ID:</strong> 383 867 49<br>
          <strong>Tarjetas VISA / Mastercard:</strong>
          <a href="https://www.portaldepagosmercantil.com/" style="color:#2471a3;">Portal de Pagos Mercantil</a>
        </p>
        <p style="margin:0 0 6px;font-weight:700;color:#1a2c5b;font-size:13px;">&#128181; Depósito en Efectivo (USD)</p>
        <p style="margin:0 0 16px;color:#555;font-size:12px;">Banco Mercantil — Cuenta: <strong>5069006770</strong></p>
        <div style="background:#eaf0f8;border-radius:6px;padding:10px 14px;">
          <p style="margin:0;color:#1a2c5b;font-size:12px;">
            &#9432; Luego de realizar su pago, notifíquenos a
            <a href="mailto:pagos@ueipab.edu.ve" style="color:#2471a3;font-weight:600;">pagos@ueipab.edu.ve</a>
            o por WhatsApp <strong>+58 414-832-1989</strong> (Glenda) adjuntando el comprobante.
          </p>
        </div>
      </div>
    </div>
  </td></tr>
  <tr><td style="background:#1a2c5b;padding:18px 36px;text-align:center;">
    <p style="color:#a8c4e0;font-size:11px;margin:0;line-height:1.7;">
      Este es un recordatorio automático del sistema de cobranzas — Colegio Andrés Bello<br>
      RIF: J-08008617-1 &bull; <a href="https://odoo.ueipab.edu.ve" style="color:#a8c4e0;">odoo.ueipab.edu.ve</a><br>
      Si ya realizó su pago, por favor ignore este mensaje.
    </p>
  </td></tr>
</table>
</td></tr>
</table>
</body></html>'''


class InvoiceReminderLine(models.TransientModel):
    _name = 'account.invoice.reminder.line'
    _description = 'Invoice Reminder Wizard Line'
    _order = 'tag, partner_name'

    wizard_id    = fields.Many2one('account.invoice.reminder.wizard', ondelete='cascade')
    partner_id   = fields.Many2one('res.partner', string='Partner')
    partner_name = fields.Char(related='partner_id.name', string='Name', store=True)
    tag          = fields.Char(string='Tag')
    balance      = fields.Float(string='Balance Due', digits=(16, 2))
    email        = fields.Char(string='Email')
    mobile       = fields.Char(string='Móvil')
    will_send    = fields.Boolean(string='Email Elegible')
    wa_will_send = fields.Boolean(string='WA Elegible')
    skip_reason  = fields.Char(string='Skip Reason')
    selected     = fields.Boolean(string='Send', default=True)
    status       = fields.Selection([
        ('pending',  'Pending'),
        ('sent',     'Sent'),
        ('failed',   'Failed'),
        ('no_email', 'No Email'),
    ], default='pending', string='Estado Email')
    error_msg    = fields.Char(string='Error')
