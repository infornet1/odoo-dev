/** @odoo-module **/
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen"
import { patch } from "@web/core/utils/patch"
import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";
import { _t } from "@web/core/l10n/translation";
patch(PaymentScreen.prototype, {

  async addNewPaymentLine(paymentMethod){
    console.log('Metodo de Pago:', paymentMethod);
    console.log('is_ref_payment', paymentMethod.is_ref_payment);
    
    // const result = this.currentOrder.add_paymentline(paymentMethod);
    // console.log("result", result)

    if (paymentMethod.is_ref_payment){
      const { confirmed, payload } = await this.popup.add(NumberPopup, {
        title: _t("Referencia de pago"),
        startingValue: paymentMethod.reference || "",
      });

      if (confirmed) {
        console.log("Referencia:", payload);

        // Agregamos la línea de pago al pedido actual
        const paymentline = this.currentOrder.add_paymentline(paymentMethod);
        if (paymentline) {
            paymentline.reference = payload; // Asignar la referencia a la línea de pago
            console.log("Payment line con referencia:", paymentline.reference);
        } else {
            console.error("Error al añadir la línea de pago");
        }
      }
    } else {
    // Si no requiere referencia, simplemente añadimos la línea de pago
    const paymentline = this.currentOrder.add_paymentline(paymentMethod);
    if (paymentline) {
        console.log("Payment line sin referencia:", paymentline.reference);
    } else {
        console.error("Error al añadir la línea de pago");
    }
}

console.log('currentOrder:', this.currentOrder);
}
     
    


    // await this.currentOrder.save();
    
  })


//   if (confirmed) {
//     console.log("Referencia", payload)
//     const paymentline = this.currentOrder.add_paymentline(paymentMethod);
//     console.log("paymentline", paymentline)
//     if(paymentline){
//       paymentline.reference = payload
//     }
//   }
//   console.log('Payment reference:', paymentline.reference);
// }
// console.log('currentOrder:', this.currentOrder);