from odoo import fields, models
from odoo.exceptions import UserError


class BatchCommissionsWizard(models.TransientModel):
    _name = "batch.commission.assign.wizard"
    _description = "to manage many assignment"

    partner_to_assign = fields.Many2one(string="To assign", comodel_name="res.partner")

    def confirm_action(self):
        context = self.env.context
        if not self.partner_to_assign:
            raise UserError("Please select a partner to continue")

        if not self.partner_to_assign.has_commissions:
            raise UserError("The partner must to have commissions enabled")

        if context.get("active_model") == "account.move":
            lines = self.env["account.move.line"].search(
                [
                    ("move_id", "=", context.get("active_id")),
                    ("product_id", "!=", False),
                ]
            )
            lines.write({"commission_partner_id": self.partner_to_assign.id})
