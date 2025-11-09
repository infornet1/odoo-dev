/** @odoo-module **/
import { PaymentScreenPaymentLines } from "@point_of_sale/app/screens/payment_screen/payment_lines/payment_lines";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreenPaymentLines.prototype, {
    formatLineAmount(paymentline){
        return this.env.utils.formatCurrency(
            paymentline.get_amount(),
            true,
            paymentline.payment_method.currency_id,
            true,
        );
    }
})