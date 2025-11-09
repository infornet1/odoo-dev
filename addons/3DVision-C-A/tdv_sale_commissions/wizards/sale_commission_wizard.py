from odoo import fields, models, api
from odoo.exceptions import UserError
import json


class SaleCommissionWizard(models.TransientModel):
    _name = "sale.commission.wizard"
    _description = "sale.commission.wizard"

    from_date = fields.Date("From Date")
    to_date = fields.Date("To Date")

    @api.model
    def create(self, *args, **kwargs):
        result = super(SaleCommissionWizard, self).create(*args, **kwargs)
        return result

    def generate_sale_commissions(self):
        moves = self.env["account.move"].search(
            [
                # ("create_date", ">=", self.from_date),
                ("create_date", "<=", self.to_date),
                ("move_type", "in", ["out_invoice"]),
                ("state", "=", "posted"),
                ("company_id", "=", self.env.company.id),
            ]
        )
        commissions = []
        for record in moves:
            payments = record.invoice_payments_widget or {}
            lines = record.invoice_line_ids.filtered("commission_partner_id")
            client = record.partner_id
            for line in lines:
                partner = line.commission_partner_id
                sale_rate = partner.get_sale_rate_by_partner(client)
                service_rate = partner.get_service_rate_by_partner(client)
                if (
                    partner.generation_mode == "total"
                    and line.move_id.payment_state in ["paid", "in_payment"]
                ) or partner.generation_mode == "sale":
                    if line.commission_line_ids:
                        continue
                    commissions.append(
                        {
                            "move_line_id": line.id,
                            "product_id": line.product_id.id,
                            "partner_id": partner.id,
                            "service_percent": service_rate,
                            "payment_mode": partner.generation_mode,
                            "sale_percent": sale_rate,
                        }
                    )
                elif partner.generation_mode == "partial":
                    filtered_payments = filter(
                        lambda x: x.get("account_payment_id")
                        not in line.commission_line_ids.mapped("payment_id.id"),
                        payments.get("content", []) if payments else [],
                    )
                    for payment in filtered_payments:
                        commissions.append(
                            {
                                "move_line_id": line.id,
                                "product_id": line.product_id.id,
                                "partner_id": partner.id,
                                "service_percent": service_rate,
                                "sale_percent": sale_rate,
                                "payment_mode": partner.generation_mode,
                                "payment_amount": payment.get("amount")
                                / record.amount_total,
                                "payment_id": payment.get("account_payment_id"),
                            }
                        )
            for refunded_move in record.reversal_move_id:
                if refunded_move.state == "posted":
                    lines = refunded_move.invoice_line_ids.filtered(
                        "commission_partner_id"
                    )
                    client = refunded_move.partner_id
                    for line in lines:
                        partner = line.commission_partner_id
                        sale_rate = partner.get_sale_rate_by_partner(client)
                        service_rate = partner.get_service_rate_by_partner(client)
                        if line.commission_line_ids:
                            continue
                        commissions.append(
                            {
                                "move_line_id": line.id,
                                "product_id": line.product_id.id,
                                "partner_id": partner.id,
                                "service_percent": service_rate,
                                "payment_mode": "sale",
                                "sale_percent": sale_rate,
                            }
                        )
        return commissions

    def create_commissions(self):
        self.ensure_one()

        commissions = self.generate_sale_commissions()

        if not commissions:
            raise UserError("No pending commissions!")

        commission_order = self.env["tdv.sale.commission"].create(
            {
                "sale_commission_line_ids": [(0, 0, line) for line in commissions],
                "state": "draft",
                "from_date": self.from_date,
                "to_date": self.to_date,
                "name": f"{self.from_date} - {self.to_date}",
            }
        )

        return {
            "name": "Sale Commission",
            "type": "ir.actions.act_window",
            "res_model": "tdv.sale.commission",
            "res_id": commission_order.id,
            "view_mode": "form",
            "view_type": "form",
            "target": "current",
        }
