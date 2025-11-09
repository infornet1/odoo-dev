/** @odoo-module **/
import { useState, onWillUpdateProps, onMounted } from "@odoo/owl";
import { OrderWidget } from "@point_of_sale/app/generic_components/order_widget/order_widget";
import { patch } from "@web/core/utils/patch";

patch(OrderWidget, {
    props: {
        ...OrderWidget.props,
        calculatedRef: { type: String, optional: true },
        hasAnyLineDiscount: { type: Boolean, optional: true },
        orderLineDiscounts: { type: Array, optional: true },
        // Props adicionales para evitar error OWL
        calculatedRefPrincipal: { type: [String, Number], optional: true },
        currencyDiscountMode: { type: String, optional: true },
        enableSpecialDiscount: { type: Boolean, optional: true },
    },
    setup() {
        console.log('[OrderWidget PATCH] Widget personalizado cargado');
        super.setup && super.setup();
        this.el?.addEventListener('forceUpdate', () => {
            console.log('[OrderWidget] Evento forceUpdate recibido, forzando render...');
            this.render();
        });

        if (this.props.order) {
            this._assignOrderlineListeners(this.props.order);
            // DEPURACIÓN: Verificar si alguna línea no tiene get_discount
            this.props.order.orderlines.forEach(line => {
                if (typeof line.get_discount !== "function") {
                    console.error("[OrderWidget][Depuración] Línea sin get_discount:", line);
                }
            });
        }

        // Inicializa el prop hasAnyLineDiscount
        if (this.props.order) {
            // DEPURACIÓN: Verificar en cada render
            this.props.order.orderlines.forEach((line, idx) => {
                if (!line || typeof line.get_discount !== "function") {
                    console.error(`[OrderWidget][Depuración][Render] Línea inválida o sin get_discount en render (índice ${idx}):`, line, new Error().stack);
                }
            });
        }
        this.props.hasAnyLineDiscount = this.props.order ? this.props.order.orderlines.filter(line => line && typeof line.get_discount === "function").some(line => Number(line.get_discount()) > 0.0001) : false;
        this.props.orderLineDiscounts = this.props.order ? this.props.order.orderlines.models.filter(line => line && typeof line.get_discount === "function").map((line, idx) => line.get_discount()) : [];

        onWillUpdateProps((nextProps) => {
            if (nextProps.order !== this.props.order) {
                this._removeOrderlineListeners(this.props.order);
                this._assignOrderlineListeners(nextProps.order);
            }
            // Actualiza el prop hasAnyLineDiscount
            nextProps.hasAnyLineDiscount = nextProps.order ? nextProps.order.orderlines.filter(line => line && typeof line.get_discount === "function").some(line => Number(line.get_discount()) > 0.0001) : false;
            nextProps.orderLineDiscounts = nextProps.order ? nextProps.order.orderlines.models.filter(line => line && typeof line.get_discount === "function").map(line => line.get_discount()) : [];
            this.props = nextProps;
            this.render();
        });

        console.log('[OrderWidget] Setup ejecutado.');

        onMounted(() => {
            setTimeout(() => {
                const order = this.props.order;
                if (!order) return;
                const ref = order.get_discount_special_amount_formatted();
                // Solo muestra si hay Ref y no hay descuento
                let refDiv = document.getElementById('tdv-ref-debug');
                if (ref) {
                    if (!refDiv) {
                        refDiv = document.createElement('div');
                        refDiv.id = 'tdv-ref-debug';
                        refDiv.style = "background: yellow; color: red; font-size: 2em; border: 2px solid black; z-index: 9999; position: fixed; top: 10px; right: 10px;";
                        document.body.appendChild(refDiv);
                    }
                    refDiv.innerHTML = `REF DEBUG: ${ref}`;
                } else {
                    if (refDiv) refDiv.remove();
                }
            }, 500);
        });
    },
    _assignOrderlineListeners(order) {
        if (!order) return;
        order.orderlines.on('change', this._onOrderLineChange, this);
        order.orderlines.on('add', this._onOrderLineChange, this);
        order.orderlines.on('remove', this._onOrderLineChange, this);
    },
    _removeOrderlineListeners(order) {
        if (!order) return;
        order.orderlines.off('change', this._onOrderLineChange, this);
        order.orderlines.off('add', this._onOrderLineChange, this);
        order.orderlines.off('remove', this._onOrderLineChange, this);
    },
    _onOrderLineChange() {
        this.render();
        console.log('[OrderWidget] Forzando render tras cambio en línea');
    },
    _subscribeToOrder() {
        // Este método puede ser vacío o mantener suscripciones para otras lógicas si existen
        // Para el Ref, no necesitamos suscripción aquí ya que viene como prop
    },
    _unsubscribeFromOrder() {
        // Este método puede ser vacío o mantener lógica de desuscripción para otras lógicas si existen
    },
    getCalculatedRef() {
        const order = this.props.order;
        if (!order) return '';
        if (order.orderlines.some(line => Number(line.get_discount()) > 0.0001)) {
            return '';
        }
        return order.get_discount_special_amount_formatted();
    },
    getCurrencyAmountDisplay() {
        const order = this.props.order;
        if (!order) return '';
        const amount = order.get_currency_amount ? order.get_currency_amount() : 0;
        if (!amount) return '';
        let symbol = '';
        if (order.pos) {
            if (order.pos.config.currency_discount_mode === 'secondary') {
                // Use secondary currency symbol
                if (order.get_secondary_currency_id && order.pos.currencies_by_id) {
            const currency_id = order.get_secondary_currency_id();
            if (currency_id && order.pos.currencies_by_id[currency_id]) {
                symbol = order.pos.currencies_by_id[currency_id].symbol;
                    }
                }
            } else {
                // Use main currency symbol
                symbol = order.pos.currency ? order.pos.currency.symbol : '';
            }
        }
        return `Currency Amount: ${symbol} ${amount.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    }
});

// Método seguro para validar si alguna línea tiene descuento
OrderWidget.prototype.hasAnyLineDiscount = function() {
    const order = this.props.order;
    if (!order) return false;
    let error = false;
    order.orderlines.forEach((line, idx) => {
        if (!line || typeof line.get_discount !== "function") {
            console.error(`[OrderWidget][Depuración][hasAnyLineDiscount] Línea inválida o sin get_discount (índice ${idx}):`, line, new Error().stack);
            error = true;
        }
    });
    if (error) return false;
    const result = order.orderlines.filter(line => line && typeof line.get_discount === "function").some(line => Number(line.get_discount()) > 0.0001);
    console.log('[OrderWidget][hasAnyLineDiscount] ¿Hay descuento en alguna línea?', result, order.orderlines.filter(line => line && typeof line.get_discount === "function").map(l => l.get_discount()));
    return result;
};

// DEPURACIÓN: Hook global para detectar cambios después de validar la orden
if (window && window.odoo && window.odoo.__DEBUG__POS__) {
    const origShowScreen = window.odoo.__DEBUG__POS__.PosComponent.prototype.showScreen;
    window.odoo.__DEBUG__POS__.PosComponent.prototype.showScreen = function(screenName, ...args) {
        if (screenName === 'ReceiptScreen' || screenName === 'PaymentScreen') {
            const order = this.env.services.pos.get_order && this.env.services.pos.get_order();
            if (order && order.orderlines) {
                order.orderlines.forEach((line, idx) => {
                    if (!line || typeof line.get_discount !== "function") {
                        console.error(`[OrderWidget][Depuración][showScreen] Línea inválida o sin get_discount tras validación (índice ${idx}):`, line, new Error().stack);
                    }
                });
            }
        }
        return origShowScreen.call(this, screenName, ...args);
    };
} 