odoo.define("tdv_multi_currency_pos.ClosePosPopup", function (require) {
    "use strict";

    const ClosePosPopup = require("point_of_sale.ClosePosPopup");
    const Registries = require("point_of_sale.Registries");
    const { useValidateCashInput } = require('point_of_sale.custom_hooks');
    const { parse } = require('web.field_utils');

    const TDVClosePosPopup = (ClosePosPopup) =>
        class extends ClosePosPopup {
            setup() {
                super.setup();
                if (this.otherPaymentMethods && this.otherPaymentMethods.length > 0) {
                    this.otherPaymentMethods.forEach(pm => {
                        if (this._getShowDiff(pm)) {
                            useValidateCashInput(
                                "closingCashInput_" + pm.id,
                                this.env.pos.convertAmount(
                                    this.state.payments[pm.id].counted,
                                    pm.currency
                                )
                            );
                        }
                    })
                }
            }

            handleInputChange(paymentId, event, currency) {
                if (event.target.classList.contains('invalid-cash-input')) return;
                let expectedAmount;
                if (this.defaultCashDetails && paymentId === this.defaultCashDetails.id) {
                    this.manualInputCashCount = true;
                    this.state.notes = '';
                    expectedAmount = this.defaultCashDetails.amount;
                } else {
                    expectedAmount = this.otherPaymentMethods.find(pm => paymentId === pm.id).amount;
                }
                let amountConverted = this.env.pos.format_currency_no_symbol(
                    this.env.pos.inverseConvertAmount(event.target.value, currency), null, currency
                );

                this.state.payments[paymentId].counted = parse.float(amountConverted);
                //console.log(this.state.payments[paymentId].counted);
                this.state.payments[paymentId].difference =
                    this.env.pos.round_decimals_currency(this.state.payments[paymentId].counted - expectedAmount);
            }
        }

    Registries.Component.extend(ClosePosPopup, TDVClosePosPopup);
    return TDVClosePosPopup;
})