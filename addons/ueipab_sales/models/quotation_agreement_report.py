# -*- coding: utf-8 -*-
"""Acuerdo de Inscripción PDF — report values.

Same pattern as ueipab_payroll_enhancements liquidacion_breakdown_report:
AbstractModel named report.<module>.<template_id> building a `reports` list.
"""
import base64
import io

from odoo import api, models

from .sale_order import UEIPAB_BCV_NOTE


class QuotationAgreementReport(models.AbstractModel):
    _name = 'report.ueipab_sales.quotation_agreement'
    _description = 'Acuerdo de Inscripción PDF'

    def _make_qr_b64(self, url):
        try:
            import qrcode
            qr = qrcode.QRCode(version=1, box_size=6, border=3,
                                error_correction=qrcode.constants.ERROR_CORRECT_M)
            qr.add_data(url)
            qr.make(fit=True)
            img = qr.make_image(fill_color='black', back_color='white')
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()
        except ImportError:
            return None

    @api.model
    def _get_report_values(self, docids, data=None):
        orders = self.env['sale.order'].browse(docids)
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
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

            order._portal_ensure_token()
            verify_url = '%s/verify-quote/%s' % (base_url, order.access_token)
            qr_b64 = self._make_qr_b64(verify_url)
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
                'verify_url': verify_url,
                'qr_b64': qr_b64,
            })
        return {
            'doc_ids': docids,
            'doc_model': 'sale.order',
            'docs': orders,
            'reports': reports,
        }
