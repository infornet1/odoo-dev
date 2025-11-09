/** @odoo-module **/

import { PaymentScreenStatus } from "@point_of_sale/app/screens/payment_screen/payment_status/payment_status";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreenStatus.prototype, {
    get hasIgtf(){
        let payments = this.props.order.paymentlines
        for (let i = 0; i < payments.length; i++){
            if (payments[i].payment_method.is_igtf === true)
                return true;
        }
        return false;
    },
    get totalIgtfText(){
        return this.env.utils.formatCurrency(this.props.order.igtfAmount);
    }
})