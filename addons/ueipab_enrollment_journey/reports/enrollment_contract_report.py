# -*- coding: utf-8 -*-
from odoo import models


class EnrollmentContractReport(models.AbstractModel):
    _name = 'report.ueipab_enrollment_journey.enrollment_contract'
    _description = 'Enrollment Contract Report'

    def _get_report_values(self, docids, data=None):
        journeys = self.env['enrollment.journey'].browse(docids)
        company = self.env.company
        results = []
        for j in journeys:
            date = j.contract_date
            date_str = date.strftime('%d/%m/%Y') if date else '___/___/______'
            results.append({
                'journey': j,
                'company': company,
                'date_str': date_str,
                'students': j.student_ids,
                'partner': j.partner_id,
                'order': j.order_id,
            })
        return {'reports': results}
