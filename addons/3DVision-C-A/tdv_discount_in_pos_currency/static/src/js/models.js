/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Order } from "@point_of_sale/app/store/models";
import { Orderline } from "@point_of_sale/app/store/models";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { PosDB } from "@point_of_sale/app/store/db";

// Guarda SIEMPRE referencia a los métodos originales
const originalExportAsJSON = Order.prototype.export_as_JSON;
const originalInitFromJSON = Order.prototype.init_from_JSON;
const originalOrderSetup = Order.prototype.setup;

// --- PATCH ROBUSTO PARA CURRENCY_AMOUNT E IS_REFUND ---
patch(Order.prototype, {
    setup(_defaultObj, options) {
        originalOrderSetup.apply(this, arguments);
        // Siempre inicializa currency_amount, incluso si no viene de JSON
        if (options && options.json && 'currency_amount' in options.json) {
            this.currency_amount = options.json.currency_amount;
        } else {
            this.currency_amount = 0;
        }
        // Inicializa is_refund
        if (options && options.json && 'is_refund' in options.json) {
            this.is_refund = options.json.is_refund;
        } else {
            this.is_refund = false;
        }
    },
    export_as_JSON() {
        const json = originalExportAsJSON.call(this);
        // Siempre serializa currency_amount, aunque sea 0
        json.currency_amount = (this.currency_amount !== undefined && this.currency_amount !== null) ? this.currency_amount : 0;
        // Serializa is_refund
        json.is_refund = !!this.is_refund;
        return json;
    },
    init_from_JSON(json) {
        originalInitFromJSON.call(this, json);
        // Siempre inicializa currency_amount, aunque no venga en el JSON
        this.currency_amount = ('currency_amount' in json) ? json.currency_amount : 0;
        // Inicializa is_refund
        this.is_refund = ('is_refund' in json) ? json.is_refund : false;
        this.trigger && this.trigger('change', this);
    },
    set_currency_amount(amount) {
        if (amount === undefined || amount === null || isNaN(amount)) {
                return;
        }
            this.currency_amount = amount;
            this.trigger && this.trigger('change', this);
        // Forzar guardado en localStorage
        if (this.pos && this.pos.db && typeof this.pos.db.save_unpaid_order === 'function') {
            this.pos.db.save_unpaid_order(this);
        }
        // (Opcional) También sincroniza con backend si lo deseas
        if (typeof syncDraftOrder === 'function') {
            syncDraftOrder(this);
        }
    },
        get_currency_amount() {
        return (this.currency_amount !== undefined && this.currency_amount !== null) ? this.currency_amount : 0;
    },
    set_is_refund(val) {
        this.is_refund = !!val;
        this.trigger && this.trigger('change', this);
    },
    isRefund() {
        return !!this.is_refund;
    },
});

// Parche seguro para set_discount_special_amount
patch(Order.prototype, {
    set_discount_special_amount(amount) {
        this.discount_special_amount = amount;
            this.trigger && this.trigger('change', this);
    },
});

// Patch para Orderline: serialización y restauración de currency_amount (o cualquier campo custom)
const originalOrderlineExportAsJSON = Orderline.prototype.export_as_JSON;
const originalOrderlineInitFromJSON = Orderline.prototype.init_from_JSON;

patch(Orderline.prototype, {
        export_as_JSON() {
        const json = originalOrderlineExportAsJSON.call(this);
        // Si tienes un campo custom en la línea, agrégalo aquí
        if (this.currency_amount !== undefined) {
            json.currency_amount = this.currency_amount;
        }
        return json;
    },
        init_from_JSON(json) {
        originalOrderlineInitFromJSON.call(this, json);
        // Restaurar el campo custom si existe
        if ('currency_amount' in json) {
            this.currency_amount = json.currency_amount;
        }
    },
    set_currency_amount(amount) {
        if (amount === undefined || amount === null || isNaN(amount)) {
            // console.log('[DEBUG][Orderline] set_currency_amount ignorado. CID:', this.cid, 'Intento de setear:', amount);
            return;
        }
        this.currency_amount = amount;
        // console.log('[DEBUG][Orderline] set_currency_amount CID:', this.cid, 'Nuevo valor:', amount);
        this.trigger && this.trigger('change', this);
    },
    get_currency_amount() {
        return (this.currency_amount !== undefined && this.currency_amount !== null) ? this.currency_amount : 0;
    },
});

