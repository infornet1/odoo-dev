odoo.define("tdv_multi_currency_pos.OrderSummary", function (require) {
    "use strict"

    const OrderSummary = require("point_of_sale.OrderSummary");
    const Registries = require("point_of_sale.Registries");
    const { float_is_zero } = require('web.utils');

    const TDVOrderSummary = (OrderSummary) =>
        class extends OrderSummary {
            getSecondTotal() {
                let pos = this.env.pos;
                return pos.format_currency(
                    pos.convertAmount(this.props.order.get_total_with_tax(), pos.secondCurrency),
                    null,
                    pos.secondCurrency
                );
            }

            getSecondTax() {
                let pos = this.env.pos;
                const total = this.props.order.get_total_with_tax();
                const totalWithoutTax = this.props.order.get_total_without_tax();
                const taxAmount = total - totalWithoutTax;
                return {
                    hasTax: !float_is_zero(taxAmount, pos.currency.decimal_places),
                    displayAmount: pos.format_currency(
                        pos.convertAmount(taxAmount, pos.secondCurrency),
                        null,
                        pos.secondCurrency
                    ),
                };
            }
        }

    Registries.Component.extend(OrderSummary, TDVOrderSummary);
    return TDVOrderSummary;
});
