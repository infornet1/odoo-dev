{
    'name': 'Sales Order Automatic',
    'version': "1.0.0",
    'category': 'Sales,Warehouse,Accounting',
    'summary': """ Auto Invoice Generation and Auto Sending of Invoice on 
     Delivery validation.""",
    'description': """This module generates and post invoice  while validating 
    the delivery""",
    'author': "3DVision C.A.",
    'depends': ['base', 'sale_management', 'stock', 'account'],
    'data': ['views/res_config_settings_views.xml'],
    'license': "LGPL-3",
    'images': [
        'static/description/icons.png',
        # 'security/ir.model.access.csv',
        ],
    'installable': True,
    'auto_install': False,
    'application': True
}
