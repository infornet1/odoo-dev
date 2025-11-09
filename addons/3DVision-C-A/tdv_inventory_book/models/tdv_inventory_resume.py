# -*- coding: utf-8 -*-
from odoo import fields, models, _
from odoo.exceptions import UserError

class InventoryResume(models.Model):
    _name = "tdv.inventory.resume"
    _description = "Inventory Resume"

    name = fields.Char(string="Name", required=True, readonly=False)
    description = fields.Char(string="Description",required=True,readonly=False)
    start_date = fields.Date(string="Start Date", required=True, readonly=False)
    end_date = fields.Date(string="End Date", required=True, readonly=False)
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("posted", "Posted"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
    )
    inventory_line_ids = fields.One2many(
        comodel_name="tdv.inventory.resume.line",
        inverse_name="inventory_resume_id",
        string="Lines",
    )
    company_id = fields.Many2one(
        string="Company",
        comodel_name="res.company",
        default=lambda self: self.env.company.id,
    )
    currency_id = fields.Many2one(
        string="Currency",
        comodel_name="res.currency",
        default=lambda self: self.env.company.currency_id.id,
        readonly=True,
    )

    def unlink(self):
        for record in self:
            if record.state != 'draft':
                raise UserError(_('You can only delete records in draft state.'))
            record.inventory_line_ids.unlink()
        return super().unlink()

    def action_post(self):
        for record in self:
            if record.state != 'draft':
                raise UserError(_('Only draft records can be posted.'))
            # Ejecuta la generación de información al confirmar
            record.generate_info()
            record.state = 'posted'
        return True

    def action_cancel(self):
        for record in self:
            if record.state != 'posted':
                raise UserError(_('Only posted records can be cancelled.'))
            record.state = 'cancelled'
        return True

    def action_draft(self):
        for record in self:
            if record.state != 'cancelled':
                raise UserError(_('Only cancelled records can be reset to draft.'))
            record.state = 'draft'
        return True

    def generate_info(self):
        self.ensure_one()
        products = self.env["product.product"].search(
            [
                ("detailed_type", "=", "product"),
                "|",
                ("company_id", "=", self.company_id.id),
                ("company_id", "=", False),
            ]
        )
        report_lines = []
        for product in products:
            line_ids = self.env["account.move.line"].search(
                [
                    ("company_id", "=", self.company_id.id),
                    ("date", "<=", self.end_date),
                    ("move_id.state", "=", "posted"),
                    ("product_id", "=", product.id),
                    ("move_id.move_type", "in", ["in_invoice", "in_refund", "out_invoice", "out_refund"]),
                ]
            )
            history_qty = 0
            history_amount = 0
            data = {
                "product_id": product.id,
                "initial_amount_qty": product.with_context({"to_date": self.start_date}).qty_available,
                "final_amount_qty": product.with_context({"to_date": self.end_date}).qty_available,
                "total_purchased_qty": 0,
                "total_purchased_amount": 0,
                "total_sold_qty": 0,
                "total_sold_amount": 0,
            }
            for line in line_ids:
                qty = line.product_uom_id._compute_quantity(line.quantity, product.uom_id)
                amount = line.currency_id._convert(
                    line.price_unit,
                    self.currency_id,
                    self.company_id,
                    line.move_id.invoice_date,
                )
                if line.date < self.start_date and line.move_id.move_type == "in_invoice":
                    history_amount += qty * amount
                    history_qty += qty
                    continue
                if line.date < self.start_date:
                    continue
                if line.move_id.move_type == "in_invoice":
                    data["total_purchased_qty"] += qty
                    data["total_purchased_amount"] += qty * amount
                elif line.move_id.move_type == "in_refund":
                    data["total_purchased_qty"] -= qty
                    data["total_purchased_amount"] -= qty * amount
                elif line.move_id.move_type == "out_invoice":
                    data["total_sold_qty"] += qty
                    data["total_sold_amount"] += qty * amount
                elif line.move_id.move_type == "out_refund":
                    data["total_sold_qty"] -= qty
                    data["total_sold_amount"] -= qty * amount
            data["initial_cost"] = history_amount / (history_qty or 1)
            data["final_cost"] = (history_amount + data["total_purchased_amount"]) / ((history_qty + data["total_purchased_qty"]) or 1)
            
            line = self.inventory_line_ids.filtered(lambda x: x.product_id.id == product.id)
            if (data["initial_amount_qty"] or data["final_amount_qty"] or 
                data["total_sold_qty"] or data["total_purchased_qty"]):
                if line:
                    line[0].write(data)
                else:
                    report_lines.append(data)
            elif line:
                line[0].unlink()
        if report_lines:
            self.inventory_line_ids = [(0, 0, line) for line in report_lines]
        return True