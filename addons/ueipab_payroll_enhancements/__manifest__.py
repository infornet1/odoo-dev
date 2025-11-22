# -*- coding: utf-8 -*-
{
    'name': 'UEIPAB Payroll Enhancements',
    'version': '17.0.1.30.0',
    'category': 'Human Resources/Payroll',
    'summary': 'Enhanced payroll batch with total net, disbursement reports (PDF/Excel), liquidation breakdown, and custom reports menu',
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
* Relación de Liquidación - NEW! FULLY WORKING
  - Detailed breakdown of liquidation benefits and deductions
  - Shows all formula calculations for transparency
  - Displays progressive bono vacacional rate based on seniority
  - Tracks antiguedad from original hire date with prepaid deductions
  - Export formats: PDF or Excel (.xlsx)
  - Portrait Letter format (fits on one page)
  - Supports USD and VEB currency display
  - V1 and V2 liquidation structure compatibility
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
    """,
    'author': 'UEIPAB',
    'website': 'https://ueipab.edu.ve',
    'depends': [
        'hr_payroll_community',
        'ueipab_hr_contract',  # For access to custom fields if needed
    ],
    'data': [
        # Security
        'security/ir.model.access.csv',

        # Wizards
        'wizard/payroll_disbursement_wizard_view.xml',
        'wizard/payroll_taxes_wizard_view.xml',
        'wizard/payroll_accounting_wizard_view.xml',
        'wizard/liquidation_wizard_view.xml',
        'wizard/prestaciones_interest_wizard_view.xml',
        'wizard/liquidacion_breakdown_wizard_view.xml',
        'wizard/finiquito_wizard_view.xml',
        'wizard/payslip_compact_wizard_view.xml',

        # Reports
        'reports/report_actions.xml',
        'reports/disbursement_list_report.xml',
        'reports/payroll_disbursement_detail_report.xml',
        'reports/prestaciones_interest_report.xml',
        'reports/liquidacion_breakdown_report.xml',
        'reports/finiquito_report.xml',
        'reports/payslip_compact_report.xml',

        # Views and Menu
        'views/hr_payslip_employees_views.xml',
        'views/hr_payslip_run_view.xml',
        'views/hr_payslip_view.xml',
        'views/payroll_reports_menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'AGPL-3',
}
