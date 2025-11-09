/** @odoo-module **/
import { ClosePosPopup } from "@point_of_sale/app/navbar/closing_popup/closing_popup";
import { patch } from "@web/core/utils/patch";
import { roundDecimals } from "@web/core/utils/numbers";


patch(ClosePosPopup.prototype, {
    getInitialState() {
        const initialState = {
            notes: "",
            payments: {}
        };
        // ✅ VERIFICACIÓN DE QUE EXISTE efectivo
        const hasValidCashPayment = this.props.default_cash_details

        if (hasValidCashPayment) {
            initialState.payments[this.props.default_cash_details.id] = {
                counted: "0",
            };
            console.log('✅ Método de pago en efectivo agregado:', this.props.default_cash_details.name);
        }else{
            console.warn('⚠️ No se encontró un método de pago en efectivo.');
        }
        
        // ✅ PROCESAR MÉTODOS DE PAGO BANCARIOS con verificación
        this.props.other_payment_methods.forEach((pm) => {
            if (pm.type === "bank" && pm.id) {
                initialState.payments[pm.id] = {
                    counted: pm.amount_full_precision !== undefined ? 
                        (pm.amount_full_precision * pm.currency.rate).toFixed(2) : 
                        `${this.env.utils.roundCurrency(this.env.utils.convertAmount(pm.amount, pm.currency), pm.currency)}`,
                };
                console.log('✅ Método de pago bancario agregado:', pm.name);
            }else{
                console.log('⚠️ Método de pago bancario no válido:', pm.name);
            }
        });
        
        return initialState;
    },
    
    getDifference(paymentId) {
        // ✅ VERIFICACIÓN MÁS ESTRICTA - Asegurar que paymentId existe y tiene counted
        if (!this.state.payments[paymentId] || 
            typeof this.state.payments[paymentId].counted === 'undefined') {
            console.warn('⚠️ Payment ID no encontrado en state o no tiene counted:', paymentId);
            return NaN;
        }
        
        const counted = this.state.payments[paymentId].counted;
        if (!this.env.utils.isValidFloat(counted)) {
            return NaN;
        }
        
        // ✅ DETERMINAR TIPO DE PAGO CON VERIFICACIONES
        const isCashPayment = this.props.default_cash_details?.id === paymentId;
        const bankPayment = this.props.other_payment_methods.find(pm => pm.id === paymentId);
        const isBankPayment = bankPayment && bankPayment.type === "bank";
        
        let paymentMethod;
        let expectedAmount;
        

        if (isCashPayment) {
            if (!this.props.default_cash_details) {
                return NaN;
            }
            paymentMethod = this.props.default_cash_details;
            expectedAmount = this.props.default_cash_details.amount || 0;
        }
        else if (isBankPayment) {
            paymentMethod = bankPayment;
            expectedAmount = bankPayment.amount || 0;
        }
        else {
            console.warn('⚠️ Método de pago no reconocido para diferencia:', paymentId);
            return NaN;
        }
        

        // calculo de la diferencia
        try {
            const counted_float = this.env.utils.inverseConvertAmount(parseFloat(counted), paymentMethod.currency);
            return this.env.utils.roundCurrency(counted_float - expectedAmount, paymentMethod.currency);
        } catch (error) {
            console.error('❌ Error en cálculo de diferencia:', error);
            return NaN;
        }
    }
});