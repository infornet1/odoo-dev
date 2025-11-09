odoo.define("tdv_multi_currency_pos.PaymentScreenPaymentLines", function(require) {
    "use strict";

    const PaymentScreenPaymentLines = require("point_of_sale.PaymentScreenPaymentLines");
    const Registries = require("point_of_sale.Registries");

    const TDVPaymentScreenPaymentLines = (PaymentScreenPaymentLines) =>
        class extends PaymentScreenPaymentLines {
            formatLineAmount(paymentLine) {

                let amount = paymentLine.get_amount();
                let currency = paymentLine.payment_method.currency_id;

                return this.env.pos.format_currency(
                    amount, null, currency
                );
            }
        }

    Registries.Component.extend(PaymentScreenPaymentLines, TDVPaymentScreenPaymentLines);
    return TDVPaymentScreenPaymentLines;
});