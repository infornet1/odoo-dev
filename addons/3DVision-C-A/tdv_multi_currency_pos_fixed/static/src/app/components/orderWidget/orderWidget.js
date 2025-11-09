/** @odoo-module **/
import { OrderWidget } from "@point_of_sale/app/generic_components/order_widget/order_widget";
import { patch } from "@web/core/utils/patch";

// patch(OrderWidget.prototype, {
//     willStart(...args){
//         super.willStart(...args);
//         this.props = { ...this.props, secondTotal: String , secondTax: String };
//     }
// })

patch(OrderWidget, {
    props: {
        ...OrderWidget.props,
        secondTotal: { type: String, optional: true },
        secondTax: { type: String, optional: true }
    }
})
