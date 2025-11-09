/** @odoo-module **/

import { OrderWidget } from "@point_of_sale/app/generic_components/order_widget/order_widget";
import { patch } from "@web/core/utils/patch";

patch(OrderWidget.prototype, {
    setup() {
        if (typeof super.setup === 'function') {
            super.setup();
        }
        try {
            Object.defineProperty(this, 'order', {
                configurable: true,
                enumerable: true,
                get: () => {
                    try {
                        const fromProps = this.props && this.props.order;
                        if (fromProps) return fromProps;
                        const fromStore = this.env?.services?.pos && this.env.services.pos.get_order && this.env.services.pos.get_order();
                        return fromStore || { get_orderlines: () => [] };
                    } catch (_e) {
                        return { get_orderlines: () => [] };
                    }
                },
            });
            Object.defineProperty(this, 'orderlines', {
                configurable: true,
                enumerable: true,
                get: () => {
                    try {
                        const order = (this.props && this.props.order)
                            || (this.env?.services?.pos && this.env.services.pos.get_order && this.env.services.pos.get_order());
                        return order && typeof order.get_orderlines === 'function' ? order.get_orderlines() : [];
                    } catch (_e) {
                        return [];
                    }
                },
            });
        } catch (_e) {}
    },
    get order() {
        try {
            const fromProps = this.props && this.props.order;
            if (fromProps) return fromProps;
            const fromStore = this.env?.services?.pos && this.env.services.pos.get_order && this.env.services.pos.get_order();
            return fromStore || { get_orderlines: () => [] };
        } catch (_e) {
            return { get_orderlines: () => [] };
        }
    },
    get orderlines() {
        try {
            const order = (this.props && this.props.order)
                || (this.env?.services?.pos && this.env.services.pos.get_order && this.env.services.pos.get_order());
            return order && typeof order.get_orderlines === 'function' ? order.get_orderlines() : [];
        } catch (_e) {
            return [];
        }
    },
});


