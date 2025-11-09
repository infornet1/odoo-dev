/** @odoo-module */
import { Order } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";
patch(Order.prototype, {
   export_for_printing() {
       const result = super.export_for_printing(...arguments);
       const posConfig = this.env.services.pos.config;
       console.log(posConfig)

       if (this.get_partner() && posConfig.receipt_partner_details) {
           result.headerData.partner = {}

           if (posConfig.receipt_partner_name) {
               result.headerData.partner.name = this.get_partner().name
           }

           if (posConfig.receipt_partner_address) {
               result.headerData.partner.street = this.get_partner().street
           }
           if (posConfig.receipt_partner_phone) {
               result.headerData.partner.phone = this.get_partner().phone
           }

           if (posConfig.receipt_partner_email) {
               result.headerData.partner.email = this.get_partner().email
           }

           if (posConfig.receipt_partner_vat) {
               result.headerData.partner.vat = this.get_partner().vat
           }
       }
       return result;
   },
}); 