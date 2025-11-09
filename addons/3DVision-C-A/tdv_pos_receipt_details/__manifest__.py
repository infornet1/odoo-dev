# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
{
    "name": "Partner Details in PoS Receipt",
    "version": "16.0",
    "category": "Point of Sale",
    "summary": """""",
    "description" :"""""",
    "author": "3DVision, C.A",
    "website": "https://www.3dvisionca.com",
    "depends": ["point_of_sale"],
    "license":"LGPL-3",
    # "auto_install": True,
    "data": [
        "views/res_config_settings_views.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            # "tdv_pos_receipt_details/static/src/app/screens/receip_screen/receip/receip_header/orderReceipt.js"
            # "tdv_pos_receipt_details/static/src/app/screens/receip_screen/receip/receip_header/orderReceipt.xml",
            "tdv_pos_receipt_details/static/src/**/*"
        ]
    },
}
