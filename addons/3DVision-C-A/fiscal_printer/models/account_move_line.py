from odoo import models, fields, api


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    fp_price_unit = fields.Float(
        string="total line fiscal currency", compute="_compute_fp_price_unit"
    )

    @api.depends("company_id", "price_unit", "currency_id")
    def _compute_fp_price_unit(self):
        for record in self:
            if record.company_id and record.price_unit and record.currency_id:
                record.fp_price_unit = record.company_id.convert_to_fiscal_currency(
                    record.price_unit, record.currency_id
                )
            else:
                record.fp_price_unit = 0

    def get_fp_tax_num(self):
        self.ensure_one()

        move_type = self.move_id.move_type

        if move_type in ["out_invoice", "out_refund"]:
            tax = self.tax_ids.mapped("x_tipo_alicuota")
            if tax:
                return tax[0]
        return 0

    def get_fiscal_info_json(self):
        return [
            {
                "name": line.product_id.name or line.name,
                "price_unit": line.fp_price_unit * (1 - (line.discount / 100.0)),
                "product_qty": line.quantity,
                "tax_ids": line.get_fp_tax_num(),
                "base_price": line.fp_price_unit,
                "discount": line.discount,
            }
            for line in self
        ]
