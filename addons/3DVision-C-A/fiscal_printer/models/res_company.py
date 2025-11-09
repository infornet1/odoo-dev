from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    fiscal_currency_id = fields.Many2one(
        "res.currency", string="Fiscal Currency")
    fiscal_group_ids = fields.One2many(
        "fp.fiscal.group", "company_id", string="Fiscal Group"
    )
    fiscal_printer_id = fields.Many2one(
        "x.pos.fiscal.printer", string="Impresora Fiscal por Defecto"
    )

    def convert_to_fiscal_currency(self, amount, from_currency):
        self.ensure_one()

        return round(
            from_currency._convert(
                from_amount=amount,
                to_currency=(self.fiscal_currency_id or self.currency_id),
                company=self,
                date=fields.datetime.now(),
            ),
            2,
        )
