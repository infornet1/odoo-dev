# -*- coding: utf-8 -*-
"""
Kiosk minimum-interval toggle guard (UEIPAB)
--------------------------------------------
The public attendance kiosk's `manual_selection` is a TOGGLE: tap once to check
in, tap again to check out. When an employee taps their name twice within a few
seconds (impatience while geolocation resolves, or the screen returning to the
menu and looking "un-tapped"), the second tap flips check-in -> check-out and
leaves a row with `check_in == check_out` (worked_hours = 0) -> the arrival is
effectively erased. Real incidents: DIXIA BELLORIN Jun-23 (2 rows), LEIDYMAR
ARAY + MAIRELSY MOTTA Jun-30.

The JS double-submit guard (kiosk_double_submit_guard.js) only blocks RPCs fired
while the first is still IN FLIGHT (per-instance re-entrancy lock). It does NOT
cover taps ~2 s apart, where the first RPC has already returned and released the
lock. So the guard must also live on the server, independent of UI/session/device.

Fix: override `hr.employee._attendance_action_change` so a toggle within
`attendance.kiosk_min_toggle_seconds` (default 60 s) of the employee's last
attendance event is treated as an accidental double-tap and IGNORED (no-op,
current state preserved) -- no zero-duration row, no premature check-out.

See documentation/ATTENDANCE_DANGLING_OPEN_RECORDS.md.
"""

import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)

# ir.config_parameter key -> minimum seconds between two consecutive toggles for
# the same employee. 0 disables the guard.
_PARAM_KEY = 'attendance.kiosk_min_toggle_seconds'
_DEFAULT_SECONDS = 60


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    def _attendance_action_change(self, geo_information=None):
        self.ensure_one()
        try:
            threshold = int(self.env['ir.config_parameter'].sudo().get_param(
                _PARAM_KEY, _DEFAULT_SECONDS))
        except (TypeError, ValueError):
            threshold = _DEFAULT_SECONDS

        if threshold > 0:
            last = self.env['hr.attendance'].sudo().search(
                [('employee_id', '=', self.id)], order='id desc', limit=1)
            ref = last and (last.check_out or last.check_in)
            if ref:
                delta = (fields.Datetime.now() - ref).total_seconds()
                if 0 <= delta < threshold:
                    # Accidental double-tap: keep the current state untouched.
                    _logger.info(
                        "Kiosk toggle ignored for %s (emp %s): %.0fs since last "
                        "event (< %ss threshold) -- prevented zero-duration row.",
                        self.sudo().name, self.id, delta, threshold)
                    return last
        return super()._attendance_action_change(geo_information=geo_information)
