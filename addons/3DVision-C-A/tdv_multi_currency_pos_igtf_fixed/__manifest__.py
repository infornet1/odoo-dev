# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
{
    "name": "Multi Currency PoS - IGTF fixed",
    "version": "17.0",
    "category": "Point of Sale",
    "summary": """""",
    "description" :"""""",
    "author": "3DVision, C.A",
    "website": "https://www.3dvisionca.com",
    "depends": ["tdv_multi_currency_pos_fixed", "tdv_pos_igtf"],
    "license":"LGPL-3",
    "auto_install": True,
    "data": [],
    "assets": {
        "point_of_sale._assets_pos": [
            # Models
            "tdv_multi_currency_pos_igtf_fixed/static/src/app/store/models.js",

            # Payment Screen Status
            "tdv_multi_currency_pos_igtf_fixed/static/src/app/screens/paymentStatus/paymentStatus.js",
            "tdv_multi_currency_pos_igtf_fixed/static/src/app/screens/paymentStatus/paymentStatus.xml",
        ]
    }
}
