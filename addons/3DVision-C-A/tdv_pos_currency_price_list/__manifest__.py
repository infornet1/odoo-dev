# -*- coding: utf-8 -*-
{
    'name': "POS Currency Price List",
    'summary': "POS Currency Price List - Control de métodos de pago por lista de precios",
    'description': """
        Control de métodos de pago en divisa basado en listas de precios del POS.
        Permite configurar qué listas de precio habilitan el popup de métodos de pago en divisa
        y bloquea manualmente los métodos de pago para forzar el uso del popup.
    """,
    'author': "3DVision C.A.",
    'website': "https://www.3dvisionve.com",
    'category': 'Customization',
    'version': '17.0.0.0',
    'depends': ['point_of_sale', 'tdv_multi_currency_pos_fixed'],
    'license': 'LGPL-3',
    'data': [
        'views/pos_config_view.xml',
        'views/pos_order_view.xml',
        'security/ir.model.access.csv',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'tdv_pos_currency_price_list/static/src/js/models.js',
            'tdv_pos_currency_price_list/static/src/js/Popups/DivisaPaymentMethodsPopup.js',
            'tdv_pos_currency_price_list/static/src/js/patch_payment_screen.js',
            'tdv_pos_currency_price_list/static/src/js/patch_ticket_screen.js',
            'tdv_pos_currency_price_list/static/src/xml/patch_payment_screen.xml',
            'tdv_pos_currency_price_list/static/src/xml/divisa_payment_methods_popup.xml',
            'tdv_pos_currency_price_list/static/src/xml/ticket_screen_currency_patch.xml',
            'tdv_pos_currency_price_list/static/src/js/patch_order_widget_getter.js',
            'tdv_pos_currency_price_list/static/src/js/patch_order_widget_should_update.js',
        ],
    },
    'installable': True,
    'application': True,
}
