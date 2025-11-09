/** @odoo-module **/
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { _t } from "@web/core/l10n/translation";


patch(PaymentScreen.prototype, {

    updateSelectedPaymentline(amount = false) {
        if (this.paymentLines.every((line) => line.paid)) {
            this.currentOrder.add_paymentline(this.payment_methods_from_config[0]);
        }
        if (!this.selectedPaymentLine) {
            return;
        } // do nothing if no selected payment line
        if (amount === false) {
            if (this.numberBuffer.get() === null) {
                amount = null;
            } else if (this.numberBuffer.get() === "") {
                amount = 0;
            } else {
                amount = this.numberBuffer.getFloat();
            }
        }
        // disable changing amount on paymentlines with running or done payments on a payment terminal
        const payment_terminal = this.selectedPaymentLine.payment_method.payment_terminal;
        // const hasCashPaymentMethod = this.payment_methods_from_config.some(
        //     (method) => method.type === "cash"
        // );
        // if (
        //     !hasCashPaymentMethod &&
        //     amount > this.currentOrder.get_due() + this.selectedPaymentLine.amount
        // ) {
        //     this.selectedPaymentLine.set_amount(0);
        //     this.numberBuffer.set(this.currentOrder.get_due().toString());
        //     amount = this.currentOrder.get_due();
        //     this.showMaxValueError();
        // }
        if (
            payment_terminal &&
            !["pending", "retry"].includes(this.selectedPaymentLine.get_payment_status())
        ) {
            return;
        }
        if (amount === null) {
            this.deletePaymentLine(this.selectedPaymentLine.cid);
        } else {
            this.selectedPaymentLine.set_amount(amount);
        }
    }
,
    async _isOrderValid(isForceValidate) {


        if (this.currentOrder.get_orderlines().length === 0 && this.currentOrder.is_to_invoice()) {
            this.popup.add(ErrorPopup, {
                title: _t("Empty Order"),
                body: _t(
                    "There must be at least one product in your order before it can be validated and invoiced."
                ),
            });
            return false;
        }

        if ((await this._askForCustomerIfRequired()) === false) {
            return false;
        }

        if (
            (this.currentOrder.is_to_invoice() || this.currentOrder.getShippingDate()) &&
            !this.currentOrder.get_partner()
        ) {
            const { confirmed } = await this.popup.add(ConfirmPopup, {
                title: _t("Please select the Customer"),
                body: _t(
                    "You need to select the customer before you can invoice or ship an order."
                ),
            });
            if (confirmed) {
                this.selectPartner();
            }
            return false;
        }

        const partner = this.currentOrder.get_partner();
        if (
            this.currentOrder.getShippingDate() &&
            !(partner.name && partner.street && partner.city && partner.country_id)
        ) {
            this.popup.add(ErrorPopup, {
                title: _t("Incorrect address for shipping"),
                body: _t("The selected customer needs an address."),
            });
            return false;
        }

        if (
            this.currentOrder.get_total_with_tax() != 0 &&
            this.currentOrder.get_paymentlines().length === 0
        ) {
            this.notification.add(_t("Select a payment method to validate the order."));
            return false;
        }

        // VALIDACIÓN ESTRICTA DE PAGOS
        const tolerance = 0.01; // Tolerancia muy pequeña para evitar problemas de redondeo
        
        if (this.pos.secondCurrency) {
            // Validación en moneda secundaria - SOLO cuando el pago es inferior al total
            const totalInSecondCurrency = this.currentOrder.get_total_with_tax_second_currency();
            const paidInSecondCurrency = this.currentOrder.get_total_paid_second_currency();
            const difference = totalInSecondCurrency - paidInSecondCurrency; // Sin Math.abs para mantener el signo
            
            // console.log("🔍 VALIDACIÓN MONEDA SECUNDARIA:", {
            //     totalRequerido: totalInSecondCurrency,
            //     montoInsertado: paidInSecondCurrency,
            //     diferencia: difference,
            //     moneda: this.pos.secondCurrency.name
            // });
            
            // Solo bloquear si hay un DÉFICIT (diferencia positiva)
            if (difference > tolerance) {
                // console.log("❌ PAGO INCOMPLETO - Déficit:", difference);
                
                // Usar la moneda del método de pago actual
                const paymentMethodCurrency = this.currentOrder.paymentlines.length > 0 ? 
                    this.currentOrder.paymentlines[0].payment_method.currency_id : 
                    this.pos.secondCurrency;
                
                // Formatear manualmente para evitar conversiones incorrectas
                const formattedAmount = difference.toFixed(2);
                const currencySymbol = paymentMethodCurrency ? paymentMethodCurrency.symbol : '';
                
                this.popup.add(ErrorPopup, {
                    title: _t("Pago incompleto"),
                    body: _t("El monto pagado no coincide con el total de la orden. Faltan ") + 
                          currencySymbol + " " + formattedAmount + 
                          _t(" para completar el pago."),
                });
                return false;
            }
            
            // console.log("✅ PAGO VÁLIDO - Monto suficiente o exacto");
        } else {
            // Validación en moneda principal si no hay moneda secundaria
            if (!this.currentOrder.is_paid() || this.invoicing) {
                return false;
            }
        }

        if (this.currentOrder.has_not_valid_rounding()) {
            var line = this.currentOrder.has_not_valid_rounding();
            this.popup.add(ErrorPopup, {
                title: _t("Incorrect rounding"),
                body: _t(
                    "You have to round your payments lines." + line.amount + " is not rounded."
                ),
            });
            return false;
        }

        // if the change is too large, it's probably an input error, make the user confirm.
        if (
            !isForceValidate &&
            this.currentOrder.get_total_with_tax() > 0 &&
            this.currentOrder.get_total_with_tax() * 1000 < this.currentOrder.get_total_paid()
        ) {
            this.popup
                .add(ConfirmPopup, {
                    title: _t("Please Confirm Large Amount"),
                    body:
                        _t("Are you sure that the customer wants to  pay") +
                        " " +
                        this.env.utils.formatCurrency(this.currentOrder.get_total_paid()) +
                        " " +
                        _t("for an order of") +
                        " " +
                        this.env.utils.formatCurrency(this.currentOrder.get_total_with_tax()) +
                        " " +
                        _t('? Clicking "Confirm" will validate the payment.'),
                })
                .then(({ confirmed }) => {
                    if (confirmed) {
                        this.validateOrder(true);
                    }
                });
            return false;
        }

        if (!this.currentOrder._isValidEmptyOrder()) {
            return false;
        }

        return true;
    }
})