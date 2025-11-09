# -*- coding: utf-8 -*-

from odoo import api, fields, models


class InventoryResumeLine(models.Model):
    _name = "tdv.inventory.resume.line"
    _description = "inventory resume line"

    name = fields.Char(related="product_id.name")
    inventory_resume_id = fields.Many2one(
        comodel_name="tdv.inventory.resume", required=True
    )

    # product info
    product_id = fields.Many2one(comodel_name="product.product", string="product")
    initial_amount_qty = fields.Float(string="initial amount", default=0)
    initial_cost = fields.Monetary(string="initial cost", currency_field="currency_id")
    final_amount_qty = fields.Float(string="final amount", default=0)
    final_cost = fields.Monetary(string="final cost", currency_field="currency_id")

    # Purchase fields
    total_purchased_qty = fields.Float(string="total purchased", default=0)
    total_purchased_amount = fields.Monetary(
        string="total purchased amount", default=0, currency_field="currency_id"
    )

    # Sale fields
    total_sold_qty = fields.Float(string="Total sold", default=0)
    total_sold_amount = fields.Monetary(
        string="total sold amount", default=0, currency_field="currency_id"
    )

    # self-consumption
    self_consumption_qty = fields.Float(string="Self consumption QTY")
    self_consumption_amount = fields.Monetary(
        string="Self consumption amount", currency_field="currency_id"
    )

    # Reference fields
    currency_id = fields.Many2one(related="inventory_resume_id.currency_id")
    company_id = fields.Many2one(related="inventory_resume_id.company_id")
    uom_id = fields.Many2one(related="product_id.uom_id")
