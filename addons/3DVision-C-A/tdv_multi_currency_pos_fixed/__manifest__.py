# -*- coding: utf-8 -*-
{
    "name": "Point Of Sale - Multi Currency Fixed",
    "version": "17.0.0.0",
    "author": "3DVision C.A.",
    "website": "https://www.3dvisionve.com",
    "depends": ["point_of_sale", "tdv_multi_currency_account"],
    "summary": "Allows to visualize a second reference currency in the POS interface",
    "description": """
        Add a second currency in the items of the products,
        in the order and in the payment methods
    """,
    "category": "Customization",
    "license": "LGPL-3",
    "application" : False,
    "installable" : True,
    "auto_install": True,
    "data": ["views/pos_payment_method_views.xml", "views/res_config_settings_views.xml"],
    "assets": {
        "point_of_sale._assets_pos": [
            # Models
            "tdv_multi_currency_pos_fixed/static/src/app/store/models.js",

            # Products List
            "tdv_multi_currency_pos_fixed/static/src/app/screens/productScreen/productList/productList.xml",

            # Product Card
            "tdv_multi_currency_pos_fixed/static/src/app/components/productCard/productCard.js",
            "tdv_multi_currency_pos_fixed/static/src/app/components/productCard/productCard.xml",

            # Product Screen
            "tdv_multi_currency_pos_fixed/static/src/app/screens/productScreen/productScreen.xml",

            # Product Widget
            "tdv_multi_currency_pos_fixed/static/src/app/components/orderWidget/orderWidget.js",
            "tdv_multi_currency_pos_fixed/static/src/app/components/orderWidget/orderWidget.xml",

            # Product OrderLine
            "tdv_multi_currency_pos_fixed/static/src/app/components/orderLine/orderLine.js",
            "tdv_multi_currency_pos_fixed/static/src/app/components/orderLine/orderLine.xml",

            # Payment Screen Status
            "tdv_multi_currency_pos_fixed/static/src/app/screens/paymentScreen/paymentStatus/paymentStatus.js",
            "tdv_multi_currency_pos_fixed/static/src/app/screens/paymentScreen/paymentStatus/paymentStatus.xml",

            # Payment Screen Payment Lines
            "tdv_multi_currency_pos_fixed/static/src/app/screens/paymentScreen/paymentLines/paymentLines.js",
            "tdv_multi_currency_pos_fixed/static/src/app/screens/paymentScreen/paymentLines/paymentLines.xml",

            # Payment Screen
            "tdv_multi_currency_pos_fixed/static/src/app/screens/paymentScreen/payment_screen.js",

            # Closing Popups
            "tdv_multi_currency_pos_fixed/static/src/app/navbar/closingPopup/closingPopup.js",
            "tdv_multi_currency_pos_fixed/static/src/app/navbar/closingPopup/closingPopup.xml",

            # Receipt Screen
            "tdv_multi_currency_pos_fixed/static/src/app/screens/receiptScreen/orderReceipt.xml",

            # Receipt Screen
            "tdv_multi_currency_pos_fixed/static/src/app/screens/partnerScreen/partnerList.js",

            #Utils
            "tdv_multi_currency_pos_fixed/static/src/app/utils/contextualUtilsService.js",

            # "tdv_multi_currency_pos_fixed/static/src/js/**/*.js",
            # "tdv_multi_currency_pos_fixed/static/src/xml/**/*.xml"
        ],
    }
}
