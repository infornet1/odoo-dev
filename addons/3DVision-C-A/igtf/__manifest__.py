{
    "name": "IGTF",
    "version": "1.0.0",
    "author": "3DVision C.A.",
    "website": "https://www.3dvisionve.com",
    "depends": ["tribute_fields"],
    "summary": "Activates the tax on large financial transactions",
    "description": """
        This module modifies the payment by adding an additional 3%
        on the amount paid in the cases applied the IGTF.
    """,
    "license" : "LGPL-3",
    "installable": True,
    "data": [
        "wizards/account_payment_register_view.xml",
        "views/res_config_settings_view.xml",
        "views/account_journal_view.xml",
        "views/account_move_view.xml",
        "views/account_payment_view.xml",
    ],
}