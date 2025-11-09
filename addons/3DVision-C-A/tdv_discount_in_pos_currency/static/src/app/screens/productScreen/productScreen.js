/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

patch(ProductScreen.prototype, {
    get orderWidgetProps() {
        const props = this._super();
        return {
            ...props,
            order: this.pos.get_order(),
            currency_discount_mode: this.pos.config.currency_discount_mode,
        };
    },
}); 