# -*- coding: utf-8 -*-

from odoo import models


class PayslipReportWrapper:
    """Wrapper to add formatted dates to payslip objects for PDF rendering."""
    def __init__(self, payslip):
        self.payslip = payslip
        self.date_from_str = payslip.date_from.strftime('%d/%m/%Y') if payslip.date_from else 'N/A'
        self.date_to_str = payslip.date_to.strftime('%d/%m/%Y') if payslip.date_to else 'N/A'
        # Pre-copy frequently accessed attributes (use getattr for safety)
        self.id = getattr(payslip, 'id', None)
        self.number = getattr(payslip, 'number', None)
        self.payslip_run_id = getattr(payslip, 'payslip_run_id', None)
        self.employee_id = getattr(payslip, 'employee_id', None)
        self.line_ids = getattr(payslip, 'line_ids', [])

    def __getattr__(self, name):
        # Delegate all other attributes to the wrapped payslip
        if name.startswith('_'):
            # Don't delegate private attributes - raise AttributeError
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
        return getattr(self.payslip, name)


class PayslipEmailReport(models.AbstractModel):
    _name = 'report.ueipab_payroll_enhancements.report_payslip_email_document'
    _description = 'Payslip Email PDF Report'
    _table = 'report_payslip_email'  # Short table name to avoid PostgreSQL limit

    def _get_report_values(self, docids, data=None):
        """Prepare values for payslip email report."""
        payslips = self.env['hr.payslip'].browse(docids)

        # Pre-format ALL values to avoid any Python calls in QWeb
        formatted_data = {}
        for payslip in payslips:
            # Get exchange rate
            exchange_rate = getattr(payslip, 'exchange_rate_used', None) or 241.5780

            # Get payroll lines
            salary_v2 = payslip.line_ids.filtered(lambda l: l.code == 'VE_SALARY_V2')
            bonus_v2 = payslip.line_ids.filtered(lambda l: l.code == 'VE_BONUS_V2')
            extrabonus_v2 = payslip.line_ids.filtered(lambda l: l.code == 'VE_EXTRABONUS_V2')
            gross_v2 = payslip.line_ids.filtered(lambda l: l.code == 'VE_GROSS_V2')
            sso = payslip.line_ids.filtered(lambda l: l.code == 'VE_SSO_DED_V2')
            faov = payslip.line_ids.filtered(lambda l: l.code == 'VE_FAOV_DED_V2')
            paro = payslip.line_ids.filtered(lambda l: l.code == 'VE_PARO_DED_V2')
            ari = payslip.line_ids.filtered(lambda l: l.code == 'VE_ARI_DED_V2')
            total_ded = payslip.line_ids.filtered(lambda l: l.code == 'VE_TOTAL_DED_V2')

            # Format dates
            date_from_str = payslip.date_from.strftime('%d/%m/%Y') if payslip.date_from else 'N/A'
            date_to_str = payslip.date_to.strftime('%d/%m/%Y') if payslip.date_to else 'N/A'

            # Get NET amount from payslip lines (VE_NET_V2 or VE_NET)
            net_line = payslip.line_ids.filtered(lambda l: l.code == 'VE_NET_V2')
            if not net_line:
                net_line = payslip.line_ids.filtered(lambda l: l.code == 'VE_NET')
            net_amount = net_line.total if net_line else 0.0

            # Format amounts in VEB
            formatted_data[payslip.id] = {
                # Employee info
                'number': payslip.number or 'N/A',
                'payslip_run_name': payslip.payslip_run_id.name if payslip.payslip_run_id else 'N/A',
                'employee_name': payslip.employee_id.name or 'N/A',
                'employee_id_number': payslip.employee_id.identification_id or 'N/A',
                'bank_account': payslip.employee_id.bank_account_id.acc_number if payslip.employee_id.bank_account_id else 'N/A',

                # Dates
                'date_from': date_from_str,
                'date_to': date_to_str,
                'period': f"{date_from_str} → {date_to_str}",

                # Credits (pre-formatted with thousand separators)
                'salary_veb': f"{(salary_v2.total if salary_v2 else 0.0) * exchange_rate:,.2f}",
                'bonus_veb': f"{(bonus_v2.total if bonus_v2 else 0.0) * exchange_rate:,.2f}",
                'extrabonus_veb': f"{(extrabonus_v2.total if extrabonus_v2 else 0.0) * exchange_rate:,.2f}",
                'gross_veb': f"{(gross_v2.total if gross_v2 else 0.0) * exchange_rate:,.2f}",

                # Deductions (pre-formatted with thousand separators)
                'sso_veb': f"{abs(sso.total if sso else 0.0) * exchange_rate:,.2f}",
                'faov_veb': f"{abs(faov.total if faov else 0.0) * exchange_rate:,.2f}",
                'paro_veb': f"{abs(paro.total if paro else 0.0) * exchange_rate:,.2f}",
                'ari_veb': f"{abs(ari.total if ari else 0.0) * exchange_rate:,.2f}",
                'total_ded_veb': f"{abs(total_ded.total if total_ded else 0.0) * exchange_rate:,.2f}",

                # Total and exchange rate
                'net_wage_veb': f"{net_amount * exchange_rate:,.2f}",
                'exchange_rate': f"{exchange_rate:,.4f}",

                # Raw payslip for any other needs
                'payslip': payslip,
            }

        return {
            'doc_ids': docids,
            'doc_model': 'hr.payslip',
            'docs': payslips,
            'formatted_data': formatted_data,
            'data': data,
        }


