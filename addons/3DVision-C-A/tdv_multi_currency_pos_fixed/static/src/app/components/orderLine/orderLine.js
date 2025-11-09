/** @odoo-module **/
/** @odoo-module **/
import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";
import { patch } from "@web/core/utils/patch";

patch(Orderline, {
    props: {
        ...Orderline.props,
        secondPrice: { type: String, optional: true }
    }
})

