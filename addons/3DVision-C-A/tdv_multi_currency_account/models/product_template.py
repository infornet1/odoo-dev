from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    ref_currency_id = fields.Many2one(
        "res.currency",
        "Reference Currency",
        default=lambda self: self.env.company.second_currency_id,
        store=True,
    )
    ref_list_price = fields.Monetary(
        "Reference Price",
        currency_field="ref_currency_id",
        compute="_compute_ref_list_price",
        inverse="_inverse_ref_list_price",
        store=True,
    )
    ref_standard_price = fields.Monetary(
        "Reference Cost",
        currency_field="ref_currency_id",
        compute="_compute_ref_standard_price",
        inverse="_inverse_ref_standard_price",
        store=True,
    )

    fixed_price = fields.Boolean("Fixed Price", default=False)

    def _convert_amount(self, amount, from_currency, to_currency):
        return from_currency._convert(
            from_amount=amount,
            to_currency=to_currency,
            company=self.company_id or self.env.company,
            date=fields.Date.today(),
            round=True,
        )


    @api.depends("list_price")
    def _compute_ref_list_price(self):
        for product in self:
            product.ref_list_price = product._convert_amount(
                amount=product.list_price,
                from_currency=product.currency_id,
                to_currency=product.ref_currency_id,
            )

    @api.depends("standard_price")
    def _compute_ref_standard_price(self):
        for product in self:
            product.ref_standard_price = product._convert_amount(
                amount=product.standard_price,
                from_currency=product.currency_id,
                to_currency=product.ref_currency_id,
            )

    @api.onchange("ref_list_price")
    def _inverse_ref_list_price(self):
        for product in self:
            product.list_price = product._convert_amount(
                amount=product.ref_list_price,
                from_currency=product.ref_currency_id,
                to_currency=product.currency_id,
            )

    @api.onchange("ref_standard_price")
    def _inverse_ref_standard_price(self):
        for product in self:
            product.standard_price = product._convert_amount(
                amount=product.ref_standard_price,
                from_currency=product.ref_currency_id,
                to_currency=product.currency_id,
            )


    @api.onchange("standard_price", "list_price")
    def _check_button(self):
        if self.standard_price > self.list_price:
            return {
                "warning": {
                    "title": "ADVERTENCIA",
                    "message": "El Costo del producto es mayor que el precio de venta",
                }
            }

    @api.model
    def _get_update_price_domain(self,product_ids):
        domain= [("fixed_price", "=", False)]

        if product_ids:
            domain = [("id", "in", product_ids)]

        return domain

    @api.model
    def update_price(self,product_ids):
        domain = self._get_update_price_domain(product_ids)

        for product in self.env["product.template"].search(domain):
            product.currency_id = product.currency_id or self.env.company.currency_id
            product.ref_currency_id = product.ref_currency_id or self.env.company.second_currency_id

            if self.env.company.fixed_ref:
                product._inverse_ref_list_price()

                if self.env.company.product_cost_updatable:
                    product._inverse_ref_standard_price()
            else:
                product._compute_ref_list_price()

                if self.env.company.product_cost_updatable:
                    product._compute_ref_standard_price()

        return True

