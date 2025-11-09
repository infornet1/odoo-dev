odoo.define("tdv_multi_currency_pos.PaymentScreenStatus", function(require) {
    "use strict";

    const PaymentScreenStatus = require("point_of_sale.PaymentScreenStatus");
    const Registries = require("point_of_sale.Registries");

    const TDVPaymentScreenStatus = () =>
        class extends PaymentScreenStatus {
            get secondTotalDueText() {
                let pos = this.env.pos;
                let amount = pos.convertAmount(this.props.order.get_total_with_tax() + this.props.order.get_rounding_applied(), pos.secondCurrency);

                return pos.format_currency(
                    amount,
                    null,
                    pos.secondCurrency
                )
            }
            get secondRemainingText() {
                let pos = this.env.pos
                let due = pos.convertAmount(
                    (this.props.order.get_due() > 0)? this.props.order.get_due() : 0,
                    pos.secondCurrency
                );
                return pos.format_currency(due, null, pos.secondCurrency);
            }
            get secondChangeText() {
                let pos = this.env.pos;
                let change = pos.convertAmount(
                    this.props.order.get_change(), pos.secondCurrency
                );
                return pos.format_currency(change, null, pos.secondCurrency);
            }
        }

    Registries.Component.extend(PaymentScreenStatus, TDVPaymentScreenStatus);
    return TDVPaymentScreenStatus;
})