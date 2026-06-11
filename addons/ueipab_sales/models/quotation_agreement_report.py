# -*- coding: utf-8 -*-
"""Acuerdo de Inscripción PDF — report values.

Same pattern as ueipab_payroll_enhancements liquidacion_breakdown_report:
AbstractModel named report.<module>.<template_id> building a `reports` list.
"""
from odoo import api, models

from .sale_order import UEIPAB_BCV_NOTE


class QuotationAgreementReport(models.AbstractModel):
    _name = 'report.ueipab_sales.quotation_agreement'
    _description = 'Acuerdo de Inscripción PDF'

    @api.model
    def _get_report_values(self, docids, data=None):
        orders = self.env['sale.order'].browse(docids)
        reports = []
        for order in orders:
            def lines_by_prefix(prefixes, _o=order):
                return _o.order_line.filtered(
                    lambda l: l.product_id.default_code
                    and l.product_id.default_code.startswith(tuple(prefixes)))

            ins_lines = lines_by_prefix(['INS2627'])
            men_lines = lines_by_prefix(['MEN2627'])
            anu_lines = lines_by_prefix(['SEG2627', 'ING2627', 'OLI2627', 'ENC2627'])
            other_lines = order.order_line - ins_lines - men_lines - anu_lines

            ref_date = order.date_order.date() if order.date_order else None
            llamado = self.env['sale.order']._ueipab_llamado_for_date(ref_date)
            n_students = int(max(order.order_line.mapped('product_uom_qty') or [1]))

            plan_lines = order.order_line.filtered(lambda l: not l.display_type)

            reports.append({
                'order': order,
                'plan_lines': plan_lines,
                'partner': order.partner_id,
                'company': order.company_id,
                'llamado': llamado,
                'n_students': n_students,
                'ins_lines': ins_lines,
                'men_lines': men_lines,
                'anu_lines': anu_lines,
                'other_lines': other_lines,
                'validity_str': order.validity_date.strftime('%d/%m/%Y') if order.validity_date else '',
                'date_str': order.date_order.strftime('%d/%m/%Y') if order.date_order else '',
                'bcv_note': UEIPAB_BCV_NOTE,
            })
        return {
            'doc_ids': docids,
            'doc_model': 'sale.order',
            'docs': orders,
            'reports': reports,
        }
