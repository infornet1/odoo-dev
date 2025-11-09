# -*- coding: utf-8 -*-

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    ced_rif = fields.Char(
        string="CEDULA/RIF",
        help="""
        Requerido para generar los tickets,
        en caso de ser RIF completar 10 digitos con ceros a la izquierda
    """,
    )

    def get_fiscal_info_json(self):
        self.ensure_one()
        return {
            "name": self.name,
            "id": self.id,
            "street": self.street or "",
            "phone": self.phone or "",
            "email": self.email or "",
            "vat": (self.ced_rif or self.vat) or "0123456789",
        }
