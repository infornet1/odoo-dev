# -*- coding: utf-8 -*-
"""UEIPAB Sales — enrollment quotation engine + AI quote controls.

Pricing source: comunicado oficial 10/06/2026 "Proceso de Inscripciones
2026-2027" (Opción A aprobada). Three time-windowed llamados; prices live
in product.template records (default_code based), NOT in code or AI prompts.
"""
import logging
from datetime import date

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Enrollment windows 2026-2027. The engine picks the row whose window
# contains today; after the last window the L3 (regular) pricing applies.
UEIPAB_LLAMADOS = [
    {
        'code': 'L1',
        'name': '1er Llamado — Promoción Especial',
        'start': date(2026, 6, 11),
        'end': date(2026, 7, 31),
        'ins': 'INS2627-L1',
        'men': {1: 'MEN2627-PROMO', 2: 'MEN2627-PROMO-H2',
                3: 'MEN2627-PROMO-H3', 4: 'MEN2627-PROMO-H4'},
        'ing': 'ING2627-P',
        'convenio': True,
    },
    {
        'code': 'L2',
        'name': '2do Llamado — Promoción Periodo Vacacional',
        'start': date(2026, 8, 1),
        'end': date(2026, 8, 31),
        'ins': 'INS2627-L2',
        'men': {1: 'MEN2627-BASE', 2: 'MEN2627-H2',
                3: 'MEN2627-H3', 4: 'MEN2627-H4'},
        'ing': 'ING2627-R',
        'convenio': False,
    },
    {
        'code': 'L3',
        'name': '3er Llamado — Regular',
        'start': date(2026, 9, 1),
        'end': date(2026, 9, 30),
        'ins': 'INS2627-L3',
        'men': {1: 'MEN2627-BASE', 2: 'MEN2627-H2',
                3: 'MEN2627-H3', 4: 'MEN2627-H4'},
        'ing': 'ING2627-R',
        'convenio': False,
    },
]

# Annual per-student products (seguro / olimpiadas / enciclopedia);
# the inglés guide code is window-dependent (see UEIPAB_LLAMADOS['ing']).
UEIPAB_ANUALES = ['SEG2627', 'OLI2627', 'ENC2627']

