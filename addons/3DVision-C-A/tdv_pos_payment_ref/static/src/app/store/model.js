/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Payment } from "@point_of_sale/app/store/models";

patch(Payment.prototype, {
  setup() {
    super.setup(...arguments);
    this.reference = ""
  },

  init_from_JSON(json) {
    super.init_from_JSON(json);
    this.reference = json.reference
  },

  export_as_JSON() {
     const res = super.export_as_JSON(...arguments);
     console.log(res)
     res.reference = this.reference;
     return res;
  }


})