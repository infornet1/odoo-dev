/** @odoo-module **/

import { PaymentScreenStatus } from "@point_of_sale/app/screens/payment_screen/payment_status/payment_status";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreenStatus.prototype, {
    get secondTotalIgtfText(){
        return this.env.utils.formatCurrency(this.props.order.igtfAmount, true, this.props.order.pos.secondCurrency);
    }
})