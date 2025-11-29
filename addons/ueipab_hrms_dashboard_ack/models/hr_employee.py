# -*- coding: utf-8 -*-
"""
UEIPAB HRMS Dashboard - Payslip Acknowledgment Widget

Extends hr.employee with methods to fetch payslip acknowledgment statistics
for the HRMS Dashboard widget.
"""

from odoo import api, models
from odoo.http import request


class HrEmployee(models.Model):
    """Extend hr.employee with payslip acknowledgment statistics methods."""

    _inherit = 'hr.employee'

    @api.model
    def get_payslip_acknowledgment_stats(self):
        """
        Fetch payslip acknowledgment statistics for dashboard widget.

        Returns different data based on user role:
        - Employee: Personal acknowledgment stats
        - Manager: Batch-level statistics with breakdown

        Returns:
            dict: Acknowledgment statistics including:
                - personal: Personal stats (all users)
                - batch: Latest batch stats (managers only)
                - is_manager: Boolean flag
        """
        uid = request.session.uid
        employee = self.env['hr.employee'].sudo().search(
            [('user_id', '=', uid)], limit=1
        )

        # Check if user is HR manager
        is_manager = self.env.user.has_group('hr.group_hr_manager')

        result = {
            'is_manager': is_manager,
            'personal': self._get_personal_ack_stats(employee),
            'batch': self._get_batch_ack_stats() if is_manager else {},
        }

        return result

    def _get_personal_ack_stats(self, employee):
        """
        Get personal acknowledgment statistics for an employee.

        Args:
            employee: hr.employee record

        Returns:
            dict: Personal stats including total, acknowledged, pending counts
        """
        if not employee:
            return {
                'total': 0,
                'acknowledged': 0,
                'pending': 0,
                'percentage': 0,
                'recent': [],
            }

        # Get all payslips for this employee (last 12 months worth)
        payslips = self.env['hr.payslip'].sudo().search([
            ('employee_id', '=', employee.id),
            ('state', 'in', ['done', 'paid']),
        ], order='date_to desc', limit=24)

        total = len(payslips)
        acknowledged = len(payslips.filtered(lambda p: p.is_acknowledged))
        pending = total - acknowledged
        percentage = round((acknowledged / total * 100), 1) if total > 0 else 0

        # Get recent payslips (last 6) with status
        recent = []
        for slip in payslips[:6]:
            recent.append({
                'id': slip.id,
                'number': slip.number or slip.name,
                'date': slip.date_to.strftime('%b %Y') if slip.date_to else '',
                'acknowledged': slip.is_acknowledged,
                'batch_name': slip.payslip_run_id.name if slip.payslip_run_id else '',
            })

        return {
            'total': total,
            'acknowledged': acknowledged,
            'pending': pending,
            'percentage': percentage,
            'recent': recent,
        }

    def _get_batch_ack_stats(self):
        """
        Get batch-level acknowledgment statistics for managers.

        Returns:
            dict: Batch stats including latest batch info and overall stats
        """
        # Get latest batches with payslips
        batches = self.env['hr.payslip.run'].sudo().search([
            ('state', 'in', ['close', 'done', 'verify']),
        ], order='date_end desc', limit=5)

        if not batches:
            return {
                'latest_batch': {},
                'recent_batches': [],
                'overall': {
                    'total': 0,
                    'acknowledged': 0,
                    'pending': 0,
                    'percentage': 0,
                },
            }

        # Process each batch
        batch_stats = []
        for batch in batches:
            payslips = batch.slip_ids.filtered(lambda p: p.state in ['done', 'paid'])
            total = len(payslips)
            acknowledged = len(payslips.filtered(lambda p: p.is_acknowledged))
            pending = total - acknowledged
            percentage = round((acknowledged / total * 100), 1) if total > 0 else 0

            batch_stats.append({
                'id': batch.id,
                'name': batch.name,
                'date_end': batch.date_end.strftime('%Y-%m-%d') if batch.date_end else '',
                'total': total,
                'acknowledged': acknowledged,
                'pending': pending,
                'percentage': percentage,
            })

        # Get pending employees from latest batch
        latest_batch = batches[0]
        pending_employees = []
        pending_slips = latest_batch.slip_ids.filtered(
            lambda p: p.state in ['done', 'paid'] and not p.is_acknowledged
        )
        for slip in pending_slips[:10]:  # Limit to 10 for display
            pending_employees.append({
                'id': slip.employee_id.id,
                'name': slip.employee_id.name,
                'payslip_id': slip.id,
                'payslip_number': slip.number or slip.name,
            })

        # Overall stats (all confirmed batches in last 3 months)
        all_payslips = self.env['hr.payslip'].sudo().search([
            ('state', 'in', ['done', 'paid']),
            ('payslip_run_id', '!=', False),
        ])
        overall_total = len(all_payslips)
        overall_ack = len(all_payslips.filtered(lambda p: p.is_acknowledged))

        return {
            'latest_batch': batch_stats[0] if batch_stats else {},
            'recent_batches': batch_stats,
            'pending_employees': pending_employees,
            'overall': {
                'total': overall_total,
                'acknowledged': overall_ack,
                'pending': overall_total - overall_ack,
                'percentage': round((overall_ack / overall_total * 100), 1) if overall_total > 0 else 0,
            },
        }
