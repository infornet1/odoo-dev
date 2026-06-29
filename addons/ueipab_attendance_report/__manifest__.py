{
    'name': 'UEIPAB Attendance Biweekly Report',
    'version': '17.0.1.6.31',
    'category': 'Human Resources/Attendance',
    'summary': 'Reporte quincenal de asistencia con confirmación digital del empleado',
    'depends': ['hr_attendance', 'mail', 'ueipab_payroll_enhancements'],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_attendance_report_views.xml',
        'views/hr_attendance_report_wizard_views.xml',
        'views/hr_attendance_correction_views.xml',
        'views/hr_attendance_revision_wizard_views.xml',
        'views/hr_attendance_rejection_wizard_views.xml',
        'views/hr_attendance_approve_wizard_views.xml',
        'views/hr_notice_acknowledgment_views.xml',
        'views/partner_communication_ack_views.xml',
        'views/vote_assist_wizard_views.xml',
        'views/menu.xml',
        'data/holidays_config.xml',
        'data/mail_template_attendance.xml',
        'data/mail_template_correction.xml',
    ],
    'assets': {
        # Patch the public attendance kiosk to guard the manual check-in/out path
        # against double-submit (concurrent manual_selection RPCs). See
        # static/src/js/kiosk_double_submit_guard.js.
        'hr_attendance.assets_public_attendance': [
            'ueipab_attendance_report/static/src/js/kiosk_double_submit_guard.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
