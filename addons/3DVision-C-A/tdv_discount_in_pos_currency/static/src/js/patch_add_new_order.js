/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

// Guarda referencia al método original
const originalAddNewOrder = PosStore.prototype.add_new_order;

patch(PosStore.prototype, {
    add_new_order(...args) {
        const order = originalAddNewOrder.apply(this, args);
        if (order && typeof order.set_is_refund === 'function') {
            order.set_is_refund(false);
        }
        return order;
    },
}); 