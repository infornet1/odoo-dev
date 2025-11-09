/** @odoo-module **/

import { Orderline } from "@point_of_sale/app/store/models"
import { patch } from "@web/core/utils/patch"


patch(Orderline.prototype, {
    get_ref_price_without_tax() {
        const priceWithoutTax = this.get_price_without_tax();
        return priceWithoutTax * this.pos.config.x_fiscal_printer_currency_rate;
    },
    get_ref_price_with_tax() {
        const priceWithTax = this.get_price_with_tax();
        return priceWithTax * this.pos.config.x_fiscal_printer_currency_rate;
    }
});