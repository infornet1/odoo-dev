/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { Order } from "@point_of_sale/app/store/models";

patch(Order.prototype, {
    set_partner(partner) {
        super.set_partner(partner);
        if (partner && partner.id && typeof partner.vat === "undefined") {
            this.env.services.orm
                .read("res.partner", [partner.id], ["vat"])
                .then((result) => {
                    const record = result && result[0];
                    if (record) {
                        partner.vat = record.vat || "";
                        this.trigger("change");
                    }
                })
                .catch(() => {});
        }
    },
});
