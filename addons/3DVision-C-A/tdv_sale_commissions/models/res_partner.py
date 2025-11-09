from odoo import fields, models

GENERATION_MODE = [
    ("total", "Totally Paid"),
    ("partial", "Partially Paid"),
    ("sale", "On Sale"),
]


class ResPartner(models.Model):
    _inherit = "res.partner"

    sale_commission_partner = fields.Many2one(
        string="Vendedor para comisiones", comodel_name="res.partner"
    )
    sale_commission_rate = fields.Float("Sale Commission Rate")
    service_commission_rate = fields.Float("Service Commission Rate")
    has_commissions = fields.Boolean("Has Commissions")
    generation_mode = fields.Selection(
        string="Mode", selection=GENERATION_MODE, required=True, default="total"
    )
    special_commission_rate = fields.One2many(
        comodel_name="special.commission.rate", inverse_name="partner_id"
    )

    def _get_special_rate_by_partner(self, partner_id):
        self.ensure_one()
        return self.special_commission_rate.filtered(
            lambda x: x.related_partner.id == partner_id.id
        )

    def get_service_rate_by_partner(self, partner_id):
        rate = self._get_special_rate_by_partner(partner_id)
        if rate:
            return rate[0].service_rate
        return self.service_commission_rate

    def get_sale_rate_by_partner(self, partner_id):
        rate = self._get_special_rate_by_partner(partner_id)
        if rate:
            return rate[0].sale_rate
        return self.sale_commission_rate
