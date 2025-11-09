from odoo import fields, api, models, _
from odoo.exceptions import UserError
from collections import defaultdict

IAE_TYPES = [("S", "Service"), ("C", "Purchase")]


class AccountMove(models.Model):
    _inherit = "account.move"

    retention_currency_id = fields.Many2one(
        "res.currency",
        "Retention Currency",
        default=lambda self: self.env.ref("base.VEF"),
    )
    
    islr_retention_tax_id = fields.Many2one(
        related="partner_id.islr_retention_tax_id",
        domain="[('type','=','islr')]",
        store=True,
        readonly=False
    )

    iae_retention_tax_id = fields.Many2one(
        related="partner_id.iae_retention_tax_id",
        domain="[('type','=','iae')]",
        store=True,
        readonly=False
    )
    iva_retention_tax_id = fields.Many2one(
        related="partner_id.iva_retention_tax_id",
        domain="[('type','=','iva')]",
        readonly=False,
        store=True
    )

    iva_retention = fields.Monetary(
        "Amount detained by IVA",
        currency_field="retention_currency_id",
        compute="compute_retention_amount"
    )
    islr_retention = fields.Monetary(
        "Amount detained by ISLR",
        currency_field="retention_currency_id",
        compute="compute_retention_amount"
    )
    iae_retention = fields.Monetary(
        "Amount detained by IAE",
        currency_field="retention_currency_id",
        compute="compute_retention_amount"
    )
    total_detained = fields.Monetary(
        "Total detained",
        currency_field="retention_currency_id",
        compute="compute_retention_amount"
    )
    iae_type = fields.Selection(IAE_TYPES, "Transaction type")
    retention_line_id = fields.Many2one("retention.line", "Retention Line")
    is_active_theoretical = fields.Boolean(
        related="company_id.active_retention_theoretical")
    counted_retentions = fields.Integer(compute="compute_counted_retentions")
    retention_line_ids = fields.One2many(
        'retention.line',
        'invoice_id',
        string='Líneas de Retención',
        copy=False
    )

    @api.depends(
        "amount_total",
        "currency_id",
        "retention_currency_id",
        "iva_retention_tax_id",
        "islr_retention_tax_id",
        "iae_retention_tax_id",
        "invoice_date",
    )
    def compute_retention_amount(self):
        for move in self:

            def _convert(amount):
                return move.currency_id._convert(
                    from_amount=amount,
                    to_currency=move.retention_currency_id,
                    company=move.company_id,
                    date=move.invoice_date or fields.date.today(),
                    round=True,
                )

            def _percentage(amount, percentage):
                return amount * percentage / 100

            amount_base = move.amount_untaxed
            taxes = {
                'iva': move.iva_retention_tax_id.tax,
                'islr': move.islr_retention_tax_id.tax,
                'iae': move.iae_retention_tax_id.tax,
            }

            iva_retention = _percentage(move.amount_tax, taxes['iva'])
            islr_retention = _percentage(amount_base, taxes['islr'])
            iae_retention = _percentage(amount_base, taxes['iae'])
            move.iva_retention = _convert(iva_retention)
            move.islr_retention = _convert(islr_retention)
            move.iae_retention = _convert(iae_retention)

            if move.islr_retention_tax_id.decrement:
                move.islr_retention -= (
                    move.islr_retention_tax_id.decrement
                )

            move.total_detained = (
                move.iva_retention
                + move.islr_retention
                + move.iae_retention
            )

    def compute_counted_retentions(self):
        for move in self:
            move.counted_retentions = len(
                self.env["retention.line"]
                    .search([("invoice_id", "=", move.id)])
                    .mapped("retention_id")
            )

    def create_retentions(self):

        def _check_has_retention_by_type(partner_type):
            return self.env['retention.line'].search([
                ("invoice_id", "=", self.id),
                ("type", "=", partner_type),
                ("state", "!=", "cancel")
            ])

        RETENTION_DOMAIN = [
            ("partner_id", "=", self.partner_id.id),
            ("company_id", "=", self.company_id.id),
            ("current", "=", True),
            ("state", "=", "draft"),
        ]

        currency = self.env["res.currency"].browse([3])
        partner_types = {}

        # Determinar si la retención es de cliente o proveedor
        retention_kind = "customer" if self.move_type in ["out_invoice", "out_refund"] else "vendor"

        if self.iva_retention_tax_id:
            partner_types["iva"] = {
                "tax": self.iva_retention_tax_id.id,
                "journal": self.company_id._get_retention_journal_id("iva", retention_kind).id,
            }

        if self.islr_retention_tax_id:
            partner_types["islr"] = {
                "tax": self.islr_retention_tax_id.id,
                "journal": self.company_id._get_retention_journal_id("islr", retention_kind).id,
            }

        if self.iae_retention_tax_id:
            partner_types["iae"] = {
                "tax": self.iae_retention_tax_id.id,
                "journal": self.company_id._get_retention_journal_id("iae", retention_kind).id,
            }

        for ret_type, value in partner_types.items():
            if not _check_has_retention_by_type(ret_type):
                current_retention = self.env["retention"].search(
                    RETENTION_DOMAIN + [("type", "=", ret_type), ("partner_type", "=", retention_kind)]
                )

                new_retention_line = self.env["retention.line"].create(
                    {
                        "invoice_id": self.id,
                        "ret_tax_id": value["tax"],
                        "currency_id": currency.id
                    }
                )

                if not current_retention:
                    new_retention = self.env["retention"].create(
                        {
                            "company_id": self.company_id.id,
                            "partner_id": self.partner_id.id,
                            "journal_id": value["journal"],
                            "type": ret_type,
                            "partner_type": retention_kind,
                            "line_ids": [(4, new_retention_line.id)],
                            "date": self.date,
                        }
                    )
                    new_retention.onchange_date_or_type()
                else:
                    new_retention_line.retention_id = current_retention

                new_retention_line.onchange_invoice_or_currency()

    def action_generate_retention_report(self):
        retention_amounts = defaultdict(int)

        if not self.invoice_date:
            raise UserError(
                _("Please, add the invoice date to generate the Theoretical")
            )

        if self.iva_retention_tax_id:
            retention_amounts["iva"] = (
                self.amount_tax * self.iva_retention_tax_id.tax
            ) / 100

        if self.islr_retention_tax_id:
            retention_amounts["islr"] = ((self.amount_untaxed * self.islr_retention_tax_id.tax) / 100) - self.islr_retention_tax_id.decrement

        if self.iae_retention_tax_id:
            retention_amounts["iae"] = (
                self.amount_untaxed * self.iae_retention_tax_id.tax
            ) / 100

        return {
            "name": _("Retention Theoretical"),
            "type": "ir.actions.act_window",
            "res_model": "account.move.retention.wizard",
            "view_mode": "form",
            "context": {
                **retention_amounts,
                "invoice_name": self.name,
                "move_currency_id": self.currency_id.id,
                "invoice_amount_due": self.amount_residual,
                "invoice_date": self.invoice_date.strftime("%Y-%m-%d"),
                "partner_id": self.partner_id.id,
            },
            "target": "new",
        }

    def button_open_retention(self):
        self.ensure_one()
        res = {}
        retentions = self.env["retention.line"] \
            .search([("invoice_id", "=", self.id)]) \
            .mapped("retention_id")
        if retentions:
            res.update({
                "name": _("Retentions"),
                "type": "ir.actions.act_window",
                "res_model": "retention",
                "context": {"create": False},
                "view_mode": "tree,form",
                "domain": [("id", "in", retentions.ids)],
            })

        return res

    def action_view_retentions(self):
        self.ensure_one()
        action = {
            'name': 'Retenciones',
            'type': 'ir.actions.act_window',
            'res_model': 'retention',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.retention_line_ids.mapped('retention_id').ids)],
            'context': {
                'default_partner_id': self.partner_id.id,
                'default_partner_type': 'customer' if self.move_type in ['out_invoice', 'out_refund'] else 'vendor',
            }
        }
        return action
