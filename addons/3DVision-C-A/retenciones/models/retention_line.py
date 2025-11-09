from odoo import fields, api, models, _
from odoo.exceptions import UserError
from functools import partial
import re

INVOICE_DOMAIN = """[
    ('company_id','=',company_id),
    ('move_type','in',['in_invoice','in_refund'] if partner_type == 'vendor' else ['out_invoice','out_refund']),
    ('partner_id','=',partner_id),
    ('state','in',['posted','reversed']),
    ('id','not in', existing_invoice_ids)
]"""

IAE_TYPES = [
    ("none", ""),
    ("S", "Service"),
    ("C", "Purchase"),
]

REGISTRY_TYPES = [
    ("01", "01 - Invoice"),
    ("02", "02 - Debit Note"),
    ("03", "03 - Credit Note"),
]


class RetentionLine(models.Model):
    _name = "retention.line"
    _description = "Retention lines"

    retention_id = fields.Many2one("retention", "Retention")
    company_id = fields.Many2one(related="retention_id.company_id", store=True)
    state = fields.Selection(related="retention_id.state")
    type = fields.Selection(related="retention_id.type")
    partner_type = fields.Selection(related="retention_id.partner_type")
    partner_id = fields.Many2one(related="retention_id.partner_id", store=True)
    registry_type = fields.Selection(REGISTRY_TYPES, "Registry Type")
    @api.model
    def _get_invoice_domain(self):
        # Excluir facturas ya asociadas a una retención confirmada del mismo tipo y período
        confirmed_lines = self.env['retention.line'].search([
            ('retention_id.state', '=', 'posted'),
            ('retention_id.type', '=', self.retention_id.type if self.retention_id else False),
            ('retention_id.period', '=', self.retention_id.period if self.retention_id else False),
        ])
        confirmed_invoice_ids = confirmed_lines.mapped('invoice_id').ids
        domain = [
            ('company_id', '=', self.company_id.id if self.company_id else False),
            ('move_type', 'in', ['in_invoice', 'in_refund'] if self.partner_type == 'vendor' else ['out_invoice', 'out_refund']),
            ('state', 'in', ['posted', 'reversed']),
            ('id', 'not in', confirmed_invoice_ids),
        ]
        return domain

    invoice_id = fields.Many2one(
        comodel_name="account.move",
        string="Invoice",
        domain=INVOICE_DOMAIN,
        required=True
    )
    invoice_ref = fields.Char(
        related="invoice_id.fiscal_correlative",
        readonly=False
    )
    control_number = fields.Char(
        related="invoice_id.control_number",
        readonly=False,
    )
    ret_tax_id = fields.Many2one(
        "retention.tax", "Retention Tax", domain="[('type','=',type)]"
    )
    currency_id = fields.Many2one(related="retention_id.currency_id")
    amount_base = fields.Monetary("Untaxed", currency_field="currency_id")
    amount_untaxed = fields.Monetary("Tax Free", currency_field="currency_id")
    amount_tax = fields.Monetary("Tax", currency_field="currency_id")
    amount_total = fields.Monetary("Total", currency_field="currency_id")
    amount_subtracting = fields.Monetary(
        string="Subtracting",
        currency_field="currency_id",
        compute="_compute_amount_detained",
        store=True,
    )
    amount_detained_manual = fields.Monetary(
        string="Detained (manual)",
        currency_field="currency_id",
        help="Override manual del monto retenido. Solo aplica en borrador.",
        default=0.0,
    )
    amount_detained = fields.Monetary(
        string="Detained",
        currency_field="currency_id",
        compute="_compute_amount_detained",
        inverse="_inverse_amount_detained",
        store=True,
    )
    reversed_entry_id = fields.Many2one(related='invoice_id.reversed_entry_id')
    existing_invoice_ids = fields.Many2many(
        comodel_name="account.move",
        compute="_compute_existing_invoice_ids"
    )
    iae_type = fields.Selection(
        related="invoice_id.iae_type",
        readonly=False,
        store=True
    )
    move_id = fields.Many2one("account.move", "Journal Entry")

    @api.depends("retention_id")
    def _compute_existing_invoice_ids(self):
        for line in self:
            line.existing_invoice_ids = line.retention_id.line_ids.invoice_id

    @api.onchange("invoice_id", "currency_id")
    def onchange_invoice_or_currency(self):
        def _convert(amount):
            return self.invoice_id.currency_id._convert(
                from_amount=amount,
                to_currency=self.currency_id,
                company=self.company_id,
                date=self.invoice_id.invoice_date,
                round=True
            )

        if not self.invoice_id:
            return

        lines_amount_untaxed = sum(
            self.invoice_id.invoice_line_ids.filtered_domain(
                [("tax_ids.name", "ilike", "EXENTO")]
            ).mapped("price_total")
        )

        sign = 1

        if self.invoice_id.is_credit_note:
            self.registry_type = "03"
            sign = -1
        elif self.invoice_id.is_debit_note:
            self.registry_type = "02"
        else:
            self.registry_type = "01"

        self.amount_base = sign * \
            _convert(self.invoice_id.amount_untaxed - lines_amount_untaxed)
        self.amount_untaxed = sign * _convert(lines_amount_untaxed)
        self.amount_tax = sign * _convert(self.invoice_id.amount_tax)
        self.amount_total = sign * _convert(self.invoice_id.amount_total)

    @api.depends(
        "amount_base",
        "amount_untaxed",
        "amount_tax",
        "amount_total",
        "ret_tax_id",
        "retention_id.is_legal_entity",
    )
    def _compute_amount_detained(self):
        for line in self:
            def _percentage(amount):
                return amount * line.ret_tax_id.tax / 100

            line.amount_subtracting = line.ret_tax_id.currency_id._convert(
                from_amount=line.ret_tax_id.decrement,
                to_currency=line.currency_id,
                company=line.company_id or self.env.company,
                date=line.retention_id.date or fields.date.today(),
                round=True
            )

            computed_detained = _percentage(
                (line.amount_base + line.amount_untaxed)
                if line.retention_id.type != "iva"
                else line.amount_tax
            )

            # Usar override manual solo en borrador
            if line.state == 'draft' and line.amount_detained_manual:
                line.amount_detained = line.amount_detained_manual
            else:
                line.amount_detained = computed_detained

            if line.type == "islr" and not line.retention_id.is_legal_entity:
                sign = -1 if line.registry_type == "01" else 1

                line.amount_detained += (sign * line.amount_subtracting) \
                    if abs(line.amount_detained) > abs(line.amount_subtracting) \
                    else (-line.amount_detained)

    def _inverse_amount_detained(self):
        for line in self:
            # Solo permitir editar en borrador; persistir en el campo manual
            if line.state == 'draft':
                line.amount_detained_manual = line.amount_detained

    def _get_move_lines_data(self, credit_account, debit_account, currency):
        def _convert(amount, currency=None):
            return self.currency_id._convert(
                from_amount=amount,
                to_currency=currency or self.company_id.currency_id,
                company=self.company_id,
                date=self.retention_id.date,
                round=True
            )

        amount_currency = _convert(abs(self.amount_detained), currency)
        balance = _convert(abs(self.amount_detained))

        # Ajuste: para clientes, el monto va como crédito (ganancia para la empresa)
        if self.partner_type == 'customer':
            debit_line = {
                "account_id": debit_account.id,  # Cuenta de retención de cliente
                "partner_id": self.partner_id.id,
                "currency_id": currency.id,
                "amount_currency": amount_currency,  # Positivo para débito
                "debit": balance,
                "credit": 0.0,
            }
            credit_line = {
                "account_id": credit_account.id,  # Cuenta por cobrar del cliente
                "partner_id": self.partner_id.id,
                "currency_id": currency.id,
                "amount_currency": -amount_currency,  # Negativo para crédito
                "debit": 0.0,
                "credit": balance,
            }
        else:
            # Para proveedores, el monto va como débito (pasivo para la empresa)
            debit_line = {
                "account_id": debit_account.id,
                "partner_id": self.partner_id.id,
                "currency_id": currency.id,
                "amount_currency": amount_currency,  # Positivo para débito
                "debit": balance,
                "credit": 0.0,
            }
            credit_line = {
                "account_id": credit_account.id,
                "partner_id": self.partner_id.id,
                "currency_id": currency.id,
                "amount_currency": -amount_currency,  # Negativo para crédito
                "debit": 0.0,
                "credit": balance,
            }

        return debit_line, credit_line

    def _create_account_move(self):
        credit_account = (
            self.retention_id.credit_account_id
            or self.company_id._get_retention_account_id(self.type, self.partner_type)
        )
        debit_account = (
            self.retention_id.debit_account_id
            or (
                self.partner_id.property_account_receivable_id
                if self.partner_type == 'customer'
                else self.partner_id.property_account_payable_id
            )
        )
        currency = self.retention_id.journal_currency or self.currency_id

        if self.partner_type == 'customer':
            credit_account, debit_account = debit_account, credit_account

        if self.amount_detained < 0:
            credit_account, debit_account = debit_account, credit_account

        if not self.move_id:
            self.move_id = self.env["account.move"].create(
                {
                    "ref": _(
                        "%s retention on %s (%s)"
                        % (
                            self.type.upper(),
                            self.invoice_id.name,
                            self.retention_id.name,
                        )
                    ),
                    "company_id": self.company_id.id,
                    "journal_id": self.retention_id.journal_id.id,
                    "currency_id": currency.id,
                    "date": self.retention_id.date,
                    "partner_id": self.partner_id.id,
                    "line_ids": [
                        (0, 0, line)
                        for line in self._get_move_lines_data(
                            credit_account, debit_account, currency
                        )
                    ],
                }
            )

        self.move_id.action_post()
        return True

    def _cancel_move(self):
        self.move_id.button_cancel()
        return True

    def _draft_move(self):
        self.move_id.button_draft()
        return True

    def get_text_info(self):
        sanitize = partial(re.sub, pattern=r"[-_.,#\\]", repl="")
        company_vat = self.company_id.company_registry or self.company_id.vat
        partner_vat = self.partner_id.vat or self.partner_id.ced_rif
        r_correlative = None

        if self.reversed_entry_id:
            r_correlative = self.reversed_entry_id.fiscal_correlative

        if self.type == "iva":
            text_format = "\t".join(
                [
                    sanitize(string=company_vat),
                    self.retention_id.period,
                    self.invoice_id.invoice_date.strftime("%Y-%m-%d"),
                    "C",
                    self.registry_type,
                    sanitize(string=partner_vat),
                    sanitize(string=self.invoice_ref),
                    sanitize(string=self.control_number),
                    str(abs(round(self.amount_total, 2))),
                    str(abs(round(self.amount_base, 2))),
                    str(abs(round(self.amount_detained, 2))),
                    sanitize(string=r_correlative or "0"),
                    sanitize(string=self.retention_id.correlative),
                    str(abs(round(self.amount_untaxed, 2))),
                    "16",
                    "0",
                ]
            )
        else:
            document_type = {"01": "FT", "02": "ND", "03": "NC"}
            text_format = "\t".join(
                [
                    self.retention_id.company_id.taxpayer_license,
                    company_vat,
                    self.retention_id.period[:4],
                    self.retention_id.period[4:6],
                    partner_vat,
                    self.iae_type,
                    self.retention_id.date.strftime("%d/%m/%Y"),
                    self.invoice_ref,
                    self.control_number,
                    document_type.get(self.registry_type),
                    self.partner_id.taxpayer_license,
                    r_correlative or "NA",
                    "NA",
                    self.retention_id.correlative,
                    str(abs(round(self.amount_base + self.amount_untaxed, 2))),
                    str(abs(round(self.ret_tax_id.tax, 2))),
                    self.ret_tax_id.code,
                    str(abs(self.amount_detained)),
                    self.retention_id.partner_id.ruc or "NA",
                ]
            )

        return text_format

# TODO: Per invoice in retention lines
# _sql_constraints = [ ('unique_product_per_invoice', 'unique(move_id, product_id)', 'Cada producto debe ser único en la factura.') ]
