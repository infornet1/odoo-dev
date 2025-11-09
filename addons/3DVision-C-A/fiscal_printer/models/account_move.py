from odoo import fields, models, api
from odoo.exceptions import UserError

FP_STATES = [
    ("none", ""),
    ("to_print", "Para Imprimir"),
    ("to_reprint", "Para Reimprimir"),
    ("sent", "En cola de impresion"),
    ("printed", "Impreso"),
]


class AccountMove(models.Model):
    _inherit = "account.move"

    ticket_ref = fields.Char("Referencia de ticket", default=0, readonly=True)
    cn_ticket_ref = fields.Char(
        "Referencia de ticket (CN)", default=0, readonly=True
    )
    num_report_z = fields.Char(
        "Numero de Reporte Z", default=0, readonly=True, copy=False
    )
    fp_serial_num = fields.Char("Numero Serial FP", default="", readonly=True)
    fp_serial_date = fields.Char("Fecha de la factura fiscal", readonly=True)
    fp_state = fields.Selection(
        FP_STATES, "Estado Factura Fiscal", default="none", copy=False
    )
    fp_internal_reference = fields.Integer(
        "Referencia interna Fiscal",
        compute="_compute_fp_internal_reference",
        store=True,
    )

    fp_total_amount = fields.Float(
        string="total fiscal currency", compute="_compute_fp_total_amount"
    )
    has_same_fp_group = fields.Boolean(
        string="has same fiscal group", compute="_compute_has_same_fp_group"
    )

    @api.model
    def get_last_invoice_number(self, company_id):
        return self.env["account.move"].search(
            [
                ("state", "=", "posted"),
                ("company_id", "=", company_id),
                ("move_type", "=", "out_invoice"),
                ("ticket_ref", "!=", 0),
            ],
            order="id desc",
            limit=1,
        ).ticket_ref

    @api.model
    def get_last_cn_invoice_number(self, company_id):
        return self.env["account.move"].search(
            [
                ("state", "=", "posted"),
                ("company_id", "=", company_id),
                ("move_type", "=", "out_refund"),
                ("cn_ticket_ref", "!=", 0),
            ],
            order="id desc",
            limit=1,
        ).cn_ticket_ref

    @api.depends("user_id")
    def _compute_has_same_fp_group(self):
        for record in self:
            user = self.env.user
            if user.fp_fiscal_group_id:
                record.has_same_fp_group = (
                    record.user_id.fp_fiscal_group_id == user.fp_fiscal_group_id
                )
            else:
                record.has_same_fp_group = False

    @api.depends("company_id", "amount_total", "currency_id")
    def _compute_fp_total_amount(self):
        for record in self:
            if record.company_id and record.amount_total and record.currency_id:
                record.fp_total_amount = record.company_id.convert_to_fiscal_currency(
                    record.amount_total, record.currency_id
                )
            else:
                record.fp_total_amount = 0

    @api.depends("name")
    def _compute_fp_internal_reference(self):
        for record in self:
            record.fp_internal_reference = record.id

    def send_to_fiscal_printer(self):
        """Send invoice to fiscal printer"""
        self.ensure_one()

        # Get the fiscal printer from company configuration
        fiscal_printer = self.company_id.fiscal_printer_id
        if not fiscal_printer:
            raise UserError(
                "No se ha configurado una impresora fiscal para esta empresa")

        # Get formatted invoice data
        invoice_data = self.get_fp_formated_invoice()
        if not invoice_data:
            raise UserError("No se pudo obtener los datos de la factura")

        # Return client action to print invoice
        return {
            'type': 'ir.actions.client',
            'tag': 'fiscal_printer_invoice',
            'params': {
                'printer_id': fiscal_printer.id,
                'invoice_data': invoice_data[0] if invoice_data else {},
                'res_model': self._name,
                'res_id': self.id,
                'serial_port': fiscal_printer.serial_port,
                'connection_type': fiscal_printer.connection_type,
                'api_url': fiscal_printer.api_url,
                'usb_vendor_id': fiscal_printer.usb_vendor_id,
                'usb_product_id': fiscal_printer.usb_product_id,
                'flag_21': fiscal_printer.flag_21,
                'flag_50': fiscal_printer.flag_50,
                'flag_63': fiscal_printer.flag_63,
            }
        }

    def get_payment_type_for_fiscal_printer(self):
        self.ensure_one()
        if self.move_type == "out_invoice":
            return "inbound"
        elif self.move_type == "out_refund":
            return "outbound"

    @api.model
    def tdv_calculate_payments(self, invoice):
        payments = []
        for item in (invoice.invoice_payments_widget or {}).get("content", []):
            pos_payment = item.get("pos_payment_name", False)
            if not pos_payment:
                if item.get("igtf_payment_model") == "account.move":
                    payment = self.env["account.move"].search(
                        [("id", "in", item.get("account_payment_id"))]
                    )
                    for fp in payment:
                        payments.append(
                            {
                                "name": fp.journal_id.name,
                                "id": fp.journal_id.id,
                                "fp_type": fp.journal_id.fp_payment_method,
                                "type": fp.get_payment_type_for_fiscal_printer(),
                                "amount": fp.company_id.convert_to_fiscal_currency(
                                    item.get("amount"), invoice.currency_id
                                ),
                            }
                        )
                else:
                    payment = self.env["account.payment"].search(
                        [("id", "=", item.get("account_payment_id"))]
                    )
                    for fp in payment:
                        payments.append(
                            {
                                "name": fp.journal_id.name,
                                "id": fp.journal_id.id,
                                "fp_type": fp.journal_id.fp_payment_method,
                                "type": fp.payment_type,
                                "amount": fp.company_id.convert_to_fiscal_currency(
                                    item.get("amount"), invoice.currency_id
                                ),
                            }
                        )
        return sorted(payments, key=lambda x: x.get("fp_type"), reverse=True)

    @api.model
    def tdv_get_payments(self, invoice):
        fp_amount_total = invoice.fp_total_amount
        payments = self.tdv_calculate_payments(invoice)
        payments_total = sum(payment.get("amount") for payment in payments)
        if payments_total < fp_amount_total:
            payments.append(
                {
                    "name": "CREDITO",
                    "id": 2,
                    "fp_type": "m11",
                    "type": "inbound"
                    if invoice.move_type == "out_invoice"
                    else "outbound",
                    "amount": fp_amount_total - payments_total,
                }
            )

        return payments

    def get_reversed_name(self):
        self.ensure_one()
        if self.reversed_entry_id:
            return self.reversed_entry_id.id
        return 0

    def get_fp_invoice_lines(self):
        return self.invoice_line_ids

    def get_fp_formated_invoice(self):
        response = []
        for record in self:
            if record.has_same_fp_group:
                response.append(
                    {
                        "name": record.name,
                        "id": record.id,
                        "ticket_ref": record.ticket_ref,
                        "num_report_z": record.num_report_z,
                        "cn_ticket_ref": record.cn_ticket_ref,
                        "fp_serial_num": record.fp_serial_num,
                        "fp_serial_date": record.fp_serial_date or "",
                        "type": record.move_type,
                        "action_type": record.fp_state,
                        "reversed": record.get_reversed_name(),
                        "partner_id": record.partner_id.get_fiscal_info_json(),
                        "payment": self.tdv_get_payments(record),
                        "payment_state": record.payment_state,
                        "invoice_line_ids": record.get_fp_invoice_lines().get_fiscal_info_json(),
                        "amount_total": record.fp_total_amount,
                    }
                )
        return response

    def tdv_fp_get_invoices(self, debug=False):
        records = self.env["account.move"].search(
            [
                ("fp_state", "=", "to_print"),
                ("state", "=", "posted"),
                ("company_id", "in", self.env.user.company_ids.mapped("id")),
            ]
        )

        invoices = records.get_fp_formated_invoice()
        if records and not debug:
            records.write({"fp_state": "sent"})
        return invoices

    @api.model
    def _tdv_validate_info(self, invoice={}):
        if not (
            invoice
            and (
                type(invoice["ticket_ref"]) == int
                and type(invoice["num_report_z"]) == int
                and type(invoice["fp_serial_num"] == str)
            )
        ):
            raise Exception("Validation Error")
        return True

    def tdv_fp_update_invoices(self, info=[], **kwargs):
        res = {}
        account_moves = self.env["account.move"].search(
            [("id", "in", [invoice.get("id") for invoice in info])]
        )
        for invoice in info:
            to_update = account_moves.filtered_domain(
                [("id", "=", invoice.get("id"))])
            try:
                if self._tdv_validate_info(invoice) and to_update:
                    to_update.update_fp_fiscal_info(
                        {"fp_state": "printed", **invoice})
                    res.update({str(invoice.get("id")): "Success"})
                else:
                    res.update({str(invoice.get("id")): "Failed"})
            except Exception as e:
                res.update({str(invoice.get("id")): str(e)})
        return res

    def update_fp_fiscal_info(self, info):
        self.write(info)
        return self
