/** @odoo-module **/
import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";

export class DiscountSpecialNumberPopup extends NumberPopup {
    static props = {
        ...NumberPopup.props,
        title: { type: String, optional: true },
        body: { type: String, optional: true },
        startingValue: { type: Number, optional: true },
        // Puedes agregar más props personalizadas aquí si lo necesitas
    };
} 