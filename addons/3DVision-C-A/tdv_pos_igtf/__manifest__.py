# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
{
    "name": "IGTF in Point Of Sale",
    "version": "17.0",
    "category": "Point of Sale",
    "summary": """""",
    "description" :"""""",
    "author": "3DVision, C.A",
    "website": "https://www.3dvisionca.com",
    "depends": ["point_of_sale", "igtf"],
    "license":"LGPL-3",
    "auto_install": True,
    "data": [
        "data/product_data.xml",
        "views/pos_payment_method_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            # Models
            "tdv_pos_igtf/static/src/app/store/models.js",

            # Payment Screen Status
            "tdv_pos_igtf/static/src/app/screens/paymentStatus/paymentStatus.js",
            "tdv_pos_igtf/static/src/app/screens/paymentStatus/paymentStatus.xml",
        ]
    }
}
