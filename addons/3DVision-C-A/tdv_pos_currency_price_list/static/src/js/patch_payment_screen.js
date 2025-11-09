/** @odoo-module **/

/**
 * PATCH PARA CONTROL DE DIVISA POR LISTA DE PRECIO
 * 
 * COMPORTAMIENTO:
 * - Cuando la lista de precio seleccionada está en la configuración del addon:
 *   ✅ Se muestra la nota de pago en divisa
 *   ✅ Se muestra el botón para abrir el popup de divisa
 *   ✅ Se bloquean TODOS los métodos de pago normales (forzar uso exclusivo de divisa)
 *   ✅ Solo se permiten los métodos de pago especiales configurados
 * 
 * - Cuando la lista de precio NO está en la configuración:
 *   ❌ No se muestra nada del control de divisa
 *   ✅ Todos los métodos de pago funcionan normalmente
 */

import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { DivisaPaymentMethodsPopup } from "@tdv_pos_currency_price_list/js/Popups/DivisaPaymentMethodsPopup";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { Order } from "@point_of_sale/app/store/models";
import { patch as patchModel } from "@web/core/utils/patch";

// Guardar referencia al método original antes del patch
const originalAddNewPaymentLine = PaymentScreen.prototype.addNewPaymentLine;
const originalUpdateSelectedPaymentline = PaymentScreen.prototype.updateSelectedPaymentline;

