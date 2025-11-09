/** @odoo-module **/

import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { DivisaPaymentMethodsPopup } from "@tdv_discount_in_pos_currency/js/Popups/DivisaPaymentMethodsPopup";
import { useService } from "@web/core/utils/hooks";
import { Order } from "@point_of_sale/app/store/models";
import { patch as patchModel } from "@web/core/utils/patch";

// Guardar referencia al método original antes del patch
const originalAddNewPaymentLine = PaymentScreen.prototype.addNewPaymentLine;

// Definir la variable en el scope global antes del patch
const originalUpdateSelectedPaymentline = PaymentScreen.prototype.updateSelectedPaymentline;

patch(PaymentScreen.prototype, {
    setup() {
        super.setup && super.setup();
        this.popup = useService("popup");
        this.notification = useService("notification");
        // Guardar ids de métodos de pago a deshabilitar (asegúrate que sean IDs)
        this.disabledPaymentMethodIds = Array.isArray(this.pos.config.special_discount_payment_method_ids)
            ? this.pos.config.special_discount_payment_method_ids
            : (this.pos.config.special_discount_payment_method_ids || []).map(pm => pm.id);
        // Parcheo visual: forzar el estilo gris y deshabilitado
        setTimeout(() => {
            const buttons = document.querySelectorAll('.paymentmethod');
            buttons.forEach(btn => {
                const paymentName = btn.querySelector('.payment-name')?.textContent?.trim();
                const paymentMethod = this.pos.payment_methods.find(pm => pm.name === paymentName);
                if (!paymentMethod) return;
                const order = this.pos.get_order();
                // Si la orden es un reembolso, no deshabilitar ningún método de pago
                if (order && typeof order.isRefund === 'function' && order.isRefund()) {
                    btn.classList.remove('disabled');
                    btn.style.pointerEvents = '';
                    btn.style.opacity = '';
                    return;
                }
                // Deshabilitar métodos especiales siempre
                if (this.disabledPaymentMethodIds.includes(paymentMethod.id)) {
                    btn.classList.add('disabled');
                    btn.style.pointerEvents = 'none';
                    btn.style.opacity = '0.5';
                } else {
                    // Métodos normales: deshabilitar si no se ha cubierto el monto de divisa
                    const requiredDivisa = order.get_currency_amount();
                    if (requiredDivisa > 0) {
                        let paidDivisa = 0;
                        for (const line of order.paymentlines) {
                            if (this.disabledPaymentMethodIds.includes(line.payment_method.id)) {
                                paidDivisa += line.amount;
                            }
                        }
                        if (Math.abs(paidDivisa - requiredDivisa) > 0.01) {
                            btn.classList.add('disabled');
                            btn.style.pointerEvents = 'none';
                            btn.style.opacity = '0.5';
                        } else {
                            btn.classList.remove('disabled');
                            btn.style.pointerEvents = '';
                            btn.style.opacity = '';
                        }
                    } else {
                        btn.classList.remove('disabled');
                        btn.style.pointerEvents = '';
                        btn.style.opacity = '';
                    }
                }
            });
        }, 500);
    },
    getFormattedValue(value) {
        if (typeof value !== 'number') value = parseFloat(value);
        if (isNaN(value)) return '';
        // Formateo manual: separador de miles punto, decimales coma
        const parts = value.toFixed(2).split('.');
        parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, '.');
        return parts.join(',');
    },
    get discountSpecialNote() {
        const order = this.pos.get_order();
        if (order && typeof order.get_currency_amount === "function") {
            const amount = order.get_currency_amount();
            if (amount !== null && amount !== undefined && !isNaN(amount)) {
                const formattedValue = this.getFormattedValue(amount);
                return `Nota: Se debe pagar ${this.getCurrencySymbol()}${formattedValue} en divisa.`;
            }
        }
        return "";
    },
    get showDivisaButton() {
        // Mostrar el botón solo si hay un monto en currency_amount
        const order = this.pos.get_order();
        return order && typeof order.get_currency_amount === "function" && order.get_currency_amount() > 0;
    },
    paymentMethodIsDisabled(paymentMethod) {
        // Si es método especial, no deshabilitar aquí
        if (this.disabledPaymentMethodIds.includes(paymentMethod.id)) {
            return false;
        }
        // Métodos normales: deshabilitar si hay currency_amount pendiente
        const order = this.pos.get_order();
        // Si la orden es un reembolso, no deshabilitar ningún método de pago
        if (order && typeof order.isRefund === 'function' && order.isRefund()) {
            return false;
        }
        if (order && typeof order.get_currency_amount === "function") {
            const requiredDivisa = order.get_currency_amount();
            if (requiredDivisa > 0) {
                // Sumar lo pagado en métodos especiales
                let paidDivisa = 0;
                for (const line of order.paymentlines) {
                    if (this.disabledPaymentMethodIds.includes(line.payment_method.id)) {
                        paidDivisa += line.amount;
                    }
                }
                // Si no se ha cubierto el total, deshabilitar métodos normales
                if (Math.abs(paidDivisa - requiredDivisa) > 0.01) {
                    return true;
                }
            }
        }
        return false;
    },
    refreshNormalPaymentButtons() {
        const buttons = document.querySelectorAll('.paymentmethod');
        buttons.forEach(btn => {
            const paymentName = btn.querySelector('.payment-name')?.textContent?.trim();
            const paymentMethod = this.pos.payment_methods.find(pm => pm.name === paymentName);
            if (!paymentMethod) return;
            // Solo métodos normales
            if (!this.disabledPaymentMethodIds.includes(paymentMethod.id)) {
                const order = this.pos.get_order();
                let requiredDivisa = 0;
                let paidDivisa = 0;
                if (order && typeof order.get_currency_amount === "function") {
                    requiredDivisa = order.get_currency_amount();
                    if (requiredDivisa > 0) {
                        for (const line of order.paymentlines) {
                            if (this.disabledPaymentMethodIds.includes(line.payment_method.id)) {
                                paidDivisa += line.amount;
                            }
                        }
                    }
                }
                if (requiredDivisa > 0 && Math.abs(paidDivisa - requiredDivisa) > 0.01) {
                    btn.classList.add('disabled');
                    btn.style.pointerEvents = 'none';
                    btn.style.opacity = '0.5';
                } else {
                    btn.classList.remove('disabled');
                    btn.style.pointerEvents = '';
                    btn.style.opacity = '';
                }
            }
        });
    },
    addNewPaymentLine(paymentMethod) {
        // Validar tanto métodos normales como especiales por lógica, no solo visual
        // Si es especial y está deshabilitado por config, bloquear
        if (this.disabledPaymentMethodIds.includes(paymentMethod.id)) {
            this.notification.add('Este método de pago especial está deshabilitado para descuento en divisa.', { type: 'warning' });
            return false;
        }
        // Si es normal y la lógica lo deshabilita, bloquear
        if (this.paymentMethodIsDisabled(paymentMethod)) {
            this.notification.add('Este método de pago está deshabilitado hasta que se cargue la divisa.', { type: 'warning' });
            return false;
        }
        const result = originalAddNewPaymentLine.call(this, paymentMethod);
        setTimeout(() => this.refreshNormalPaymentButtons(), 0);
        return result;
    },
    deletePaymentLine(paymentLineOrCid) {
        const order = this.pos.get_order();
        // Si recibes un cid, obtén el objeto real
        const paymentLine = typeof paymentLineOrCid === 'object' ? paymentLineOrCid : order.paymentlines.find(l => l.cid === paymentLineOrCid);
        if (!paymentLine) return;
        if (paymentLine.is_divisa_special) {
            this.notification.add('No puede eliminar este método de pago especial desde aquí. Use el popup para modificarlo o cargue de nuevo la cantidad en divisas.', { type: 'warning' });
            return;
        }
        order.remove_paymentline(paymentLine);
        setTimeout(() => this.refreshNormalPaymentButtons(), 0);
    },
    async showDivisaPaymentMethodsPopup() {
        const { confirmed } = await this.popup.add(DivisaPaymentMethodsPopup, {});
        setTimeout(() => this.refreshNormalPaymentButtons(), 0);
        // Ya no es necesario eliminar líneas aquí, el popup restaura el estado si se cancela
        // Si confirmed, no hagas nada: ya está actualizado en tiempo real
    },
    updateSelectedPaymentline(amount = false) {
        // Bloquear si no hay línea seleccionada
        if (!this.selectedPaymentLine) {
            if (this.notification && typeof this.notification.add === 'function') {
                this.notification.add('Debe seleccionar un método de pago válido para ingresar un monto.', { type: 'warning' });
            }
            return;
        }
        // Bloquear edición de líneas especiales
        if (this.selectedPaymentLine.is_divisa_special) {
            if (this.notification && typeof this.notification.add === 'function') {
                this.notification.add('No puede editar este método de pago especial desde aquí. Use el popup para modificarlo.', { type: 'warning' });
            }
            return;
        }
        // Llamar al método original para métodos normales
        return originalUpdateSelectedPaymentline.call(this, amount);
    },
    getCurrencySymbol() {
        const mode = this.pos.config.currency_discount_mode;
        if (mode === 'secondary' && this.pos.secondCurrency && this.pos.secondCurrency.symbol) {
            return this.pos.secondCurrency.symbol;
        } else if (mode === 'main' && this.pos.currency && this.pos.currency.symbol) {
            return this.pos.currency.symbol;
        }
        // Fallback
        return '$';
    },
});

