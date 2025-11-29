# -*- coding: utf-8 -*-
{
    'name': 'UEIPAB HRMS Dashboard - Payslip Acknowledgment Widget',
    'version': '17.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Adds payslip acknowledgment tracking widget to HRMS Dashboard',
    'description': """
UEIPAB HRMS Dashboard - Payslip Acknowledgment Widget
======================================================

Extends the HRMS Dashboard with a payslip acknowledgment tracking widget.

Features:
---------
* Employee View: Personal acknowledgment status for own payslips
* Manager View: Batch-level acknowledgment statistics
* Progress bar showing acknowledgment percentage
* Quick access to pending acknowledgments
* Latest batch tracking with drill-down

This module extends hrms_dashboard without modifying it, ensuring
safe upgrades of the base module.

Dependencies:
-------------
* hrms_dashboard - Base HR Dashboard module
* ueipab_payroll_enhancements - Provides is_acknowledged field on hr.payslip
    """,
    'author': 'UEIPAB',
    'website': 'https://ueipab.edu.ve',
    'depends': [
        'hrms_dashboard',
        'ueipab_payroll_enhancements',
    ],
    'data': [
        'security/ir.model.access.csv',
    ],
    'assets': {
        'web.assets_backend': [
            'ueipab_hrms_dashboard_ack/static/src/css/payslip_ack.css',
            'ueipab_hrms_dashboard_ack/static/src/xml/payslip_ack_templates.xml',
            'ueipab_hrms_dashboard_ack/static/src/js/payslip_ack_widget.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'AGPL-3',
}
