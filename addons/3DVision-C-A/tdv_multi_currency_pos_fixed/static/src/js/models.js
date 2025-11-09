odoo.define('tdv_multi_currency_pos.models', function (require) {
    'use strict';

    const { PosGlobalState, Order, Payment } = require("point_of_sale.models");
    const Registries = require("point_of_sale.Registries");
    const utils = require("web.utils");
    const round_pr = utils.round_precision;

    const TDVPosGlobalState = (PosGlobalState) =>
        class extends PosGlobalState {
            constructor(...args) {
                super(...args);
                this.secondCurrency = null;
            }
            async _processData(loadedData) {
                this.secondCurrency = loadedData["second.currency"];
                super._processData(loadedData);
            }
            format_currency(amount, precision, currency) {
                currency = currency || this.currency;
                amount = this.format_currency_no_symbol(amount, precision, currency);

                let formats = {
                    after: `${amount} ${(currency.symbol || '')}`,
                    before: `${(currency.symbol || '')} ${amount}`,
                }

                return formats[currency.position]
            }
            convertAmount(amount, currency){
                currency = currency || this.currency;
                if (currency.id == this.currency.id)
                    return amount;
                return amount * currency.rate;
            }
            inverseConvertAmount(amount, currency){
                currency = currency || this.currency;
                if (currency.id == this.currency.id)
                    return amount;
                return amount / currency.rate;
            }
        }
    const TDVOrder = (Order) =>
        class extends Order {

            get_total_paid() {
                return round_pr(this.paymentlines.reduce((function(sum, paymentLine) {
                    console.log("EL PAYMENT LINE: ",paymentLine);
                    if (paymentLine.is_done()) {
                        sum += paymentLine.pos.inverseConvertAmount(paymentLine.get_amount(), paymentLine.payment_method.currency_id);
                    }
                    return sum;
                }), 0), this.pos.currency.rounding);
            }

            get_due(paymentline) {
                if (!paymentline) {
                    var due = this.get_total_with_tax() - this.get_total_paid() + this.get_rounding_applied();
                } else {
                    var due = this.get_total_with_tax();
                    var lines = this.paymentlines;
                    for (var i = 0; i < lines.length; i++) {
                        if (lines[i] === paymentline) {
                            break;
                        } else {
                            due -= this.pos.convertAmount(lines[i].get_amount(), paymentline.currency_id);
                        }
                    }
                }
                return round_pr(due, this.pos.currency.rounding);
            }
            add_paymentline(payment_method) {
                this.assert_editable();
                if (this.electronic_payment_in_progress()) {
                    return false;
                } else {
                    var newPaymentline = Payment.create({},{order: this, payment_method:payment_method, pos: this.pos});
                    this.paymentlines.add(newPaymentline);
                    this.select_paymentline(newPaymentline);
                    if(this.pos.config.cash_rounding){
                      this.selected_paymentline.set_amount(0);
                    }
                    newPaymentline.set_amount(this.pos.convertAmount(this.get_due(), payment_method.currency_id));

                    if (payment_method.payment_terminal) {
                        newPaymentline.set_payment_status('pending');
                    }
                    return newPaymentline;
                }
            }
        }
    const TDVPayment = (Payment) =>
        class extends Payment {
            export_as_JSON() {
                let json = super.export_as_JSON();
                json["amount"] = this.pos.inverseConvertAmount(json["amount"], this.payment_method.currency_id);
                return json;
            }
        }


        Registries.Model.extend(PosGlobalState, TDVPosGlobalState);
        Registries.Model.extend(Order, TDVOrder);
        Registries.Model.extend(Payment, TDVPayment);
    return TDVPosGlobalState;
});