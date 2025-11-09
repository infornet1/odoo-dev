/** @odoo-module **/

import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { _t } from "@web/core/l10n/translation";
import { usePos } from "@point_of_sale/app/store/pos_hook";

// Función utilitaria para convertir string de moneda a número
function parseCurrencyToNumber(value) {
    if (typeof value === "number") return value;
    if (typeof value === "string") {
        // Elimina símbolos de moneda, espacios, y cambia coma por punto
        let cleaned = value.replace(/[^0-9,\.]/g, '').replace(',', '.');
        let num = parseFloat(cleaned);
        return isNaN(num) ? 0 : num;
    }
    return 0;
}

export class DiscountButton extends Component {
    static template = "DiscountButton";

    setup() {
        this.popup = useService("popup");
        this.notification = useService("notification");
        this.pos = usePos();

        // Suscribirse a los cambios de la orden activa de forma robusta
        this._orderChangeHandler = () => this.render();

        onMounted(() => {
            const order = this.pos.get_order();
            if (order && order.on) {
                order.on('change', null, this._orderChangeHandler);
            }
        });

        onWillUnmount(() => {
            const order = this.pos.get_order();
            if (order && order.off) {
                order.off('change', null, this._orderChangeHandler);
            }
        });
    }

    async onClick() {
        const order = this.pos.get_order();
        if (!order) return;

        if (!order.get_orderlines || order.get_orderlines().length === 0) {
            await this.popup.add(ErrorPopup, {
                title: _t("No products"),
                body: _t("You must add at least one product before applying the discount."),
            });
            return;
        }

        let current_discount = 0;
        if (typeof order.get_discount_amount === "function") {
            current_discount = order.get_discount_amount() || 0;
        }

        const { confirmed, payload: amount } = await this.popup.add(NumberPopup, {
            title: _t("Enter the amount to pay in currency"),
            startingValue: current_discount,
        });

        console.log("[Descuento Especial] Confirmado:", confirmed, "Valor ingresado:", amount);

        if (confirmed) {
            // === RESETEAR DESCUENTOS DE TODAS LAS LÍNEAS ANTES DE APLICAR EL NUEVO DESCUENTO ===
            order.get_orderlines().forEach(line => {
                line.set_discount(0);
            });

            // --- NUEVA LÓGICA: DISTINCIÓN ENTRE MONEDA PRINCIPAL Y SECUNDARIA ---
            const mode = this.pos.config.currency_discount_mode;

            // Permitir decimales con coma o punto
            let normalizedAmount = amount;
            if (typeof normalizedAmount === "string") {
                normalizedAmount = normalizedAmount.replace(',', '.');
            }
            let refValue = (normalizedAmount === '' || normalizedAmount === null || isNaN(normalizedAmount)) ? null : parseFloat(normalizedAmount);

            // Si el valor es negativo, lo forzamos a 0
            if (refValue < 0) {
                refValue = 0;
            }

            let porcentaje_descuento_pos = this.pos.config.discount_percentage || 0;
            let porcentaje_decimal = porcentaje_descuento_pos / 100;
            let total_divisas, cantidad_divisa_cargada, dctoPorProducto;

            if (mode === 'secondary') {
                // === Lógica moneda secundaria (actual) ===
                const total_bsf = order.get_total_with_tax();
                let tasa_cambio = this.pos.secondCurrency && this.pos.secondCurrency.rate ? this.pos.secondCurrency.rate : 1;
                if (tasa_cambio < 1) {
                    tasa_cambio = 1 / tasa_cambio;
                }
                const total_usd_real = total_bsf / tasa_cambio;
                total_divisas = total_usd_real;
                cantidad_divisa_cargada = refValue;
                dctoPorProducto = 1 - ((total_divisas - (cantidad_divisa_cargada * porcentaje_decimal)) / total_divisas);
                dctoPorProducto = dctoPorProducto * 100;
            } else if (mode === 'main') {
                // === Lógica moneda principal ===
                total_divisas = order.get_total_with_tax();
                cantidad_divisa_cargada = refValue;
                dctoPorProducto = 1 - ((total_divisas - (cantidad_divisa_cargada * porcentaje_decimal)) / total_divisas);
                dctoPorProducto = dctoPorProducto * 100;
            } else {
                // Si ninguno está activo, no aplicar descuento
                dctoPorProducto = 0;
            }

            // ===============================
            // AQUÍ SE MANDA EL DESCUENTO EN % A TODAS LAS LÍNEAS DE PRODUCTOS
            // ===============================
            const dctoPorProductoRedondeado = Math.round(dctoPorProducto * 1000) / 1000;
            order.get_orderlines().forEach(line => {
                line.set_discount(dctoPorProductoRedondeado);
            });

            this.notification.add(`Descuento aplicado a todas las líneas: ${dctoPorProductoRedondeado.toFixed(3)}%`, { type: "info" });

            // Solo guardar si es un número válido, distinto de null y no vacío
            if (refValue !== null && refValue !== '' && !isNaN(refValue)) {
                // Eliminar todas las líneas de pago antes de aplicar el nuevo monto
                order.paymentlines.slice().forEach(line => order.remove_paymentline(line, {force: true}));
                order.set_discount_special_amount(refValue);
                // Log explícito antes de setear currency_amount en la orden
                console.log('[DEBUG][DiscountButton] Llamando a set_currency_amount con:', refValue, 'UID:', order.uid);
                order.set_currency_amount(refValue);
                if (this.pos.config && this.pos.config.iface_table_management) {
                    try {
                        // Guardar la orden como draft en el backend SOLO si es restaurante
                        await fetch('/pos/draft/save', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({
                                uid: order.uid,
                                data: order.export_as_JSON(),
                                session_id: this.pos.pos_session.id,
                            }),
                            credentials: 'include'
                        });
                    } catch (e) {}
                }
                // Log explícito después de set_currency_amount
                console.log('[DEBUG][DiscountButton] Después de set_currency_amount, valor en order:', order.currency_amount, 'UID:', order.uid);
                this.pos.db.save_unpaid_order(order);
                this.pos.trigger && this.pos.trigger('change');
                const formattedValue = this.formatCurrencyValue(refValue);
                this.notification.add(`Se seleccionaron ${this.getCurrencySymbol()}${formattedValue} en divisa.`, { type: "info" });
            } else {
                order.set_discount_special_amount(null);
            }
        }
    }

    willUpdateProps(nextProps) {
        const order = this.pos.get_order();
        if (order) {
            console.log('[LOG] Valor actual de discount_special_amount al renderizar:', order.discount_special_amount);
        }
    }

    getCurrencySymbol() {
        const mode = this.pos.config.currency_discount_mode;
        if (mode === 'secondary' && this.pos.secondCurrency && this.pos.secondCurrency.symbol) {
            return this.pos.secondCurrency.symbol;
        } else if (mode === 'main' && this.pos.currency && this.pos.currency.symbol) {
            return this.pos.currency.symbol;
        }
        // Fallback
        return '$';
    }

    formatCurrencyValue(value) {
        if (typeof value !== 'number') value = parseFloat(value);
        if (isNaN(value)) return '';
        // Formateo manual: separador de miles punto, decimales coma
        const parts = value.toFixed(2).split('.');
        parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, '.');
        return parts.join(',');
    }
}

