from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def set_commission_partner(self):
        return {
            "name": "Set commission partner",
            "type": "ir.actions.act_window",
            "view_type": "form",
            "view_mode": "form",
            "res_model": "batch.commission.assign.wizard",
            "target": "new",
            "context": self.env.context,
        }

    def update_commissions(self):
        for invoice in self:
            move_lines = invoice.line_ids.filtered(lambda line: not line.commission_partner_id)

            for line in move_lines:
                if invoice.invoice_user_id and invoice.invoice_user_id.has_commissions:
                    line.commission_partner_id = invoice.invoice_user_id.partner_id

        return True