# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PurchaseReportLine(models.Model):
  _inherit = "tdv.purchase.report.line"

  retention_line_id = fields.Many2one("retention.line", "Retention Line")
  retention_id = fields.Many2one(related='retention_line_id.retention_id')

  amount_detained = fields.Monetary("Amount Detained", currency_field="currency_id")

  @api.onchange("invoice_id")
  def onchange_invoice_or_currency(self):
    super(PurchaseReportLine, self).onchange_invoice_or_currency()
    self._retention_line() 

  def _retention_line(self):
    retention_line = self._find_retention_line()
    if retention_line:
      self.retention_line_id = retention_line
      self.amount_detained = retention_line.currency_id._convert(
          from_amount=retention_line.amount_detained,
          to_currency=self.currency_id,
          company=self.company_id,
          date=retention_line.retention_id.date or fields.date.today(),
          round=True
      )
      self.retention_line_id = retention_line.id

  def _find_retention_line(self):
    return self.env['retention.line'].search([
        ('invoice_id', '=', self.invoice_id.id),
        ('type', '=', 'iva'),
        ("state", "=", "posted"),
    ], limit=1)


    # retention_line = self.env['retention.line'].search([
    #         ('invoice_id','=',self.invoice_id.id),
    #         ('type','=','iva'),
    #         ("state", "=", "posted"),
    #     ], limit=1)

    # if retention_line and retention_line.retention_id.state == 'posted':
    #         self.retention_line_id = retention_line
    #         self.amount_detained = retention_line.currency_id._convert(
    #             from_amount=retention_line.amount_detained,
    #             to_currency=se.lf.currency_id,
    #             company=self.company_id,
    #             date=retention_line.retention_id.date or fields.date.today(),
    #             round=True
    #         )