UEIPAB_BCV_NOTE = ("NOTA IMPORTANTE: Todos los montos están expresados en USD. "
                   "Debe ser pagado a la tasa BCV del día.")


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    ueipab_payment_due_date = fields.Date(
        string='Fecha de pago acordada', copy=False,
        help='Convenio 1er Llamado: fecha acordada con el representante para '
             'pagar este concepto. La fecha definitiva se establece al momento '
             'de la firma en la institución.')


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    is_glenda_quote = fields.Boolean(
        string='Cotización Glenda (IA)', default=False, copy=False,
        help='Creada automáticamente por el agente IA. Los correos de Odoo '
             'al cliente se suprimen: la entrega es por el canal de Glenda.')
    quote_channel = fields.Selection(
        [('telegram', 'Telegram'), ('whatsapp', 'WhatsApp'), ('manual', 'Manual')],
        string='Canal de Cotización', default='manual', copy=False)

    # ── Email suppression ────────────────────────────────────────────────────

    def _ueipab_suppress_ai_emails(self):
        ICP = self.env['ir.config_parameter'].sudo()
        return ICP.get_param(
            'ueipab_sales.suppress_ai_quote_emails', 'True').lower() == 'true'

    def _send_order_notification_mail(self, mail_template):
        # Single funnel for confirmation / payment mails in Odoo 17.
        # AI quotes must never email the customer (delivery via Glenda).
        if self.is_glenda_quote and self._ueipab_suppress_ai_emails():
            _logger.info(
                "ueipab_sales: suppressed customer mail for AI quote %s", self.name)
            return
        return super()._send_order_notification_mail(mail_template)

    # ── Convenio payment plan (1er llamado) ──────────────────────────────────

    def action_generate_payment_plan(self):
        """Create one draft invoice per agreed due date (convenio de pago).

        Called at premise signing, AFTER the order is confirmed and the final
        due dates are set on every line. Each invoice gets invoice_date_due =
        the agreed date; the existing WA/email reminder infra and Glenda
        balance queries then track them with no extra code.
        """
        self.ensure_one()
        if self.state != 'sale':
            raise UserError(_(
                "Confirme la cotización primero (al momento de la firma del "
                "convenio en la institución)."))
        if self.invoice_ids.filtered(lambda m: m.state != 'cancel'):
            raise UserError(_(
                "Esta orden ya tiene facturas generadas. Anule el plan "
                "existente antes de regenerarlo."))
        plan_lines = self.order_line.filtered(lambda l: not l.display_type)
        missing = plan_lines.filtered(lambda l: not l.ueipab_payment_due_date)
        if missing:
            raise UserError(_(
                "Faltan fechas de pago acordadas en: %s. Las fechas "
                "definitivas se establecen al firmar el convenio.")
                % ', '.join(missing.mapped('product_id.name')))

        groups = {}
        for line in plan_lines:
            groups.setdefault(line.ueipab_payment_due_date,
                              self.env['sale.order.line'])
            groups[line.ueipab_payment_due_date] |= line

        moves = self.env['account.move']
        for due_date in sorted(groups):
            lines = groups[due_date]
            moves |= self.env['account.move'].create({
                'move_type': 'out_invoice',
                'partner_id': self.partner_id.id,
                'currency_id': self.currency_id.id,
                'invoice_origin': self.name,
                'invoice_date_due': due_date,
                'invoice_payment_term_id': False,
                'narration': UEIPAB_BCV_NOTE,
                'invoice_line_ids': [(0, 0, {
                    'product_id': l.product_id.id,
                    'name': l.name,
                    'quantity': l.product_uom_qty,
                    'price_unit': l.price_unit,
                    'tax_ids': [(6, 0, l.tax_id.ids)],
                    'sale_line_ids': [(6, 0, [l.id])],
                }) for l in lines],
            })

        _logger.info(
            "ueipab_sales: payment plan %s — %d invoices (%s) total %.2f",
            self.name, len(moves),
            ', '.join(str(d) for d in sorted(groups)),
            sum(moves.mapped('amount_total')))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Plan de Pagos %s') % self.name,
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', moves.ids)],
        }

    # ── Enrollment quote engine ──────────────────────────────────────────────

    @api.model
    def _ueipab_llamado_for_date(self, on_date=None):
        """Return the llamado dict active on `on_date` (default today).

        Before the first window -> first window (early quote).
        After the last window  -> last window pricing (regular).
        """
        on_date = on_date or fields.Date.context_today(self)
        for llamado in UEIPAB_LLAMADOS:
            if on_date <= llamado['end']:
                return llamado
        return UEIPAB_LLAMADOS[-1]

    @api.model
    def _ueipab_product_by_code(self, code):
        product = self.env['product.product'].search(
            [('default_code', '=', code)], limit=1)
        if not product:
            raise UserError(_(
                "Producto de inscripción no encontrado: %s. "
                "Ejecute el script de catálogo ueipab_sales.") % code)
        return product

    @api.model
    def create_ai_quote(self, partner_id, n_students, channel='telegram'):
        """Create an enrollment quotation for `partner_id` with `n_students`.

        Called by the Glenda AI agent (ACTION:QUOTE) — and usable from the
        shell / XML-RPC. Prices come 100% from product records; the active
        llamado is resolved from today's date.

        Returns a summary dict (order id/name, llamado, lines, total,
        portal URL) so the caller can build the customer message verbatim.
        """
        n_students = max(1, int(n_students))
        partner = self.env['res.partner'].browse(int(partner_id))
        if not partner.exists():
            raise UserError(_("Contacto no encontrado (id=%s).") % partner_id)

        llamado = self._ueipab_llamado_for_date()
        men_code = llamado['men'][min(n_students, 4)]
        line_codes = ([llamado['ins'], men_code]
                      + ['SEG2627', llamado['ing'], 'OLI2627', 'ENC2627'])

        order_lines = []
        for code in line_codes:
            product = self._ueipab_product_by_code(code)
            order_lines.append((0, 0, {
                'product_id': product.id,
                'product_uom_qty': n_students,
            }))

        order = self.create({
            'partner_id': partner.id,
            'is_glenda_quote': True,
            'quote_channel': channel,
            'order_line': order_lines,
            'validity_date': llamado['end'],
            'require_signature': False,   # read-only portal (phase 1)
            'require_payment': False,
            'note': UEIPAB_BCV_NOTE,
        })
        order._portal_ensure_token()

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        lines = [{
            'code': l.product_id.default_code,
            'name': l.product_id.name,
            'qty': l.product_uom_qty,
            'price_unit': l.price_unit,
            'subtotal': l.price_subtotal,
        } for l in order.order_line]

        _logger.info(
            "ueipab_sales: AI quote %s created — partner=%s students=%s "
            "llamado=%s total=%.2f channel=%s",
            order.name, partner.name, n_students, llamado['code'],
            order.amount_total, channel)

        return {
            'order_id': order.id,
            'name': order.name,
            'llamado_code': llamado['code'],
            'llamado_name': llamado['name'],
            'convenio': llamado['convenio'],
            'validity_date': str(order.validity_date),
            'n_students': n_students,
            'lines': lines,
            'amount_total': order.amount_total,
            'currency': order.currency_id.name,
            'bcv_note': UEIPAB_BCV_NOTE,
            'portal_url': base_url + order.get_portal_url(),
        }
