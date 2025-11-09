# -*- coding: utf-8 -*-

from odoo import models, fields, api

class PosOrder(models.Model):
    _inherit = 'pos.order'
    
    is_refund = fields.Boolean(
        string='Is Refund', 
        default=False, 
        help='Indicates if this order is a refund generated from the POS.'
    )
    
    @api.model
    def _order_fields(self, ui_order):
        order_fields = super(PosOrder, self)._order_fields(ui_order)
        
        if 'is_refund' in ui_order:
            order_fields['is_refund'] = ui_order.get('is_refund', False)
        
        return order_fields

    @api.model
    def create_from_ui(self, orders, draft=False):
        for order in orders:
            if 'extra_data' in order:
                if 'is_refund' in order['extra_data']:
                    order['is_refund'] = order['extra_data']['is_refund']
        return super().create_from_ui(orders, draft=draft)

    def _export_for_ui(self, order):
        result = super()._export_for_ui(order)
        result['is_refund'] = order.is_refund
        return result
