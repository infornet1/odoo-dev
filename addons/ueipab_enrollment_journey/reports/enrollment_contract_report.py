# -*- coding: utf-8 -*-
import base64
import io

from odoo import models


class EnrollmentContractReport(models.AbstractModel):
    _name = 'report.ueipab_enrollment_journey.enrollment_contract'
    _description = 'Enrollment Contract Report'

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

    def _get_report_values(self, docids, data=None):
        journeys = self.env['enrollment.journey'].browse(docids)
        company = self.env.company
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        ceiling_per_payment = 218.88
        total_payments = 13
        results = []
        for j in journeys:
            date = j.contract_date
            date_str = date.strftime('%d/%m/%Y') if date else '___/___/______'
            n_students = len(j.student_ids) or 1
            ceiling_total = ceiling_per_payment * n_students * total_payments
            verify_url = '%s/verify-contract/%s' % (base_url, j.access_token)
            qr_b64 = self._make_qr_b64(verify_url)
            results.append({
                'journey': j,
                'company': company,
                'date_str': date_str,
                'students': j.student_ids,
                'partner': j.partner_id,
                'order': j.order_id,
                'n_students': n_students,
                'ceiling_per_payment': ceiling_per_payment,
                'total_payments': total_payments,
                'ceiling_total': ceiling_total,
                'verify_url': verify_url,
                'qr_b64': qr_b64,
            })
        return {'reports': results}
