/** @odoo-module **/

import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreen.prototype, {
  setup() {
    super.setup(...arguments);
    console.log("setup");
    console.log("POS Environment:", this.env.services.pos.config.is_automatic_print);
    console.log("PDF", this.env.services.pos.config.is_download_pdf);
    if (this.env.services.pos.config.is_automatic_print) {
      console.log("Automatic POS invoice enabled");
      // Genera la factura
      this.currentOrder.set_to_invoice(true);
      this.render(true);
    }
  },

  toggleIsToInvoice() {
    if (!this.env.services.pos.config.is_automatic_print) {
      super.toggleIsToInvoice();
    }
  },

  shouldDownloadInvoice() {
    const result = super.shouldDownloadInvoice();
    const config = this.env.services.pos.config.is_download_pdf;
    console.log("PDF", config);
    return result && config;
  },
});

// Asegúrate de exportar el módulo si es necesario
export default PaymentScreen;