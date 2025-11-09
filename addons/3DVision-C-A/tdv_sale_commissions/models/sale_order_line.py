from odoo import fields, models, api


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    commission_partner_id = fields.Many2one("res.partner", string="Commission")

    def _prepare_invoice_line(self, **optional_values):
        res = super()._prepare_invoice_line(**optional_values)
        if self.commission_partner_id:
            res.update(
                {
                    "commission_partner_id": self.commission_partner_id.id,
                }
            )
        return res

    @api.model
    def create(self, *args, **kwargs):
        result = super().create(*args, **kwargs)
        for record in result:
            if not record.commission_partner_id:
                partner_user_id = record.order_id.partner_id.sale_commission_partner
                if partner_user_id:
                    record.write(
                        {
                            "commission_partner_id": partner_user_id.id,
                        }
                    )
        return result
