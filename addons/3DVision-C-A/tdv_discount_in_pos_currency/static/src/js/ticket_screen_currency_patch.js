/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { useService } from "@web/core/utils/hooks";

patch(TicketScreen.prototype, {
    async setup() {
        super.setup && super.setup();
        if (this.orders && this.orders.length) {
            const orderIds = this.orders.map(order => order.id).filter(Boolean);
            if (orderIds.length) {
                try {
                    const response = await fetch('/pos/currency_amounts', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({order_ids: orderIds}),
                        credentials: 'include'
                    });
                    const data = await response.json();
                    let changed = false;
                    for (const order of this.orders) {
                        const before = order.currency_amount;
                        if (order.id && data[order.id] !== undefined && order.currency_amount !== data[order.id]) {
                            order.currency_amount = data[order.id];
                            changed = true;
                        }
                    }
                    if (changed && this.render) {
                        this.render();
                    }
                } catch (e) {
                    // Ignora errores de red
                }
            }
        }
    },
}); 