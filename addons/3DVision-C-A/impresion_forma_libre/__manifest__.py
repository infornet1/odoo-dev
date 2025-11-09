{
    'name': 'Print in Free Form',
    'version': '17.0.1.3',
    "author": "3DVision C.A.",
    'description': 'Management of tax impressions type free form',
    'summary': 'Allows tax printing in free format',
    'depends': ['base', 'account', 'tribute_fields'],
    'application': True,
    'installable': True,
    'license': "LGPL-3",
    'data': [
        'data/data_currency.xml',
        'report/freeform_templates.xml',
        'report/freeform_report_views.xml',
        'views/account_move_view.xml',
        'views/res_config_settings_views.xml',
    ]
}
