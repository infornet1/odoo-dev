from odoo import models
import pytz
from pytz import timezone

RRHH_EMAIL = 'recursoshumanos@ueipab.edu.ve'


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    def _validate_leave_request(self):
        super()._validate_leave_request()
        self._cc_rrhh_outcome('✅', 'aprobado')

    def action_refuse(self):
        result = super().action_refuse()
        self._cc_rrhh_outcome('❌', 'rechazado')
        return result

    def _cc_rrhh_outcome(self, icon, word):
        rrhh = self.env['res.partner'].sudo().search(
            [('email', '=', RRHH_EMAIL)], limit=1
        )
        if not rrhh:
            return
        for holiday in self.filtered(
            lambda r: r.holiday_type == 'employee' and r.employee_id
        ):
            tz = timezone(holiday.tz or 'America/Caracas')
            date_local = pytz.utc.localize(holiday.date_from).astimezone(tz).replace(tzinfo=None)
            employee = holiday.employee_id.name
            leave_type = holiday.holiday_status_id.display_name
            holiday.sudo().message_notify(
                partner_ids=rrhh.ids,
                subject=f"[CC] {icon} {employee} — {leave_type} {word}",
                body=(
                    f'<p>El permiso de <strong>{employee}</strong> fue <strong>{word}</strong>.</p>'
                    f'<ul>'
                    f'<li><strong>Tipo:</strong> {leave_type}</li>'
                    f'<li><strong>Fecha:</strong> {date_local.strftime("%d/%m/%Y %H:%M")} VET</li>'
                    f'</ul>'
                ),
            )
