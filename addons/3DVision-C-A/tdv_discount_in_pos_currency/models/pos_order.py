from odoo import models, fields, api

class PosOrder(models.Model):
    _inherit = 'pos.order'

    discount_special_amount = fields.Float(string='Currency Discount (Ref)')
    currency_amount = fields.Float(string='Currency Amount', help='Amount in the selected currency for this order.')
    display_discount_currency_id = fields.Many2one(
        'res.currency',
        string='Currency for Discount/Ref',
        help='Currency used for the currency amount.'
    )
    currency_dynamic_id = fields.Many2one(
        'res.currency',
        string='Dynamic Currency',
        compute='_compute_currency_dynamic_id',
        store=False,
        help='Currency to use for display, based on POS config.'
    )
    currency_symbol = fields.Char(string='Currency Symbol', help='Symbol of the currency used for the currency amount.')
    display_currency_amount = fields.Char(
        string='Currency Amount Display',
        compute='_compute_display_currency_amount',
        store=False
    )
    is_refund = fields.Boolean(string='Es reembolso', default=False, help='Indica si esta orden es un reembolso generado desde el POS.')

    def _order_fields(self, ui_order):
        fields = super()._order_fields(ui_order)
        extra_data = ui_order.get('extra_data') or {}
        fields['discount_special_amount'] = ui_order.get('discount_special_amount', extra_data.get('discount_special_amount', 0))
        fields['currency_amount'] = ui_order.get('currency_amount', extra_data.get('currency_amount', 0))
        fields['display_discount_currency_id'] = ui_order.get('display_discount_currency_id', extra_data.get('display_discount_currency_id'))
        # Manejar is_refund desde el frontend
        fields['is_refund'] = ui_order.get('is_refund', extra_data.get('is_refund', False))
        # Assign the currency symbol as a string
        config_id = ui_order.get('config_id') or extra_data.get('config_id')
        if not config_id and self.env.context.get('pos_config_id'):
            config_id = self.env.context.get('pos_config_id')
        if not config_id:
            config = self.env['pos.config'].search([], limit=1)
        else:
            config = self.env['pos.config'].browse(config_id)
        currency = None
        if config and config.currency_discount_mode == 'secondary' and config.display_discount_currency_id:
            currency = config.display_discount_currency_id
        elif config:
            currency = config.currency_id
        fields['currency_symbol'] = currency.symbol if currency else ''
        return fields

    @api.depends('currency_id', 'display_discount_currency_id', 'config_id')
    def _compute_currency_dynamic_id(self):
        for rec in self:
            config = rec.config_id or self.env['pos.config'].search([], limit=1)
            if config and config.currency_discount_mode == 'secondary' and rec.display_discount_currency_id:
                rec.currency_dynamic_id = rec.display_discount_currency_id
            else:
                rec.currency_dynamic_id = rec.currency_id

    @api.depends('currency_symbol', 'currency_amount')
    def _compute_display_currency_amount(self):
        for rec in self:
            symbol = rec.currency_symbol or ''
            amount = rec.currency_amount or 0
            # Formato: separador de miles punto, decimales coma
            amount_str = f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            rec.display_currency_amount = f"{symbol} {amount_str}".strip()

    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None, load=True):
        # Fuerza que currency_amount siempre esté en los campos pedidos
        if fields and 'currency_amount' not in fields:
            fields.append('currency_amount')
        return super().search_read(domain, fields, offset, limit, order, load=load)

    def read(self, fields=None, load='_classic_read'):
        if fields and 'currency_amount' not in fields:
            fields.append('currency_amount')
        return super().read(fields=fields, load=load)

    @api.model
    def create_from_ui(self, orders, draft=False):
        for order in orders:
            if 'extra_data' in order:
                if 'discount_special_amount' in order['extra_data']:
                    order['discount_special_amount'] = order['extra_data']['discount_special_amount']
                if 'currency_amount' in order['extra_data']:
                    order['currency_amount'] = order['extra_data']['currency_amount']
                if 'display_discount_currency_id' in order['extra_data']:
                    order['display_discount_currency_id'] = order['extra_data']['display_discount_currency_id']
                if 'is_refund' in order['extra_data']:
                    order['is_refund'] = order['extra_data']['is_refund']
        return super().create_from_ui(orders, draft=draft)

    def _export_for_ui(self, order):
        result = super()._export_for_ui(order)
        result['currency_amount'] = order.currency_amount
        result['is_refund'] = order.is_refund
        return result 