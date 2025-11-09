{
    "name": "POS Contact Tag Restriction",
    "version": "1.0.0",
    "category": "Point of Sale",
    "summary": "Restricts visible partners in POS based on selected contact tags.",
    "author": "3DVision, C.A",
    "website": "https://www.3dvisionca.com",
    "depends": ["point_of_sale"],
    "license":"LGPL-3",
    "data": [
        "views/pos_config_view.xml",
        "views/res_config_settings_view.xml",
        "data/res_partner_category_data.xml"
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "tdv_pos_contact_label/static/src/js/partner_list_extension.js",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False
}
