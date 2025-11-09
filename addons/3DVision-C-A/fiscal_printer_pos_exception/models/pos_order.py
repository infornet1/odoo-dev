from odoo import models, fields, api
from odoo.exceptions import UserError


class PosOrder(models.Model):
    _inherit = 'pos.order'

    z_report = fields.Char(
        "Reporte Z", related="session_id.x_pos_z_report_number", store=True)

    num_report_z = fields.Char("Número de Reporte Z", store=True)
    num_factura = fields.Char("Num. Factura Fiscal", store=True)
    fiscal_date = fields.Date("Fecha fiscal", store=True)
    fiscal_serial = fields.Char("Serial fiscal", store=True)
    refund_num_factura = fields.Char(
        "Num. Factura Fiscal devuelta", store=True)
    refund_fiscal_date = fields.Date("Fecha fiscal devuelta", store=True)
    refund_fiscal_serial = fields.Char("Serial fiscal devuelto", store=True)

    def _prepare_invoice_vals(self):
        res = super()._prepare_invoice_vals()
        res.update({
            'ticket_ref': self.num_factura,
            'fp_serial_date': self.fiscal_date,
            'fp_serial_num': self.fiscal_serial,
            'cn_ticket_ref': self.refund_num_factura,
            'fp_state': 'printed',
            'num_report_z': self.num_report_z,
        })
        # Aqui van los datos de las facturas ya impresas
        return res

    @api.model
    def _order_fields(self, ui_order):
        order_fields = super(PosOrder, self)._order_fields(ui_order)
        order_fields['num_factura'] = ui_order.get('num_factura')
        order_fields['fiscal_date'] = ui_order.get('fiscal_date')
        order_fields['fiscal_serial'] = ui_order.get('fiscal_serial')
        order_fields['refund_num_factura'] = ui_order.get('refund_num_factura')
        order_fields['refund_fiscal_date'] = ui_order.get('refund_fiscal_date')
        order_fields['refund_fiscal_serial'] = ui_order.get(
            'refund_fiscal_serial')
        order_fields['num_report_z'] = ui_order.get('num_report_z')
        return order_fields

    def _export_for_ui(self, order):
        result = super(PosOrder, self)._export_for_ui(order)
        result.update({
            'num_factura': order.num_factura,
            'fiscal_date': order.fiscal_date,
            'fiscal_serial': order.fiscal_serial,
            'refund_num_factura': order.refund_num_factura,
            'refund_fiscal_date': order.refund_fiscal_date,
            'refund_fiscal_serial': order.refund_fiscal_serial,
            'num_report_z': order.num_report_z,
        })
        return result
