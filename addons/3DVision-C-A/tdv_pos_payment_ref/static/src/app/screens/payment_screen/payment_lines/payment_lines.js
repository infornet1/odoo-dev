/** @odoo-module **/

import { PaymentScreenPaymentLines } from "@point_of_sale/app/screens/payment_screen/payment_lines/payment_lines";
import { patch } from "@web/core/utils/patch";
import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";

patch(PaymentScreenPaymentLines.prototype, {

  

  async selectLine(paymentline) {
    console.log('Método de pago:', paymentline.payment_method);
    console.log('is_ref_payment:', paymentline.payment_method.is_ref_payment);

    
    if (paymentline.payment_method.is_ref_payment) {
      const { confirmed, payload } = await this.popup.add(NumberPopup, {
        title: _t("Referecia de pago"),
        startingValue: paymentline.reference || "",
      });
      if (confirmed) {
        paymentline.reference = payload;
      }
    }
  },
})