# -*- coding: utf-8 -*-
"""
AR-I Rejection Wizard

Allows HR to provide a reason when rejecting an AR-I declaration.
"""

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ARIRejectWizard(models.TransientModel):
    _name = 'ari.reject.wizard'
    _description = 'AR-I Rejection Wizard'

    ari_id = fields.Many2one(
        'hr.employee.ari',
        string='AR-I Declaration',
        required=True
    )
    rejection_reason = fields.Text(
        string='Rejection Reason',
        required=True,
        help='Explain why the AR-I declaration is being rejected'
    )

    def action_confirm_reject(self):
        """Confirm rejection with reason."""
        self.ensure_one()
        if not self.rejection_reason:
            raise ValidationError(_('Please provide a rejection reason.'))

        self.ari_id.write({
            'state': 'rejected',
            'rejection_reason': self.rejection_reason,
            'reviewed_by': self.env.uid,
            'review_date': fields.Date.today()
        })

        # TODO: Notify employee of rejection
        return {'type': 'ir.actions.act_window_close'}
