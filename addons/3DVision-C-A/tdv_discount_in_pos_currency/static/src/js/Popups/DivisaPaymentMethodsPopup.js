/** @odoo-module **/

import { AbstractAwaitablePopup } from "@point_of_sale/app/popup/abstract_awaitable_popup";
import { useState } from "@odoo/owl";

export class DivisaPaymentMethodsPopup extends AbstractAwaitablePopup {
    static template = "tdv_discount_in_pos_currency.DivisaPaymentMethodsPopup";

    setup() {
        super.setup();
        const pos = this.env.services.pos;
        // Asegurar que siempre sea un array de IDs
        let specialIds = pos.config.special_discount_payment_method_ids;
        if (Array.isArray(specialIds)) {
            // Puede ser un array de objetos o de IDs
            if (specialIds.length > 0 && typeof specialIds[0] === 'object' && specialIds[0].id) {
                specialIds = specialIds.map(pm => pm.id);
            }
        } else {
            specialIds = [];
        }
        // Obtener los métodos de pago especiales (disabled)
        this.specialPaymentMethods = pos.payment_methods.filter(pm =>
            specialIds.includes(pm.id)
        );
        // Obtener el monto total a distribuir
        this.totalAmount = pos.get_order()?.get_currency_amount?.() || 0;
        // Estado reactivo para los montos
        this.amounts = useState(
            Object.fromEntries(this.specialPaymentMethods.map(pm => [pm.id, 0]))
        );
        this.error = useState({ msg: "" });
        // Guardar el estado original de las líneas de pago especiales
        const order = pos.get_order();
        this._originalDivisaLines = order.paymentlines
            .filter(line => this.specialPaymentMethods.some(pm => pm.id === line.payment_method.id))
            .map(line => ({
                payment_method_id: line.payment_method.id,
                amount: line.amount,
            }));
        // Esperar a que el DOM esté listo para agregar la validación
        setTimeout(() => {
            document.querySelectorAll('.form-control[type="number"]').forEach(input => {
                input.addEventListener('keydown', function(event) {
                    if (event.key === '-' || event.keyCode === 189 || event.keyCode === 109) {
                        event.preventDefault();
                    }
                });
                input.addEventListener('input', function(event) {
                    if (this.value.includes('-')) {
                        this.value = this.value.replace(/-/g, '');
                    }
                });
            });
        }, 0);
    }

    get totalEntered() {
        return Object.values(this.amounts).reduce((a, b) => parseFloat(a) + parseFloat(b), 0);
    }

    onInputChange(paymentMethodId, ev) {
        let value = ev.target.value.replace(',', '.');
        this.amounts[paymentMethodId] = value === '' ? 0 : parseFloat(value);
        this.error.msg = "";
        // --- Actualizar líneas de pago en tiempo real ---
        const pos = this.env.services.pos;
        const order = pos.get_order();
        for (const [pm_id, amount] of Object.entries(this.amounts)) {
            const paymentMethod = pos.payment_methods.find(pm => pm.id == pm_id);
            if (!paymentMethod) continue;
            const existingLine = order.paymentlines.find(line => line.payment_method && line.payment_method.id == paymentMethod.id);
            if (amount > 0) {
                if (existingLine) {
                    existingLine.set_amount(amount);
                    existingLine.is_divisa_special = true;
                    existingLine.node && existingLine.node.setAttribute && existingLine.node.setAttribute('data-is-divisa-special', '1');
                } else {
                    order.add_paymentline(paymentMethod);
                    order.selected_paymentline.set_amount(amount);
                    order.selected_paymentline.is_divisa_special = true;
                    order.selected_paymentline.node && order.selected_paymentline.node.setAttribute && order.selected_paymentline.node.setAttribute('data-is-divisa-special', '1');
                }
            } else if (existingLine) {
                order.remove_paymentline(existingLine, {force: true});
            }
        }
    }

    async confirm() {
        if (Math.abs(this.totalEntered - this.totalAmount) > 0.01) {
            this.error.msg = `La suma debe ser exactamente ${this.getCurrencySymbol()}${this.totalAmount}`;
            return;
        }
        // GUARDAR EL VALOR EN LA ORDEN
        const pos = this.env.services.pos;
        const order = pos.get_order();
        order.set_currency_amount(this.totalEntered);

        // Confirmar: no hace falta restaurar nada, los cambios ya están hechos en tiempo real
        this.props.close({ confirmed: true, payload: { distribution: { ...this.amounts } } });
    }

    onCancel() {
        const pos = this.env.services.pos;
        const order = pos.get_order();
        // Eliminar todas las líneas de pago especiales
        order.paymentlines
            .filter(line => this.specialPaymentMethods.some(pm => pm.id === line.payment_method.id))
            .forEach(line => order.remove_paymentline(line, {force: true}));
        // Restaurar las líneas originales
        this._originalDivisaLines.forEach(lineInfo => {
            const paymentMethod = pos.payment_methods.find(pm => pm.id === lineInfo.payment_method_id);
            if (paymentMethod) {
                order.add_paymentline(paymentMethod);
                order.selected_paymentline.set_amount(lineInfo.amount);
                order.selected_paymentline.is_divisa_special = true;
            }
        });
        this.props.close({ confirmed: false });
    }

    // refreshDivisaPayments() {
    //     const pos = this.env.services.pos;
    //     const order = pos.get_order();
    //     // Eliminar todas las líneas de pago de los métodos especiales
    //     order.paymentlines
    //         .filter(line => this.specialPaymentMethods.some(pm => pm.id === line.payment_method.id))
    //         .forEach(line => order.remove_paymentline(line));
    //     this.props.close({ confirmed: false, payload: null });
    // }

    getCurrencySymbol() {
        const pos = this.env.services.pos;
        const mode = pos.config.currency_discount_mode;
        if (mode === 'secondary' && pos.secondCurrency && pos.secondCurrency.symbol) {
            return pos.secondCurrency.symbol;
        } else if (mode === 'main' && pos.currency && pos.currency.symbol) {
            return pos.currency.symbol;
        }
        // Fallback
        return '$';
    }

    getFormattedValue(value) {
        if (typeof value !== 'number') value = parseFloat(value);
        if (isNaN(value)) return '';
        // Formateo manual: separador de miles punto, decimales coma
        const parts = value.toFixed(2).split('.');
        parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, '.');
        return parts.join(',');
    }
} 