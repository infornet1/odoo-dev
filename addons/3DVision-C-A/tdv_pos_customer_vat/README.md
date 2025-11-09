# TDV POS Customer VAT

## Version: '17.0.1.0.0'

## Description
This Odoo 17 addon adds the customer VAT field to the Point of Sale payment screen. When a customer is selected, the VAT number is displayed next to the customer name in the format: **Customer Name - (VAT)**.

## Features
- Displays customer VAT number in the POS payment screen
- Shows VAT only when available (conditional display)
- Maintains the original customer name display when no VAT is present
- Inherits the native PaymentScreenButtons template properly

## Installation
1. Copy the `tdv_pos_customer_vat` folder to your Odoo addons directory
2. Update the addon list in Odoo
3. Install the addon from the Apps menu

## Technical Details
- **Dependencies**: point_of_sale
- **Template Inheritance**: PaymentScreenButtons template
- **Field Used**: partner.vat
- **Display Format**: Customer Name - (VAT)

## Files Structure
```
tdv_pos_customer_vat/
├── __init__.py
├── __manifest__.py
├── README.md
└── static/
    └── src/
        └── xml/
            └── payment_screen.xml
```

## Usage
After installation, when you select a customer in the POS payment screen, if the customer has a VAT number, it will be displayed next to their name in the right sidebar of the payment interface.

