/** @odoo-module **/
import { PaymentScreenStatus } from "@point_of_sale/app/screens/payment_screen/payment_status/payment_status";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreenStatus.prototype, {
    get secondTotalDueText() {
        return this.env.utils.formatCurrency(
            this.props.order.get_total_with_tax() + this.props.order.get_rounding_applied(),
            true,
            this.props.order.pos.secondCurrency
        )
    },
    get secondRemainingText(){
        // Mostrar el restante calculado directamente en moneda secundaria
        const dueSecond = this.props.order.get_due_second_currency();
        return this.env.utils.formatCurrency(
            dueSecond > 0 ? dueSecond : 0,
            true,
            this.props.order.pos.secondCurrency,
            true // noConvert: ya está en moneda secundaria
        );
    },
    get secondChangeText() {
        // Usar el cambio calculado directamente en moneda secundaria (sin reconvertir)
        const changeSecond = this.props.order.get_change_second_currency ? this.props.order.get_change_second_currency() : 0;
        return this.env.utils.formatCurrency(changeSecond, true, this.props.order.pos.secondCurrency, true);
    },
})