// --- SINCRONIZACIÓN DE BORRADORES CON BACKEND ---
async function syncDraftOrder(order) {
    if (!(order.pos && order.pos.config && order.pos.config.iface_table_management)) return; // Solo restaurante
    try {
        await fetch('/pos/draft/save', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                uid: order.uid,
                data: order.export_as_JSON(),
                session_id: order.pos && order.pos.pos_session && order.pos.pos_session.id,
            }),
            credentials: 'include'
        });
        // console.log('[SYNC][DRAFT] Borrador sincronizado en backend para UID:', order.uid);
    } catch (e) {
        // console.error('[SYNC][DRAFT] Error al sincronizar borrador:', e);
    }
}

// Parchea set_currency_amount para llamar a syncDraftOrder
const originalSetCurrencyAmount = Order.prototype.set_currency_amount;
Order.prototype.set_currency_amount = function(amount) {
    originalSetCurrencyAmount.call(this, amount);
    syncDraftOrder(this);
};

// Parchea set_selected_order para guardar la orden anterior al cambiar
const originalSetSelectedOrder = PosStore.prototype.set_selected_order;
patch(PosStore.prototype, {
    set_selected_order(order) {
        if (this.selectedOrder) {
            if (typeof syncDraftOrder === 'function') {
                syncDraftOrder(this.selectedOrder);
            }
        }
        originalSetSelectedOrder.apply(this, arguments);
    }
});

// Función para cargar borradores al iniciar el POS
export async function loadDraftOrders(pos) {
    if (!(pos.config && pos.config.iface_table_management)) return; // Solo restaurante
    try {
        if (!pos.pos_session || !pos.pos_session.id) {
            // No hay sesión aún, no intentes cargar borradores
            return;
        }
        const response = await fetch('/pos/draft/load', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({session_id: pos.pos_session.id}),
            credentials: 'include'
        });
        const drafts = await response.json();
        drafts.forEach(draft => {
            // Restaurar usando init_from_JSON para asegurar campos custom
            const order = new Order({}, { pos: pos });
            order.init_from_JSON(draft.data);
            pos.get_order_list().add(order);
        });
    } catch (e) {
    }
}

// Parchea load_unpaid_orders para forzar currency_amount tras restaurar
const originalLoadUnpaidOrders = PosStore.prototype.load_unpaid_orders;
patch(PosStore.prototype, {
    async load_unpaid_orders() {
        await originalLoadUnpaidOrders.apply(this, arguments);
        // Recorre todas las órdenes restauradas y fuerza currency_amount
        this.get_order_list().forEach(order => {
            if (order && typeof order.get_currency_amount === 'function') {
                if (order.currency_amount === undefined) {
                    order.currency_amount = 0;
                }
            }
        });
    }
});

// Hook para cargar borradores del backend antes de restaurar localStorage
const originalSetup = PosStore.prototype.setup;
patch(PosStore.prototype, {
    async setup() {
        // 1. Cargar borradores del backend primero
        if (typeof loadDraftOrders === 'function') {
            await loadDraftOrders(this);
        }
        // 2. Luego sigue el flujo nativo (localStorage)
        await originalSetup.apply(this, arguments);
        // 3. Elimina duplicados por UID (si existen en ambos)
        const seen = new Set();
        this.get_order_list().filter(order => {
            if (seen.has(order.uid)) {
                this.get_order_list().remove(order);
                return false;
            }
            seen.add(order.uid);
            return true;
        });
    }
});

// Refuerzo final: sobrescribe init_from_JSON para forzar currency_amount desde el backend
const originalInitFromJSONFinal = Order.prototype.init_from_JSON;
Order.prototype.init_from_JSON = function(json) {
    originalInitFromJSONFinal.call(this, json);
    if ('currency_amount' in json) {
        this.currency_amount = json.currency_amount;
    } else {
        this.currency_amount = 0;
    }
    this.trigger && this.trigger('change', this);
}; 