class AguinaldosEmailReport(models.AbstractModel):
    _name = 'report.ueipab_payroll_enhancements.report_aguinaldos_email_document'
    _description = 'Aguinaldos Email PDF Report'
    _table = 'report_aguinaldos_email'  # Short table name to avoid PostgreSQL limit

    def _get_report_values(self, docids, data=None):
        """Prepare values for aguinaldos email report."""
        payslips = self.env['hr.payslip'].browse(docids)

        # Pre-format ALL values to avoid any Python calls in QWeb
        formatted_data = {}
        for payslip in payslips:
            # Get exchange rate
            exchange_rate = getattr(payslip, 'exchange_rate_used', None) or 241.5780

            # Get aguinaldos line
            aguinaldos_line = payslip.line_ids.filtered(lambda l: l.code == 'AGUINALDOS')
            aguinaldos_total = aguinaldos_line.total if aguinaldos_line else 0.0

            # Format dates
            date_from_str = payslip.date_from.strftime('%d/%m/%Y') if payslip.date_from else 'N/A'
            date_to_str = payslip.date_to.strftime('%d/%m/%Y') if payslip.date_to else 'N/A'

            # Format amounts in VEB
            aguinaldos_veb = aguinaldos_total * exchange_rate
            # For aguinaldos, net = aguinaldos total (no deductions)
            net_wage_veb = aguinaldos_veb

            formatted_data[payslip.id] = {
                # Employee info
                'number': payslip.number or 'N/A',
                'payslip_run_name': payslip.payslip_run_id.name if payslip.payslip_run_id else 'N/A',
                'employee_name': payslip.employee_id.name or 'N/A',
                'employee_id_number': payslip.employee_id.identification_id or 'N/A',
                'bank_account': payslip.employee_id.bank_account_id.acc_number if payslip.employee_id.bank_account_id else 'N/A',

                # Dates
                'date_from': date_from_str,
                'date_to': date_to_str,
                'period': f"{date_from_str} → {date_to_str}",

                # Amounts (pre-formatted with thousand separators)
                'aguinaldos_veb': f"{aguinaldos_veb:,.2f}",
                'net_wage_veb': f"{net_wage_veb:,.2f}",
                'exchange_rate': f"{exchange_rate:,.4f}",

                # Raw payslip for any other needs
                'payslip': payslip,
            }

        return {
            'doc_ids': docids,
            'doc_model': 'hr.payslip',
            'docs': payslips,
            'formatted_data': formatted_data,
            'data': data,
        }
