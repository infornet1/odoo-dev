from collections import defaultdict

from odoo import fields, models, api
from odoo.exceptions import UserError

COMMISSION_TYPE = [("none", "NONE"), ("service", "SERVICE"), ("sale", "SALE")]
LINE_MODE = [("total", "Total"), ("partial", "Partial"), ("sale", "Sale")]


class SaleCommissionLine(models.Model):
    _name = "tdv.sale.commission.line"
    _description = "Sale Commission Line"

    move_line_id = fields.Many2one("account.move.line", string="Move Line")
    commission_id = fields.Many2one("tdv.sale.commission", string="Sale Commission")
    product_id = fields.Many2one("product.product", string="On Product")
    partner_id = fields.Many2one("res.partner", string="Employee")
    service_percent = fields.Float(string="Service Percentage")
    sale_percent = fields.Float(string="Sale Percentage")
    payment_id = fields.Many2one(string="Payment", comodel_name="account.payment")
    payment_amount = fields.Float(string="Payment Amount", default=1.0)
    payment_mode = fields.Selection(selection=LINE_MODE, default="total")

    @api.model
    def create(self, vals):
        return super().create(vals)

    @api.depends("product_id")
    def _compute_commission_type(self):
        for record in self:
            if record.product_id:
                if record.product_id.detailed_type == "service":
                    record.commission_type = "service"
                else:
                    record.commission_type = "sale"
            else:
                record.commission_type = "none"

    @api.depends("move_line_id")
    def _compute_subtotal(self):
        for record in self:
            if record.move_line_id:
                factor = (
                    1 if record.move_line_id.move_id.move_type == "out_invoice" else -1
                )
                record.subtotal = record.move_line_id.price_subtotal * factor

    @api.depends("commission_type", "move_line_id", "subtotal")
    def _compute_total_amount(self):
        for record in self:
            if record.commission_id.state == "done":
                continue
            if record.commission_type == "none":
                record.total_amount = 0
                continue
            if record.commission_type == "service":
                record.total_amount = (
                    record.service_percent * record.subtotal * record.payment_amount
                )
                record.percentage_applied = record.service_percent
            elif record.commission_type == "sale":
                record.total_amount = (
                    record.sale_percent * record.subtotal * record.payment_amount
                )
                record.percentage_applied = record.sale_percent

    percentage_applied = fields.Float(string="Percentage applied", readonly=True)
    subtotal = fields.Float(
        string="Base Total", compute="_compute_subtotal", default=0, store=True
    )
    total_amount = fields.Float(
        "Total Amount", compute="_compute_total_amount", store=True
    )
    commission_type = fields.Selection(
        COMMISSION_TYPE,
        string="Commission Type",
        compute="_compute_commission_type",
        store=True,
        readonly=True,
    )


class TotalCommissionLine(models.Model):
    _name = "tdv.total.commission.line"
    _description = "Total commission line"

    commission_type = fields.Selection(
        [("sale", "SALE"), ("service", "SERVICE")], string="Type"
    )
    partner_id = fields.Many2one("res.partner", string="Employee")
    base_amount = fields.Float(string="Base amount", default=0)
    amount = fields.Float("Amount")


class SaleCommission(models.Model):
    _name = "tdv.sale.commission"
    _description = "sales.commission"

    name = fields.Char(
        "Description",
        required=True,
        default="None",
        states={"done": [("readonly", True)], "cancelled": [("readonly", True)]},
    )
    state = fields.Selection(
        selection=[("draft", "Draft"), ("done", "Done"), ("cancelled", "Cancelled")]
    )
    sale_commission_line_ids = fields.One2many(
        "tdv.sale.commission.line",
        "commission_id",
        string="Commissions",
        states={"done": [("readonly", True)], "cancelled": [("readonly", True)]},
    )
    total_commission_line_ids = fields.Many2many(
        "tdv.total.commission.line",
        string="Total Commissions",
        states={"done": [("readonly", True)], "cancelled": [("readonly", True)]},
    )
    from_date = fields.Date(string="From Date", readonly=True)
    to_date = fields.Date(string="To Date", readonly=True)
    company_id = fields.Many2one(
        comodel_name="res.company", default=lambda self: self.env.company.id
    )

    def unlink(self):
        if any(record.state != "draft" for record in self):
            raise UserError("Only can delete in draft state")
        for record in self:
            record.sale_commission_line_ids.unlink()
        return super().unlink()

    @api.depends("sale_commission_line_ids")
    def _compute_commission_invoices(self):
        for record in self:
            record.commission_move_ids = False
            for line in record.sale_commission_line_ids:
                if line.move_line_id:
                    record.commission_move_ids |= line.move_line_id.move_id

    commission_move_ids = fields.Many2many(
        "account.move", compute="_compute_commission_invoices", store=True
    )

    def confirm_commission_action(self):
        self.ensure_one()
        self.state = "done"

    def cancel_commission_action(self):
        self.ensure_one()
        self.state = "cancelled"
        for line in self.sale_commission_line_ids:
            line.move_line_id = False
        self.total_commission_line_ids = False

    def calculate_total_amount(self):
        self.ensure_one()
        categories = ["sale", "service"]
        self.total_commission_line_ids = False
        for category in categories:
            values = defaultdict(lambda: {"base": 0, "total": 0})
            lines = self.sale_commission_line_ids.filtered_domain(
                [("commission_type", "=", category)]
            )
            for line in lines:
                values[line.partner_id]["total"] += line.total_amount
                values[line.partner_id]["base"] += line.subtotal
            self.total_commission_line_ids |= self.env[
                "tdv.total.commission.line"
            ].create(
                [
                    {
                        "partner_id": partner_id.id,
                        "commission_type": category,
                        "amount": amount["total"],
                        "base_amount": amount["base"],
                    }
                    for partner_id, amount in values.items()
                ]
            )
