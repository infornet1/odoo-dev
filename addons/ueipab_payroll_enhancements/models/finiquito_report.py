# -*- coding: utf-8 -*-

from odoo import models, api
from datetime import datetime


class FiniquitoReport(models.AbstractModel):
    _name = 'report.ueipab_payroll_enhancements.finiquito_report'
    _description = 'Finiquito Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        """
        Generate report data for finiquito agreement
        """
        # Get payslip IDs from data (wizard) or docids
        payslip_ids = data.get('payslip_ids') if data else docids
        payslips = self.env['hr.payslip'].browse(payslip_ids)
        
        # Get currency from data or default to USD
        currency_id = data.get('currency_id') if data else self.env.ref('base.USD').id
        currency = self.env['res.currency'].browse(currency_id)
        
        reports = []
        
        for payslip in payslips:
            employee = payslip.employee_id
            contract = payslip.contract_id
            
            # Get net liquidation amount (from NET salary rule)
            net_amount = 0.0
            
            # Try V2 first, fallback to V1
            net_line_v2 = payslip.line_ids.filtered(lambda l: l.code == 'LIQUID_NET_V2')
            net_line_v1 = payslip.line_ids.filtered(lambda l: l.code == 'LIQUID_NET')
            
            if net_line_v2:
                net_amount = abs(net_line_v2[0].total)
            elif net_line_v1:
                net_amount = abs(net_line_v1[0].total)
            
            # Convert to selected currency if needed (payslip uses company currency)
            payslip_currency = payslip.company_id.currency_id
            if currency != payslip_currency:
                # Default rate date is payslip date
                rate_date = payslip.date_to or payslip.date_from

                # Check for custom exchange rate override (matches Relación report behavior)
                if data and data.get('use_custom_rate') and data.get('custom_exchange_rate'):
                    # Use custom override rate
                    exchange_rate = data.get('custom_exchange_rate')
                    net_amount = net_amount * exchange_rate
                else:
                    # Check if custom date provided for automatic lookup
                    custom_date_raw = data.get('rate_date') if data else None
                    if custom_date_raw:
                        # Convert string to date object if needed
                        if isinstance(custom_date_raw, str):
                            try:
                                rate_date = datetime.strptime(custom_date_raw, '%Y-%m-%d').date()
                            except:
                                rate_date = payslip.date_to or payslip.date_from
                        else:
                            rate_date = custom_date_raw

                    # Use automatic rate for the determined date
                    net_amount = payslip_currency._convert(
                        net_amount,
                        currency,
                        payslip.company_id,
                        rate_date
                    )
            
            # Format dates
            date_start_str = contract.date_start.strftime('%d/%m/%Y') if contract.date_start else 'N/A'
            date_to_str = payslip.date_to.strftime('%d/%m/%Y') if payslip.date_to else 'N/A'
            
            # Get current date for footer
            today = datetime.today()
            day = today.day
            month_names = {
                1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril',
                5: 'mayo', 6: 'junio', 7: 'julio', 8: 'agosto',
                9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre'
            }
            month = month_names.get(today.month, '')
            year = today.year
            
            report_data = {
                'payslip': payslip,
                'employee': employee,
                'contract': contract,
                'currency': currency,
                'net_amount': net_amount,
                'date_start_str': date_start_str,
                'date_to_str': date_to_str,
                'today_day': day,
                'today_month': month,
                'today_year': year,
            }
            
            reports.append(report_data)
        
        return {
            'doc_ids': payslip_ids,
            'doc_model': 'hr.payslip',
            'docs': payslips,
            'data': data,
            'reports': reports,
        }
