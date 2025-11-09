
/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { Product, Order, Payment, Orderline } from "@point_of_sale/app/store/models";
import { roundPrecision } from "@web/core/utils/numbers";


patch(PosStore.prototype, {
    async _processData(loadedData) {
        await super._processData(...arguments);
        this.secondCurrency = loadedData["second.currency"];
    },
});

patch(Product.prototype, {
    getFormattedUnitPrice(currency){
        let price = this.get_display_price();
        let formattedPrice = this.env.utils.formatCurrency(
            price, true, currency || this.pos.currency
        );

        if (this.to_weight)
            formattedPrice = `${formattedPrice} / ${this.get_unit().name}`;

        return formattedPrice;
    }
});

patch(Orderline.prototype, {
    getDisplayData(){
        return {
            ...super.getDisplayData(),
            secondPrice: this.get_discount_str() === "100"
            ? "free"
            : this.env.utils.formatCurrency(this.get_display_price(), true, this.pos.secondCurrency),
        }
    }
});


// REVISAR LOS MONTOS ADICIONALES EN BOLIVARES QUE NO SE ESTAN COLOCANDO BIEN!!!
patch(Order.prototype, {
    add_paymentline(payment_method) {
        this.assert_editable();
        if (this.electronic_payment_in_progress()) {
            return false;
        } else {
            var newPaymentline = new Payment(
                { env: this.env },
                { order: this, payment_method: payment_method, pos: this.pos }
            );

            // LOG: mostrar totales antes de añadir la línea
            console.log("[POS][DEBUG] Order total (with tax):", this.get_total_with_tax());
            console.log("[POS][DEBUG] Order due (get_due):", this.get_due());
            console.log("[POS][DEBUG] Payment method selected:", payment_method.name, payment_method.currency_id && payment_method.currency_id.name);

            console.log("[POS] Monto pendiente de la orden antes de agregar el pago 1:", this.get_due());
            this.paymentlines.add(newPaymentline);
            this.select_paymentline(newPaymentline);
            if (this.pos.config.cash_rounding) {
                this.selected_paymentline.set_amount(0);
            }

            // Si es moneda secundaria (Bs.F), usar el monto restante en esa moneda
            if (this.pos.secondCurrency && payment_method.currency_id.id === this.pos.secondCurrency.id) {
                // Calcular el monto restante en moneda secundaria
                const totalInSecondCurrency = this.get_total_with_tax_second_currency();
                const paidInSecondCurrency = this.get_total_paid_second_currency();
                const remainingInSecondCurrency = totalInSecondCurrency - paidInSecondCurrency;
                
                console.log("[POS][DEBUG] totalInSecondCurrency:", totalInSecondCurrency, "paidInSecondCurrency:", paidInSecondCurrency, "remainingInSecondCurrency:", remainingInSecondCurrency);
                // Si hay un déficit (cantidad positiva), establecer el monto positivo
                if (remainingInSecondCurrency > 0.01) {
                    newPaymentline.set_amount(
                        this.env.utils.roundCurrency(remainingInSecondCurrency, payment_method.currency_id)
                    );
                    console.log("[POS][DEBUG] set_amount (secondCurrency, deficit):", newPaymentline.get_amount());
                } 
                // Si hay un cambio (cantidad negativa), establecer el monto negativo para devolución
                else if (remainingInSecondCurrency < -0.01) {
                    newPaymentline.set_amount(
                        this.env.utils.roundCurrency(remainingInSecondCurrency, payment_method.currency_id)
                    );
                    console.log("[POS][DEBUG] set_amount (secondCurrency, change):", newPaymentline.get_amount());
                } 
                // Si está balanceado, establecer 0
                else {
                    newPaymentline.set_amount(0);
                    console.log("[POS][DEBUG] set_amount (secondCurrency, balanced): 0");
                }
            } else {
                // Para moneda principal, usar la lógica original
            
                newPaymentline.set_amount(
                    this.env.utils.roundCurrency(
                        this.env.utils.convertAmount(this.get_due(), payment_method.currency_id),
                        payment_method.currency_id
                    ));
                  
            }
                
            console.log("[POS] Monto pendiente de la orden después de agregar el pago 2:", this.get_due());
            
            if (payment_method.payment_terminal) {
                newPaymentline.set_payment_status("pending");
            }
            return newPaymentline;
        }
        
    },

    
    get_total_paid() {
        let utils = this.env.utils;
        let totalPaid = this.paymentlines.reduce(function (sum, paymentLine) {
            if (paymentLine.is_done()) {
                // Verificar que utils esté disponible antes de usarlo
                if (utils && utils.inverseConvertAmount) {
                    const convertedAmount = utils.inverseConvertAmount(paymentLine.get_amount(), paymentLine.payment_method.currency_id);
                    sum += convertedAmount;
                    // console.log("Payment line:", {
                    //     amount: paymentLine.get_amount(),
                    //     currency: paymentLine.payment_method.currency_id.name,
                    //     convertedAmount: convertedAmount,
                    //     runningTotal: sum
                    // });
                } else {
                    // Fallback: usar el monto directamente si no hay conversión disponible
                    sum += paymentLine.get_amount();
                    console.warn("utils.inverseConvertAmount no disponible, usando monto directo:", paymentLine.get_amount());
                }
            }
            return sum;
        }, 0);
        
        // console.log("Total paid calculation:", {
        //     totalPaid: totalPaid,
        //     paymentLinesCount: this.paymentlines.length
        // });
        
        // Redondear con la precisión de la moneda principal para evitar errores de decimales
        if (utils && utils.roundCurrency) {
            return utils.roundCurrency(totalPaid, this.pos.currency);
        }
        // Fallback: redondear manualmente si utils no está disponible
        return Math.round(totalPaid * 100) / 100;
    },
    get_due(paymentline) {
        let due;
        if (!paymentline) {
            due = this.get_total_with_tax() - this.get_total_paid() + this.get_rounding_applied();
        } else {
            due = this.get_total_with_tax();
            var lines = this.paymentlines;
            for (var i = 0; i < lines.length; i++) {
                if (lines[i] === paymentline) {
                    break;
                } else {
                    // Verificar que env.utils esté disponible antes de usarlo
                    if (this.env && this.env.utils && this.env.utils.inverseConvertAmount) {
                        due -= this.env.utils.inverseConvertAmount(
                            lines[i].get_amount(),
                            lines[i].payment_method.currency_id,
                            paymentline.payment_method.currency_id
                        );
                    } else {
                        // Fallback: restar el monto directamente si no hay conversión disponible
                        due -= lines[i].get_amount();
                        console.warn("env.utils.inverseConvertAmount no disponible en get_due, usando monto directo");
                    }
                }
            }
        }
        // Usar una precisión más alta para evitar problemas con decimales
        // Solo redondear a 0 si la diferencia es realmente insignificante (menos de 0.001)
        if (Math.abs(due) < 0.01) {
            return 0.00;
        }
        
        // Log para debugging
        // console.log("get_due calculation:", {
        //     due: due,
        //     totalWithTax: this.get_total_with_tax(),
        //     totalPaid: this.get_total_paid(),
        //     roundingApplied: this.get_rounding_applied()
        // });
        
        // Redondear con la precisión de la moneda principal
        if (this.env.utils && this.env.utils.roundCurrency) {
            return this.env.utils.roundCurrency(due, this.pos.currency);
        }
        // Fallback: redondear manualmente si utils no está disponible
        return Math.round(due * 100) / 100;
    },
    // Función para obtener el total en la moneda secundaria
    get_total_with_tax_second_currency() {
        if (!this.pos.secondCurrency) {
            return 0;
        }
        const totalInMainCurrency = this.get_total_with_tax();
        return this.env.utils.convertAmount(totalInMainCurrency, this.pos.secondCurrency);
    },
    
    // Función para obtener el total pagado en la moneda secundaria
    get_total_paid_second_currency() {
        if (!this.pos.secondCurrency) {
            return 0;
        }
        let utils = this.env.utils;
        let totalPaid = this.paymentlines.reduce(function (sum, paymentLine) {
            if (paymentLine.is_done()) {
                // Si el método de pago ya está en la moneda secundaria, usar directamente
                if (paymentLine.payment_method.currency_id.id === this.pos.secondCurrency.id) {
                    sum += paymentLine.get_amount();
                } else {
                    // Verificar que utils esté disponible antes de usarlo
                    if (utils && utils.inverseConvertAmount && utils.convertAmount) {
                        // Convertir desde la moneda principal a la secundaria
                        const amountInMainCurrency = utils.inverseConvertAmount(paymentLine.get_amount(), paymentLine.payment_method.currency_id);
                        sum += utils.convertAmount(amountInMainCurrency, this.pos.secondCurrency);
                    } else {
                        // Fallback: usar el monto directamente si no hay conversión disponible
                        sum += paymentLine.get_amount();
                        console.warn("utils.inverseConvertAmount/convertAmount no disponible en get_total_paid_second_currency, usando monto directo");
                    }
                }
            }
            return sum;
        }.bind(this), 0);
        
        console.log("Total paid in second currency:", {
            totalPaid: totalPaid,
            secondCurrency: this.pos.secondCurrency.name
        });
        
        return totalPaid;
    },
    
    // Función para obtener restantes en moneda secundaria
    get_due_second_currency() {
        if (!this.pos.secondCurrency) {
            return 0;
        }
        // Obtener el total en moneda principal y convertirlo a secundaria
        const totalInMainCurrency = this.get_total_with_tax();
        const totalInSecondCurrency = this.env.utils.convertAmount(totalInMainCurrency, this.pos.secondCurrency);
        
        // Calcular el monto pagado expresado en la moneda principal (USD) sin redondeos.
        // Incluye líneas marcadas como hechas y la línea actualmente seleccionada para reflejar cambios inmediatos.
        let utils = this.env.utils;
        let paidInMainCurrencyExact = 0;
        this.paymentlines.forEach(paymentLine => {
            if (paymentLine.is_done() || paymentLine === this.selected_paymentline) {
                if (utils && utils.inverseConvertAmount) {
                    // inverseConvertAmount toma el amount en la moneda del payment line y devuelve valor en moneda principal
                    paidInMainCurrencyExact += utils.inverseConvertAmount(paymentLine.get_amount(), paymentLine.payment_method.currency_id);
                } else {
                    // Fallback: si no hay función de conversión, sumar el monto tal cual
                    paidInMainCurrencyExact += paymentLine.get_amount();
                }
            }
        });
        // Exponer para depuración o uso posterior sin modificar la firma de la función
        this.paidInMainCurrencyExact = paidInMainCurrencyExact;

        
        // Sumar solo los pagos que están en moneda secundaria (para calcular el restante en Bs.F)
        let paidInSecondCurrency = 0;
        this.paymentlines.forEach(paymentLine => {
            if (paymentLine.is_done() && paymentLine.payment_method.currency_id.id === this.pos.secondCurrency.id) {
                paidInSecondCurrency += paymentLine.get_amount();
            }
        });

        // const due = totalInSecondCurrency - paidInSecondCurrency;

        // Convertir el monto exacto pagado en USD a la segunda moneda usando la tasa exacta (sin redondeos adicionales)
        let paidInSecondExact = paidInMainCurrencyExact * this.pos.secondCurrency.rate;

        console.log("Monto en USD digitado:", paidInMainCurrencyExact)
        console.log("Monto exacto en bolivares:", paidInSecondExact)
        // Calcular la diferencia entre lo que se pagó (convertido) y el restante de la orden en Bs.F
        const due = totalInSecondCurrency - paidInSecondExact;
        console.log("El remantente de la orden en segunda moneda:", due)
        return due;
    },

    // Función para calcular el cambio (positive) en moneda secundaria.
    // Incluye todas las líneas de pago actuales (incluida la línea seleccionada que aún no esté `done`).
    get_change_second_currency() {
        if (!this.pos.secondCurrency) {
            return 0;
        }
        const totalSecond = this.get_total_with_tax_second_currency();
        console.log("Total en moneda secundaria:", totalSecond);
        let utils = this.env.utils;
        let paidSecond = this.paymentlines.reduce(function (sum, paymentLine) {

            // console.log("PaidSecond:", paidSecond)
            // Tomar el monto tal cual si el método ya está en la moneda secundaria
            if (paymentLine.payment_method && paymentLine.payment_method.currency_id && paymentLine.payment_method.currency_id.id === this.pos.secondCurrency.id) {
                sum += paymentLine.get_amount();
            } else {
                // Convertir desde la moneda del paymentLine hacia la moneda secundaria
                if (utils && utils.inverseConvertAmount && utils.convertAmount) {
                    const amountInMain = utils.inverseConvertAmount(paymentLine.get_amount(), paymentLine.payment_method.currency_id);
                    sum += utils.convertAmount(amountInMain, this.pos.secondCurrency);
                } else {
                    // Fallback: sumar el monto directo. No es ideal pero evita errores si falta utils.
                    sum += paymentLine.get_amount();
                }
            }
            return sum;
        }.bind(this), 0);

        // console.log("PaidSecond:", paidSecond)
        const change = paidSecond - totalSecond;
        // console.log("Calculated change in second currency:", change);

        // Si no hay cambio significativo, devolver 0
        if (Math.abs(change) < 0.01) {
            return 0;
        }
        const positiveChange = change > 0 ? change : 0;
        const factor = Math.pow(10,2)
        
        if (utils && utils.roundCurrency) {
            return Math.round(positiveChange * factor) / factor;
        }
        return Math.round(positiveChange * factor) / factor;
    },
    
    // Función para verificar si la orden está completamente pagada en moneda secundaria
    is_paid_second_currency() {
        if (!this.pos.secondCurrency) {
            return this.is_paid();
        }
        const tolerance = 0.01;
        const due = this.get_due_second_currency();
        const isPaid = Math.abs(due) < tolerance;
        
        // console.log("is_paid_second_currency validation:", {
        //     due: due,
        //     tolerance: tolerance,
        //     isPaid: isPaid
        // });
        
        return isPaid;
    },

    export_for_printing() {
        return {
            ...super.export_for_printing(),
            secondCurrency: this.pos.secondCurrency,
            receiptCurrencySelection: this.pos.config.report_currency_selection,
        }
    }
});


patch(Payment.prototype, {
    export_as_JSON() {
        let res = super.export_as_JSON();
        
        // Verificar que env.utils esté disponible antes de usarlo
        if (this.env && this.env.utils && this.env.utils.inverseConvertAmount) {
            res["amount"] = this.env.utils.inverseConvertAmount(res["amount"], this.payment_method.currency_id);
            //console.log("ADDON NUEVO JSON: ", res);
        } else {
            console.warn("env.utils.inverseConvertAmount no está disponible en export_as_JSON");
        }
        
        return res;
    },
    export_for_printing() {
        //console.log(this);
        return {
            ...super.export_for_printing(),
            currency: this.payment_method.currency_id,
        }
    }

})