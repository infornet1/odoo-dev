# -*- coding: utf-8 -*-
{
    'name': 'UEIPAB Payroll Enhancements',
    'version': '17.0.1.50.0',
    'category': 'Human Resources/Payroll',
    'summary': 'Enhanced payroll batch with total net, disbursement reports, advance payments, and custom reports menu',
    'description': """
UEIPAB Payroll Enhancements
============================
Enhancements to HR Payroll Community for UEIPAB-specific requirements.

Features:
---------
* Salary structure selector in batch payslip generation wizard
* Total Net Payable field in batch list and form views
* Smart defaults based on batch name/context
* Support for special payroll structures (Aguinaldos, bonuses, etc.)
* Maintains backward compatibility with standard flow
* Custom Reports menu with business-specific reports
* Detailed disbursement report (Landscape, accounting style)
* Prestaciones Sociales Interest Report (monthly breakdown)

Reports Available:
------------------
* Payroll Disbursement Detail - FULLY WORKING
  - Export formats: PDF or Excel (.xlsx)
  - Landscape Letter format (8.5"x11")
  - Courier New font for PDF (accounting style)
  - Excel export with formatted columns and totals
  - Columns: Employee, VAT ID, Department, Gross, ARI Tax, Social Security, Other Deductions, Net USD, Exchange Rate, Net VEB
  - Flexible filtering (batch or date range)
* Prestaciones Soc. Intereses - FULLY WORKING
  - Month-by-month breakdown of prestaciones and interest accrual
  - Shows quarterly deposits (15 days every 3 months)
  - Displays accumulated balance and interest earned
  - Supports USD and VEB currency display
  - Multiple payslip selection for batch reporting
* Relación de Liquidación - FULLY WORKING
  - Detailed breakdown of liquidation benefits and deductions
  - Shows all formula calculations for transparency
  - Displays progressive bono vacacional rate based on seniority
  - Tracks antiguedad from original hire date with prepaid deductions
  - Export formats: PDF or Excel (.xlsx)
  - Portrait Letter format (fits on one page)
  - Supports USD and VEB currency display
  - V1 and V2 liquidation structure compatibility
  - NEW: Estimation Mode with global % reduction (VEB only)
    * Generates projection reports without signature sections
    * Applies configurable reduction percentage to all amounts
    * Includes "ESTIMACIÓN" watermark and disclaimer
* Payroll Taxes - Coming soon
* Payroll Accounting - Coming soon
* Liquidation Forms - Coming soon

Use Cases:
----------
* Generate Aguinaldos batch with correct structure
* Generate bonus payslips without manual correction
* Generate liquidation payslips with appropriate structure
* View total net payable for disbursement planning
* Print detailed disbursement reports for finance approval
* Generate prestaciones interest breakdown for labor law compliance
* Flexible override for any special payroll scenario

Advance Payment System (Pago Adelanto):
---------------------------------------
* Partial salary disbursement for financial constraints
* Checkbox 'Es Pago Adelanto' with percentage field
* Salary rules apply multiplier to earnings
* Deductions recalculate on reduced amounts
* Remainder payment linked to original advance batch
* Reconciliation email template showing full payment history
* Each batch posts independently with its exchange rate
    """,
    'author': 'UEIPAB',
    'website': 'https://ueipab.edu.ve',
    'depends': [
        'hr_payroll_community',
        'ueipab_hr_contract',  # For access to custom fields if needed
        'website',  # For portal templates
    ],
    'data': [
        # 1. Security
        'security/ir.model.access.csv',

        # 2. Wizards (Define actions)
        'wizard/payroll_disbursement_wizard_view.xml',
        'wizard/payroll_taxes_wizard_view.xml',
        'wizard/payroll_accounting_wizard_view.xml',
        'wizard/liquidation_wizard_view.xml',
        'wizard/prestaciones_interest_wizard_view.xml',
        'wizard/liquidacion_breakdown_wizard_view.xml',
        'wizard/finiquito_wizard_view.xml',
        'wizard/payslip_compact_wizard_view.xml',
        'wizard/batch_email_wizard_view.xml',
        'wizard/ack_reminder_wizard_view.xml',
        'wizard/aguinaldos_disbursement_wizard_view.xml',

        # 3. Report Templates & Actions
        'reports/disbursement_list_report.xml',
        'reports/payroll_disbursement_detail_report.xml',
        'reports/prestaciones_interest_report.xml',
        'reports/liquidacion_breakdown_report.xml',
        'reports/finiquito_report.xml',
        'reports/payslip_compact_report.xml',
        'reports/aguinaldos_disbursement_report.xml',
        'reports/report_actions.xml',
        'data/mail_template_payslip.xml',  # After reports (depends on action_report_payslip_compact)
        'data/email_template_ack_reminder.xml',  # Acknowledgment reminder email template

        # 4. Views (which may inherit or use actions from above)
        'views/hr_payslip_employees_views.xml',
        'views/hr_payslip_run_view.xml',
        'views/hr_payslip_view.xml',
        'views/payslip_acknowledge_templates.xml',

        # 5. Menus (last, as they depend on everything else)
        'views/payroll_reports_menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'AGPL-3',
}