patch(PaymentScreen.prototype, {
    setup() {
        super.setup && super.setup();
        this.popup = useService("popup");
        this.notification = useService("notification");
        
        // Verificar si la funcionalidad está habilitada
        this.isCurrencyControlEnabled = this.pos.config.enable_currency_price_list_control || false;
        
        // Obtener las listas de precio configuradas
        this.currencyPriceListIds = Array.isArray(this.pos.config.currency_control_pricelist_ids)
            ? this.pos.config.currency_control_pricelist_ids.map(pl => pl.id || pl)
            : [];
        
        // Obtener los métodos de pago especiales configurados
        this.specialPaymentMethodIds = Array.isArray(this.pos.config.special_currency_payment_method_ids)
            ? this.pos.config.special_currency_payment_method_ids.map(pm => pm.id || pm)
            : [];
        
        // Aplicar parcheo visual si es necesario (sin retrasos)
        if (this.isCurrencyControlEnabled && this.currencyPriceListIds.length > 0) {
            this.applyVisualPatches();
        }
    },

    // Hook de OWL para cuando se monta el componente
    onMounted() {
        super.onMounted && super.onMounted();
        
        // Escuchar cambios en la orden usando el sistema de OWL
        if (this.pos && this.pos.get_order) {
            // Crear un observer para detectar cambios en la orden
            this.setupOrderObserver();
        }

        // Protección inmediata: interceptar clics sobre botones de pago
        // en fase de captura para evitar el breve lapso donde aún no se
        // aplicaron los parches visuales del DOM.
        this._paymentBtnGuard = (ev) => {
            // Buscar si el clic ocurrió en un botón de método de pago
            let node = ev.target;
            while (node && !(node.classList && node.classList.contains('paymentmethod'))) {
                node = node.parentElement;
            }
            if (!node) return;

            // Si el control no aplica, no hacemos nada
            if (!this.shouldShowDivisaControl) return;

            // Resolver el método de pago por nombre visible
            const paymentName = node.querySelector('.payment-name')?.textContent?.trim();
            if (!paymentName) return;
            const paymentMethod = this.pos.payment_methods.find(pm => pm.name === paymentName);
            if (!paymentMethod) return;

            // Determinar si este método debe estar bloqueado según la lógica
            const isSpecial = this.specialPaymentMethodIds.includes(paymentMethod.id);
            const isBlocked = isSpecial || this.paymentMethodIsDisabled(paymentMethod);
            if (isBlocked) {
                ev.stopPropagation();
                ev.preventDefault();
                // Bloqueo silencioso: no mostrar notificaciones
            }
        };
        document.addEventListener('click', this._paymentBtnGuard, true);
    },

    // Método para configurar el observer de la orden
    setupOrderObserver() {
        // Usar un intervalo para detectar cambios en la orden
        this.orderObserverInterval = setInterval(() => {
            const currentOrder = this.pos.get_order();
            if (currentOrder && currentOrder !== this.lastObservedOrder) {
                this.lastObservedOrder = currentOrder;
                this.refreshDivisaControl();
            }
            
            // Verificar si cambió la lista de precio
            if (currentOrder && currentOrder.pricelist_id) {
                const currentPricelistId = currentOrder.pricelist_id[0];
                if (currentPricelistId !== this.lastObservedPricelistId) {
                    this.lastObservedPricelistId = currentPricelistId;
                    this.refreshDivisaControl();
                }
            }
        }, 500); // Verificar cada 500ms
    },

    // Hook de OWL para limpiar recursos
    willUnmount() {
        super.willUnmount && super.willUnmount();
        
        // Limpiar el intervalo del observer
        if (this.orderObserverInterval) {
            clearInterval(this.orderObserverInterval);
            this.orderObserverInterval = null;
        }

        // Remover el guardia de clics si existe
        if (this._paymentBtnGuard) {
            document.removeEventListener('click', this._paymentBtnGuard, true);
            this._paymentBtnGuard = null;
        }
    },

    applyVisualPatches() {
        // Solo aplicar parches si el control de divisa está habilitado para la lista de precio actual
        if (!this.shouldShowDivisaControl) return;
        
        const buttons = document.querySelectorAll('.paymentmethod');
        
        buttons.forEach((btn, index) => {
            const paymentName = btn.querySelector('.payment-name')?.textContent?.trim();
            if (!paymentName) return;
            
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
            if (this.specialPaymentMethodIds.includes(paymentMethod.id)) {
                btn.classList.add('disabled');
                btn.style.pointerEvents = 'none';
                btn.style.opacity = '0.5';
            } else {
                // Métodos normales: SIEMPRE deshabilitar cuando se paga con divisa
                // Esto fuerza el uso exclusivo de los métodos especiales
                btn.classList.add('disabled');
                btn.style.pointerEvents = 'none';
                btn.style.opacity = '0.5';
            }
        });
    },

    getFormattedValue(value) {
        if (typeof value !== 'number') value = parseFloat(value);
        if (isNaN(value)) return '';
        // Formateo manual: separador de miles punto, decimales coma
        const parts = value.toFixed(2).split('.');
        parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, '.');
        return parts.join(',');
    },

    // Evita apilar notificaciones idénticas buscando el mismo texto visible
    showUniqueNotification(message, type = 'info') {
        try {
            // Buscar notificaciones visibles en el manager del cliente web
            const nodes = document.querySelectorAll('.o_notification_manager .o_notification');
            for (const el of nodes) {
                const txt = (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim();
                if (txt === message) {
                    return; // Ya hay una con el mismo texto
                }
            }
        } catch (e) {
            // Ignorar fallos del query; en el peor caso se mostrará solo una más
        }
        this.notification.add(message, { type });
    },

    // Propiedades para el template XML - REPLICANDO EXACTAMENTE LA LÓGICA DEL ADDON ORIGINAL
    get currencySpecialNote() {
        // Solo mostrar la nota si el control de divisa está habilitado para la lista de precio actual
        if (!this.shouldShowDivisaControl) {
            return "";
        }
        
        const order = this.pos.get_order();
        if (order) {
            // Mostrar el total de la orden
            const totalAmount = order.get_total_with_tax();
            if (totalAmount > 0) {
                const formattedValue = this.getFormattedValue(totalAmount);
                return `${_t('Note: You must pay')} ${this.getCurrencySymbol()}${formattedValue} ${_t('in currency.')}`;
            }
        }
        return "";
    },

    // Propiedad computada que se actualiza dinámicamente
    get shouldShowDivisaControl() {
        // Solo verificar si la funcionalidad está habilitada
        if (!this.isCurrencyControlEnabled || this.currencyPriceListIds.length === 0) {
            return false;
        }
        
        // Obtener la orden actual
        const order = this.pos.get_order();
        // Fallback temprano: si aún no se pobló la pricelist de la orden,
        // usar la lista de precio de la sesión/configuración para evitar
        // la ventana de tiempo donde se puede clicar.
        if (!order || !order.pricelist || !order.pricelist.id) {
            const configPricelistId = Array.isArray(this.pos.config.pricelist_id)
                ? this.pos.config.pricelist_id[0]
                : this.pos.config.pricelist_id;
            if (configPricelistId) {
                return this.currencyPriceListIds.includes(configPricelistId);
            }
            // Si no hay ningún dato, no mostrar el control
            return false;
        }

        // Si la orden es un reembolso, no mostrar el control de divisa
        if (order && typeof order.isRefund === 'function' && order.isRefund()) {
            return false;
        }

        // Obtener el ID de la lista de precio de la orden actual
        const currentOrderPricelistId = order.pricelist.id;
        
        // Verificar si la lista de precio actual de la orden está en las configuradas
        const result = this.currencyPriceListIds.includes(currentOrderPricelistId);
        // console.log("🔧 SIMPLE - Lista actual de la orden:", currentOrderPricelistId, "Configuradas:", this.currencyPriceListIds, "Resultado:", result);
        return result;
    },

    // Método para refrescar cuando cambie la orden o lista de precio
    refreshDivisaControl() {
        // console.log("🔧 Refrescando control de divisa...");
        
        // Forzar re-renderizado del componente
        if (this.render) {
            this.render();
        }
        
        // Aplicar parches visuales inmediatamente si corresponde
        if (this.shouldShowDivisaControl) {
            this.applyVisualPatches();
        }
    },

    // Método para forzar refrescado desde el popup
    forceRefreshDivisaControl() {
        // console.log("🔧 Forzando refrescado de control de divisa...");
        this.refreshDivisaControl();
        
        // También refrescar los botones de métodos de pago
        setTimeout(() => {
            this.refreshNormalPaymentButtons();
        }, 200);
    },

    // Método para forzar refrescado completo
    forceFullRefresh() {
        // console.log("🔧 🔄 Forzando refrescado completo...");
        
        // Forzar re-renderizado del componente
        if (this.render) {
            this.render();
        }
        
        // Aplicar parches visuales inmediatamente
        this.applyVisualPatches();
        
        // Refrescar control de divisa
        setTimeout(() => {
            this.refreshDivisaControl();
        }, 200);
    },

    get showDivisaButton() {
        // Solo mostrar si el control de divisa está habilitado para la lista de precio actual
        if (!this.shouldShowDivisaControl) {
            return false;
        }
        
        // Mostrar el botón cuando hay productos en la orden
        const order = this.pos.get_order();
        if (order && order.orderlines && order.orderlines.length > 0) {
            const totalAmount = order.get_total_with_tax();
            return totalAmount > 0;
        }
        return false;
    },

    paymentMethodIsDisabled(paymentMethod) {
        // Solo aplicar lógica si el control de divisa está habilitado para la lista de precio actual
        if (!this.shouldShowDivisaControl) {
            return false;
        }
        
        // Si es método especial, no deshabilitar aquí - REPLICANDO EXACTAMENTE LA LÓGICA DEL ADDON ORIGINAL
        if (this.specialPaymentMethodIds.includes(paymentMethod.id)) {
            return false;
        }
        
        // Métodos normales: SIEMPRE deshabilitar cuando el control de divisa esté activo
        const order = this.pos.get_order();
        
        // Si la orden es un reembolso, no deshabilitar ningún método de pago
        if (order && typeof order.isRefund === 'function' && order.isRefund()) {
            return false;
        }
        
        // Si hay productos en la orden y el control de divisa está activo, 
        // BLOQUEAR TODOS los métodos normales para forzar el uso exclusivo de divisa
        if (order && order.orderlines && order.orderlines.length > 0) {
            return true; // SIEMPRE bloquear métodos normales cuando se paga con divisa
        }
        
        return false;
    },

    refreshNormalPaymentButtons() {
        this.applyVisualPatches();
    },

    addNewPaymentLine(paymentMethod) {
        // Solo aplicar lógica si el control de divisa está habilitado para la lista de precio actual
        if (!this.shouldShowDivisaControl) {
            return originalAddNewPaymentLine.call(this, paymentMethod);
        }
        
        // Validar tanto métodos normales como especiales por lógica - REPLICANDO EXACTAMENTE LA LÓGICA DEL ADDON ORIGINAL
        // Si es especial y está deshabilitado por config, bloquear
        if (this.specialPaymentMethodIds.includes(paymentMethod.id)) {
            this.notification.add(_t('This special payment method is disabled. Use the currency popup.'), { type: 'warning' });
            return false;
        }
        
        // Si es normal y la lógica lo deshabilita, bloquear
        if (this.paymentMethodIsDisabled(paymentMethod)) {
            this.notification.add(_t('This payment method is disabled until the currency payment is completed.'), { type: 'warning' });
            return false;
        }
        
        const result = originalAddNewPaymentLine.call(this, paymentMethod);
        setTimeout(() => this.refreshNormalPaymentButtons(), 0);
        return result;
    },

    deletePaymentLine(paymentLineOrCid) {
        // Solo aplicar lógica si el control de divisa está habilitado para la lista de precio actual
        if (!this.shouldShowDivisaControl) {
            const order = this.pos.get_order();
            const paymentLine = typeof paymentLineOrCid === 'object' ? paymentLineOrCid : order.paymentlines.find(l => l.cid === paymentLineOrCid);
            if (paymentLine) {
                order.remove_paymentline(paymentLine);
            }
            return;
        }
        
        const order = this.pos.get_order();
        // Si recibes un cid, obtén el objeto real - REPLICANDO EXACTAMENTE LA LÓGICA DEL ADDON ORIGINAL
        const paymentLine = typeof paymentLineOrCid === 'object' ? paymentLineOrCid : order.paymentlines.find(l => l.cid === paymentLineOrCid);
        if (!paymentLine) return;
        
        if (paymentLine.is_divisa_special) {
            this.notification.add(_t('You cannot delete this special payment method here. Use the popup to modify it.'), { type: 'warning' });
            return;
        }
        
        order.remove_paymentline(paymentLine);
        setTimeout(() => this.refreshNormalPaymentButtons(), 0);
    },

    async showDivisaPaymentMethodsPopup() {
        // console.log("🔧 Abriendo popup de métodos de pago en divisa...");
        
        // Refrescar inmediatamente para asegurar que los métodos normales estén bloqueados
        this.forceRefreshDivisaControl();
        
        const { confirmed } = await this.popup.add(DivisaPaymentMethodsPopup, {});
        // console.log("🔧 Popup cerrado, confirmado:", confirmed);
        
        // Refrescar después de cerrar el popup
        setTimeout(() => {
            this.forceRefreshDivisaControl();
            this.refreshNormalPaymentButtons();
        }, 100);
    },

    updateSelectedPaymentline(amount = false) {
        // Solo aplicar lógica si el control de divisa está habilitado para la lista de precio actual
        if (!this.shouldShowDivisaControl) {
            return originalUpdateSelectedPaymentline.call(this, amount);
        }
        
        // Bloquear si no hay línea seleccionada - REPLICANDO EXACTAMENTE LA LÓGICA DEL ADDON ORIGINAL
        if (!this.selectedPaymentLine) {
            if (this.notification && typeof this.notification.add === 'function') {
                this.notification.add(_t('You must select a valid payment method to enter an amount.'), { type: 'warning' });
            }
            return;
        }
        
        // Bloquear edición de líneas especiales
        if (this.selectedPaymentLine.is_divisa_special) {
            if (this.notification && typeof this.notification.add === 'function') {
                this.notification.add(_t('You cannot edit this special payment method here. Use the popup to modify it.'), { type: 'warning' });
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

// --- Patch para evitar seleccionar o editar líneas especiales ---
if (!PaymentScreen.prototype._divisa_patch_applied) {
    const originalSelectLine = PaymentScreen.prototype.selectLine;
    PaymentScreen.prototype.selectLine = function(line) {
        if (line && line.is_divisa_special) {
            if (this.notification && typeof this.notification.add === 'function') {
                this.notification.add(_t('You cannot edit this special payment method here. Use the popup to modify it.'), { type: 'warning' });
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
                this.pos.notification.add(_t('You cannot delete this special payment method here. Use the popup to modify it.'), { type: 'warning' });
            }
            return;
        }
        // Si NO es especial, permitir siempre la eliminación (sin importar opts.force)
        return originalRemovePaymentLine.call(this, paymentline, opts);
    },
});

