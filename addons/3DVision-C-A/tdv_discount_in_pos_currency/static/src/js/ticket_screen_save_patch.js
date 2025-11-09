/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";

const superOnClickOrder = TicketScreen.prototype.onClickOrder;

patch(TicketScreen.prototype, {
    onClickOrder(clickedOrder) {
        // Guardar la orden activa antes de cambiar
        const prevOrder = this.pos.get_order();
        if (this.pos.config && this.pos.config.iface_table_management && prevOrder && !prevOrder.finalized && !prevOrder.is_paid) {
            this.pos.db.save_unpaid_order(prevOrder);
        }
        // Llamar al original
        return superOnClickOrder.call(this, clickedOrder);
    }
}); 