/** @odoo-module **/

import { Payment } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";

patch(Payment.prototype, {
    setup(...args) {
        super.setup(...args);
        this.x_printer_code = this.payment_method?.x_printer_code || null;
    },
    init_from_JSON(json) {
        super.init_from_JSON(json);
        this.x_printer_code = json.x_printer_code;
    },
    export_as_JSON(...args) {
        const json = super.export_as_JSON(...args);
        json.x_printer_code = this.x_printer_code;
        return json;
    },
    get_ref_amount() {
        let result = this.amount;
        if (this.pos.config.x_fiscal_printer_currency_rate !== 1 && this.payment_method.currency_rate !== this.pos.config.x_fiscal_printer_currency_rate) {
            result = this.amount * this.pos.config.x_fiscal_printer_currency_rate;
        }
        // if (this.payment_method.currency_rate !== 1) {
        //     result = result / this.payment_method.currency_rate;
        // }
        return result;
    }
});