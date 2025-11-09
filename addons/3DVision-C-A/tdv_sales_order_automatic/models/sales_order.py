from odoo import models, fields, api


class SalesOrder(models.Model):
  _inherit = "sale.order"

  def action_confirm(self):
    res = super(SalesOrder, self).action_confirm()

    Config = self.env["ir.config_parameter"]
    Module = "sale_order_automatic" 
    
    auto_validate = Config.get_param("%s.is_auto_confirm" %Module)
    auto_confirm_delivery = Config.get_param("%s.is_auto_delivery" %Module)

    self.set_service_product_qty_delivered()
    if auto_validate:
      if auto_confirm_delivery and self.picking_ids:
        self._validate_confirmation_automatic()
      else:
        self._create_and_post_invoices()
    return res

  def _validate_confirmation_automatic(self):
    self.picking_ids.mapped(lambda p: p.button_validate())

  def set_service_product_qty_delivered(self):
    for order in self:
      service_lines = order.order_line.filtered(
        lambda line: line.product_id.type == "service"
      )
      for line in service_lines:
        line.qty_delivered = line.product_uom_qty

  def _create_and_post_invoices(self):
    for order in self:
      invoice = self._create_invoices(order) if order else False
      if invoice:
        invoice.action_post()
      # for order in self:
      #   for picking in order.picking_ids:
      #     if picking.sale_id.order_line and picking.ids:
      #       invoice = picking.sale_id._create_invoices(picking.sale_id) if picking.sale_id else False
      #       if invoice:
      #           invoice.action_post()

  # def _create_and_post_invoices(self):
  #   for order in self:
  #     for picking in order.picking_ids:
  #       #  if any(move.product_id.invoice_policy == 'delivery' for move in picking.move_ids) or not picking.sale_id.invoice_ids:
  #         invoice = picking.sale_id._create_invoices(picking.sale_id) if picking.sale_id else False
  #         if invoice:
  #             invoice.action_post()