ProductScreen.addControlButton({
    component: DiscountButton,
    position: ["before", "SetFiscalPositionButton"],
    condition: function () {
        return this.pos?.config?.enable_special_discount;
    },
});

// --- Script para ocultar el Ref si hay descuento en alguna línea ---
setInterval(() => {
    // Busca el div del Ref (ajusta el selector si tu Ref tiene otra clase o estructura)
    const refDiv = document.querySelector('.order-summary');
    if (!refDiv) return;

    // Busca si hay alguna línea con descuento (ajusta el selector según tu estructura de líneas)
    const lines = Array.from(document.querySelectorAll('.product-line .discount, .orderline .discount'));
    const hasDiscount = lines.some(line => {
        const value = parseFloat(line.textContent.replace('%', '').replace(',', '.'));
        return value > 0;
    });

    // Oculta o muestra el Ref según corresponda
    refDiv.style.display = hasDiscount ? 'none' : '';
}, 500); 

// También exportar la función para usarla en el template XML
export function formatCurrencyValue(value) {
    if (typeof value !== 'number') value = parseFloat(value);
    if (isNaN(value)) return '';
    // Formateo manual: separador de miles punto, decimales coma
    const parts = value.toFixed(3).split('.');
    parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, '.');
    return parts.join(',');
} 