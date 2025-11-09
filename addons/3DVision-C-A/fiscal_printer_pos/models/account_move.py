# -*- coding: utf-8 -*-

from odoo import models, api
from odoo.exceptions import UserError
import json


class AccountMoveInherit(models.Model):
    _inherit = "account.move"

    @api.model
    def tdv_calculate_payments(self, invoice):
        payments = super().tdv_calculate_payments(invoice)
        for item in (invoice.invoice_payments_widget or {}).get("content", []):
            pos_payment = item.get("pos_payment_name", False)
            if pos_payment:
                pos_payment_method = self.env["pos.payment.method"].search(
                    [("name", "like", pos_payment)]
                )
                if not pos_payment_method:
                    raise UserError(
                        "Hay un error con los metodos de pago del punto de venta"
                    )

                for payment_method in pos_payment_method:
                    if (
                        not payment_method.journal_id
                        or not payment_method.journal_id.fp_payment_method
                    ):
                        raise UserError(
                            "Los medios de pago de la impresora fiscal deben estar configurados en los diarios"
                        )
                    payments.append(
                        {
                            "name": payment_method.journal_id.name,
                            "id": payment_method.journal_id.id,
                            "fp_type": payment_method.journal_id.fp_payment_method,
                            "type": invoice.get_payment_type_for_fiscal_printer(),
                            "amount": payment_method.company_id.convert_to_fiscal_currency(
                                item.get("amount"), invoice.currency_id
                            ),
                        }
                    )
                    break
        return payments

    def update_fp_fiscal_info(self, info):
        result = super().update_fp_fiscal_info(info)
        result.fp_update_pos_order()
        return result

    def fp_update_pos_order(self):
        for move in self:
            for order in move.pos_order_ids:
                if move.ticket_ref:
                    order.write(
                        {
                            "num_factura": move.ticket_ref,
                            "fiscal_serial": move.fp_serial_num,
                            "fiscal_date": move.fp_serial_date,
                        }
                    )
