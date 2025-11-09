/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { Order, Payment } from "@point_of_sale/app/store/models";

patch(Order.prototype, {
    async updateIGTF(){
        console.log("AJaaaa mis panitaaaaas!!!")
        let igtfOrderline = this.getIGTFOrderline();
        let igtfPercentage = this.pos.config.igtf_percentage / 100;
        if (!igtfOrderline){
            let igtfProduct = this.pos.db.get_product_by_id(this.pos.config.igtf_product_id[0]);
            igtfOrderline = await this.add_product(igtfProduct);
        }

        this.igtfAmount = this.paymentlines
            .filter(line => line.payment_method.is_igtf)
            .reduce((acc, line) => acc + this.pos.env.utils.inverseConvertAmount(line.get_amount(), line.payment_method.currency_id), 0
        );

        this.igtfAmount = igtfPercentage *
            ((this.igtfAmount < this.getTotalWithoutIGTF())?
            this.igtfAmount : this.getTotalWithoutIGTF())

        igtfOrderline.set_unit_price(this.igtfAmount);
    },
});