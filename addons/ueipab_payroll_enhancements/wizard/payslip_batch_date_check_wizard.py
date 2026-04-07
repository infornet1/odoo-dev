# -*- coding: utf-8 -*-
from odoo import models, fields, _


class HrPayslipRunDateCheckWizard(models.TransientModel):
    _name = 'hr.payslip.run.date.check.wizard'
    _description = 'Payslip Batch Date Logic Check'

    run_id = fields.Many2one('hr.payslip.run', string='Batch', required=True)
    issues_html = fields.Html(string='Issues', readonly=True, sanitize=False)
    has_blocker = fields.Boolean(default=False)
    sync_done = fields.Boolean(default=False)
    seq_fix_date = fields.Date(
        string='Suggested Accounting Date',
        help='Populated when a PAY1 sequence conflict is detected. '
             'Use "Auto-fix Accounting Dates" to apply this date to all draft payslips.',
    )

    def action_acknowledge(self):
        self.run_id.date_check_acknowledged = True
        return {'type': 'ir.actions.act_window_close'}

    def action_close(self):
        return {'type': 'ir.actions.act_window_close'}

    def action_fix_accounting_dates(self):
        """Set slip.date on all draft payslips to resolve PAY1 sequence conflict."""
        if not self.seq_fix_date:
            return {'type': 'ir.actions.act_window_close'}

        draft_slips = self.run_id.slip_ids.filtered(lambda s: s.state == 'draft')
        if not draft_slips:
            return {'type': 'ir.actions.act_window_close'}

        draft_slips.write({'date': self.seq_fix_date})
        self.run_id.date_check_acknowledged = True

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Accounting Dates Fixed'),
                'message': _(
                    '%d payslip(s) accounting date set to %s. '
                    'You can now validate the batch.'
                ) % (len(draft_slips), self.seq_fix_date),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }
