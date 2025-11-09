# -*- coding: utf-8 -*-
{
	'name': 'TDV POS Restrict Change',
	'Version': '17.0.1.0.0',
	'summary': 'Restrict POS validation when there is change to return',
	'category': 'Point of Sale',
	'author': '3DVision, C.A',
	'website': 'https://www.3dvisionca.com',
	'license': 'LGPL-3',
	'depends': ['point_of_sale', 'tdv_multi_currency_pos_fixed'],
	'data': [],
	'assets': {
		'point_of_sale._assets_pos': [
			'tdv_pos_restrict_change/static/src/app/screens/paymentScreen/payment_screen.js',
		],
	},
	'installable': True,
	'auto_install': True,
	'application': False,
}
