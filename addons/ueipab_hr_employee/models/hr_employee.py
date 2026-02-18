import logging
from datetime import timedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    ueipab_rif = fields.Char(
        string='RIF',
        help='Registro de Informacion Fiscal (e.g. V-12345678-9)',
        groups='hr.group_hr_user',
        tracking=True,
    )
    ueipab_rif_expiry_date = fields.Date(
        string='Fecha Vencimiento RIF',
        help='Fecha de vencimiento del RIF',
        groups='hr.group_hr_user',
    )

    def _cron_check_document_expiry(self):
        """Weekly check for expiring RIF and Cedula documents.

        Sends email alerts to HR Manager at 60/30/0 day thresholds.
        """
        today = fields.Date.today()
        employees = self.search([
            ('employee_type', '=', 'employee'),
            ('active', '=', True),
        ])

        alerts = []
        for emp in employees:
            for label, date_val, doc_id in [
                ('RIF', emp.ueipab_rif_expiry_date, emp.ueipab_rif or ''),
                ('Cedula de Identidad', emp.id_expiry_date, emp.identification_id or ''),
            ]:
                if not date_val:
                    continue
                days_left = (date_val - today).days

                if days_left <= 0:
                    alerts.append((emp, label, doc_id, date_val, 'expired'))
                elif days_left <= 30:
                    alerts.append((emp, label, doc_id, date_val, 'warning_30'))
                elif days_left <= 60:
                    alerts.append((emp, label, doc_id, date_val, 'warning_60'))

        if not alerts:
            _logger.info("Document expiry check: no expiring documents found.")
            return

        # Group alerts by severity for the email
        expired = [a for a in alerts if a[4] == 'expired']
        warn_30 = [a for a in alerts if a[4] == 'warning_30']
        warn_60 = [a for a in alerts if a[4] == 'warning_60']

        body_parts = []
        if expired:
            body_parts.append('<h3 style="color: red;">Documentos Vencidos</h3><ul>')
            for emp, label, doc_id, date_val, _ in expired:
                body_parts.append(
                    f'<li><b>{emp.name}</b> - {label} {doc_id} '
                    f'vencio el {date_val.strftime("%d/%m/%Y")}</li>'
                )
            body_parts.append('</ul>')

        if warn_30:
            body_parts.append('<h3 style="color: orange;">Vencen en menos de 30 dias</h3><ul>')
            for emp, label, doc_id, date_val, _ in warn_30:
                days = (date_val - today).days
                body_parts.append(
                    f'<li><b>{emp.name}</b> - {label} {doc_id} '
                    f'vence el {date_val.strftime("%d/%m/%Y")} ({days} dias)</li>'
                )
            body_parts.append('</ul>')

        if warn_60:
            body_parts.append('<h3 style="color: #cc8800;">Vencen en menos de 60 dias</h3><ul>')
            for emp, label, doc_id, date_val, _ in warn_60:
                days = (date_val - today).days
                body_parts.append(
                    f'<li><b>{emp.name}</b> - {label} {doc_id} '
                    f'vence el {date_val.strftime("%d/%m/%Y")} ({days} dias)</li>'
                )
            body_parts.append('</ul>')

        body_html = ''.join(body_parts)
        subject = f'[UEIPAB-RRHH] Alerta de vencimiento de documentos ({len(alerts)} documento(s))'

        mail_vals = {
            'subject': subject,
            'author_id': self.env.user.partner_id.id,
            'body_html': body_html,
            'email_to': 'recursoshumanos@ueipab.edu.ve',
        }
        self.env['mail.mail'].sudo().create(mail_vals).send()
        _logger.info(
            "Document expiry check: sent alert for %d document(s) "
            "(%d expired, %d 30-day, %d 60-day)",
            len(alerts), len(expired), len(warn_30), len(warn_60),
        )
