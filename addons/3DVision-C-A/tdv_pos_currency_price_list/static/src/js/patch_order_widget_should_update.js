/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { OrderWidget } from "@point_of_sale/app/generic_components/order_widget/order_widget";

patch(OrderWidget.prototype, {
    shouldUpdate(nextProps) {
        if (!nextProps || !nextProps.order) {
            return false;
        }
        return true;
    },
});


