/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { Order, Payment } from "@point_of_sale/app/store/models";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";

patch(Order.prototype, {
    setup(_defaultObj, options) {
        super.setup(...arguments);
        this.igtfAmount = 0;
    },
    getIGTFOrderline() {
        return this.orderlines.find(
            line => line.product.id === this.pos.config.igtf_product_id[0]
        )
    },
    async updateIGTF() {
        let igtfOrderline = this.getIGTFOrderline();
        console.log("🚀 ~ updateIGTF ~ igtfOrderline:", igtfOrderline)
        console.log("🚀 ~ 19 ~ updateIGTF ~ igtfOrderline:", igtfOrderline)
        let igtfPercentage = this.pos.config.igtf_percentage / 100;
        this.igtfAmount = this.paymentlines
            .filter(line => line.payment_method.is_igtf)
            .reduce((acc, line) => acc + line.get_amount(), 0
            );

        const calculatedAmount = igtfPercentage *
            ((this.igtfAmount < this.getTotalWithoutIGTF()) ?
                this.igtfAmount : this.getTotalWithoutIGTF())

        if (!igtfOrderline) {
            let igtfProduct = this.pos.db.get_product_by_id(this.pos.config.igtf_product_id[0]);
            if (!igtfProduct) {
                await this.pos.popup.add(ErrorPopup, {
                    title: "Error",
                    body: "El producto IGTF no está configurado o no se puede encontrar. Por favor, verifique la configuración de su POS.",
                });
            } else {
                await this.add_product(igtfProduct, {
                    quantity: 1,
                    price: calculatedAmount,
                    lst_price: calculatedAmount,
                });
            }
        } else {
            await igtfOrderline.set_unit_price(calculatedAmount);
            await igtfOrderline.set_lst_price(calculatedAmount);
        }
        this.igtfAmount = calculatedAmount;
    },
    remove_paymentline(line) {
        let res = super.remove_paymentline(line);
        if (line.payment_method.is_igtf && this.getIGTFOrderline()) {
            this.removeOrderline(this.getIGTFOrderline());
        }
        return res;
    },
    getTotalWithoutIGTF() {
        return this.get_total_with_tax() - this.getIGTFOrderlineAmount();
    },
    getIGTFOrderlineAmount() {
        const line = this.getIGTFOrderline();
        if (line) {
            return line.get_price_with_tax();
        }
        return 0;
    }
});

patch(Payment.prototype, {
    set_amount(value) {
        super.set_amount(value);
        if (this.payment_method.is_igtf) {
            this.order.updateIGTF();
        }
    }
});