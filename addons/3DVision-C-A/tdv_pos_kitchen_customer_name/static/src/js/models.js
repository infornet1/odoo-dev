/** @odoo-module */

import { Order } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";
import { renderToElement } from "@web/core/utils/render";

patch(Order.prototype, {
    /**
     * Override the method that generates order changes for kitchen receipts
     * to include customer name
     */
    getOrderChanges(skipped = false) {
        const changes = super.getOrderChanges(...arguments);
        
        // Add customer name to the changes object
        if (this.get_partner()) {
            changes.partner_name = this.get_partner().name;
        } else {
            changes.partner_name = false;
        }
        
        return changes;
    },

    /**
     * Override the method that transforms order changes for printing
     * to include customer name in the final data
     */
    changesToOrder(cancelled = false) {
        const result = super.changesToOrder(...arguments);
        
        // Add customer name to the result
        if (this.get_partner()) {
            result.partner_name = this.get_partner().name;
        } else {
            result.partner_name = false;
        }
        
        return result;
    },

    /**
     * Override the printChanges method to include customer name in the printing data
     */
    async printChanges(cancelled) {
        const orderChange = this.changesToOrder(cancelled);
        let isPrintSuccessful = true;
        const d = new Date();
        let hours = "" + d.getHours();
        hours = hours.length < 2 ? "0" + hours : hours;
        let minutes = "" + d.getMinutes();
        minutes = minutes.length < 2 ? "0" + minutes : minutes;
        
        for (const printer of this.pos.unwatched.printers) {
            const changes = this._getPrintingCategoriesChanges(
                printer.config.product_categories_ids,
                orderChange
            );
            if (changes["new"].length > 0 || changes["cancelled"].length > 0) {
                const printingChanges = {
                    new: changes["new"],
                    cancelled: changes["cancelled"],
                    table_name: this.pos.config.module_pos_restaurant
                        ? this.getTable().name
                        : false,
                    floor_name: this.pos.config.module_pos_restaurant
                        ? this.getTable().floor.name
                        : false,
                    name: this.name || "unknown order",
                    time: {
                        hours,
                        minutes,
                    },
                    // Add customer name to the printing data
                    partner_name: this.get_partner() ? this.get_partner().name : false,
                };
                const receipt = renderToElement("point_of_sale.OrderChangeReceipt", {
                    changes: printingChanges,
                });
                const result = await printer.printReceipt(receipt);
                if (!result.successful) {
                    isPrintSuccessful = false;
                }
            }
        }

        return isPrintSuccessful;
    },
});
