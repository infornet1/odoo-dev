/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";

patch(TicketScreen.prototype, {
    async onDoRefund() {
        const order = this.getSelectedOrder();
        const destinationOrder = this.props.destinationOrder;
        if (order.num_factura) {
            destinationOrder.num_factura = order.num_factura;
            destinationOrder.fiscal_date = order.fiscal_date;
            destinationOrder.fiscal_serial = order.fiscal_serial;
        } else {
            destinationOrder.num_factura = null;
            destinationOrder.fiscal_date = null;
            destinationOrder.fiscal_serial = null;
        }
        await super.onDoRefund();
    }
});