// --- Patch para limpiar todas las líneas de pago al cambiar la cantidad en divisa ---
const originalSetDiscountSpecialAmount = Order.prototype.set_discount_special_amount;
patchModel(Order.prototype, {
    set_discount_special_amount(amount) {
        // Limpiar TODAS las líneas de pago antes de actualizar el monto
        this.paymentlines.slice().forEach(line => this.remove_paymentline(line, {force: true}));
        return originalSetDiscountSpecialAmount.call(this, amount);
    },
});

// --- Patch para evitar seleccionar o editar líneas especiales ---
if (!PaymentScreen.prototype._divisa_patch_applied) {
    const originalSelectLine = PaymentScreen.prototype.selectLine;
    PaymentScreen.prototype.selectLine = function(line) {
        if (line && line.is_divisa_special) {
            if (this.notification && typeof this.notification.add === 'function') {
                this.notification.add('No puede editar este método de pago especial desde aquí. Use el popup para modificarlo.', { type: 'warning' });
            }
            return;
        }
        return originalSelectLine.call(this, line);
    };
    PaymentScreen.prototype._divisa_patch_applied = true;
}

// --- Patch para evitar eliminar líneas especiales ---
const originalRemovePaymentLine = Order.prototype.remove_paymentline;
patchModel(Order.prototype, {
    remove_paymentline(paymentline, opts = {}) {
        // Solo bloquear si la línea es especial y no se pasa {force: true}
        if (paymentline && paymentline.is_divisa_special && !opts.force) {
            if (this.pos && this.pos.notification && typeof this.pos.notification.add === 'function') {
                this.pos.notification.add('No puede eliminar este método de pago especial desde aquí. Use el popup para modificar o eliminar.', { type: 'warning' });
            }
            return;
        }
        // Si NO es especial, permitir siempre la eliminación (sin importar opts.force)
        return originalRemovePaymentLine.call(this, paymentline, opts);
    },
}); 
