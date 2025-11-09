/** @odoo-module **/

import { AbstractAwaitablePopup } from "@point_of_sale/app/popup/abstract_awaitable_popup";
import { useState } from "@odoo/owl";

export class DivisaPaymentMethodsPopup extends AbstractAwaitablePopup {
    static template = "tdv_pos_currency_price_list.DivisaPaymentMethodsPopup";

    setup() {
        super.setup();
        
        const pos = this.env.services.pos;
        
        let specialIds = pos.config.special_currency_payment_method_ids;
        if (Array.isArray(specialIds)) {
            if (specialIds.length > 0 && typeof specialIds[0] === 'object' && specialIds[0].id) {
                specialIds = specialIds.map(pm => pm.id);
            }
        } else {
            specialIds = [];
        }
        
        this.specialPaymentMethods = pos.payment_methods.filter(pm =>
            specialIds.includes(pm.id)
        );
        
        this.totalAmount = pos.get_order()?.get_total_with_tax() || 0;
        
        this.amounts = useState(
            Object.fromEntries(this.specialPaymentMethods.map(pm => [pm.id, 0]))
        );
        this.error = useState({ msg: "" });
        
        const order = pos.get_order();
        this._originalDivisaLines = order.paymentlines
            .filter(line => this.specialPaymentMethods.some(pm => pm.id === line.payment_method.id))
            .map(line => ({
                payment_method_id: line.payment_method.id,
                amount: line.amount,
            }));
        
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
        
        const pos = this.env.services.pos;
        const order = pos.get_order();
        
        for (const [pm_id, amount] of Object.entries(this.amounts)) {
            const paymentMethod = pos.payment_methods.find(pm => pm.id == pm_id);
            if (!paymentMethod) continue;
            
            const existingLine = order.paymentlines.find(line => 
                line.payment_method && line.payment_method.id == paymentMethod.id
            );
            
            if (amount > 0) {
                if (existingLine) {
                    existingLine.set_amount(amount);
                    existingLine.is_divisa_special = true;
                    existingLine.node && existingLine.node.setAttribute && 
                    existingLine.node.setAttribute('data-is-divisa-special', '1');
                } else {
                    order.add_paymentline(paymentMethod);
                    order.selected_paymentline.set_amount(amount);
                    order.selected_paymentline.is_divisa_special = true;
                    order.selected_paymentline.node && order.selected_paymentline.node.setAttribute && 
                    order.selected_paymentline.node.setAttribute('data-is-divisa-special', '1');
                }
            } else if (existingLine) {
                order.remove_paymentline(existingLine, {force: true});
            }
        }
    }

    async confirm() {
        if (this.totalEntered <= 0) {
            this.notification.add('El monto debe ser mayor a 0', { type: 'warning' });
            return;
        }

        if (Math.abs(this.totalEntered - this.totalAmount) > 0.01) {
            this.notification.add(`La suma debe ser exactamente ${this.getCurrencySymbol()}${this.getFormattedValue(this.totalAmount)}`, { type: 'warning' });
            return;
        }

        const pos = this.env.services.pos;
        const order = pos.get_order();
        
        if (typeof order.set_currency_amount === 'function') {
            order.set_currency_amount(this.totalEntered);
        }

        this.props.close({ confirmed: true, payload: { distribution: { ...this.amounts } } });
    }

    onCancel() {
        const pos = this.env.services.pos;
        const order = pos.get_order();
        
        order.paymentlines
            .filter(line => this.specialPaymentMethods.some(pm => pm.id === line.payment_method.id))
            .forEach(line => order.remove_paymentline(line, {force: true}));
        
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

    getCurrencySymbol() {
        const pos = this.env.services.pos;
        const mode = pos.config.currency_discount_mode;
        if (mode === 'secondary' && pos.secondCurrency && pos.secondCurrency.symbol) {
            return pos.secondCurrency.symbol;
        } else if (mode === 'main' && pos.currency && pos.currency.symbol) {
            return pos.currency.symbol;
        }

        return '$';
    }

    getFormattedValue(value) {
        if (typeof value !== 'number') value = parseFloat(value);
        if (isNaN(value)) return '';
        
        const parts = value.toFixed(2).split('.');
        parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, '.');
        return parts.join(',');
    }
}
