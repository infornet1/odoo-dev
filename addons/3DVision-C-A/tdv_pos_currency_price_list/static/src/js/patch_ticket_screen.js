/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";

// Guarda referencia al método original
const originalOnDoRefund = TicketScreen.prototype.onDoRefund;

patch(TicketScreen.prototype, {
    async onDoRefund() {
        
        // Guarda la orden activa y su estado antes del reembolso
        const beforeOrders = this.pos.orders.map(o => ({
            uid: o.uid,
            order: o,
            isEmpty: o.orderlines && o.orderlines.length === 0
        }));
        
        await originalOnDoRefund.apply(this, arguments);

        // Busca la orden que ahora tiene líneas negativas y antes estaba vacía
        for (const { uid, order, isEmpty } of beforeOrders) {
            if (
                isEmpty &&
                order.orderlines && 
                order.orderlines.length > 0 &&
                order.orderlines.every(line => line.quantity < 0)
            ) {
                if (typeof order.set_is_refund === 'function') {
                    order.set_is_refund(true);
                }
                return;
            }
        }

        const newOrder = this.pos.orders.find(o => !beforeOrders.some(b => b.uid === o.uid));
        if (newOrder && typeof newOrder.set_is_refund === 'function') {
            newOrder.set_is_refund(true);
        }
    },
});
