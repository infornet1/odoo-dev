odoo.define("automate_pos_invoice.PaymentScreen", function (require) {
    "use strict";
    console.log("Custom JavaScript In POS");

    const PaymentScreen = require("point_of_sale.PaymentScreen");
    const Registries = require("point_of_sale.Registries");

    const APIPaymentScreen = (PaymentScreen) =>
        class extends PaymentScreen {
            constructor() {
                super(...arguments);
                if (this.env.pos.config.is_automatic_print) {
                    this.currentOrder.set_to_invoice(true);
                    this.render(true);
                }
            }
            toggleIsToInvoice() {
                if (!this.env.pos.config.is_automatic_print) {
                    super.toggleIsToInvoice();
                }
            }
        };

    Registries.Component.extend(PaymentScreen, APIPaymentScreen);
    return APIPaymentScreen;
});


// odoo.define('automate_pos_invoice.PaymentScreen', function (require) {
//     "use strict";

//     const { patch } = require('@web/core/utils/patch');
//     const { onMounted } = require('@odoo/owl');
//     const { PaymentScreen } = require('point_of_sale.app.screens.payment_screen.payment_screen');

//     patch(PaymentScreen.prototype, {
//         setup() {
//             this._super.apply(this, arguments);
//             console.log("Setup method called");

//             onMounted(() => {
//                 if (this.env.pos.config.is_automatic_print) {
//                     console.log("Automatic pos invoice");
//                     this.currentOrder.set_to_invoice(true);
//                     this.render(true);
//                 }
//             });
//         }
//     });

//     return PaymentScreen;
// });

// import { registry } from "@web/core/registry";
// import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

// export class APIPaymentScreen extends PaymentScreen {
//   constructor() {
//     super.setup(...arguments);
//     console.log("PaymentScreen \n *********");
    
//     if (this.env.pos.config.is_automatic_print) {
//       console.log("Automatic print");
//       this.currentOrder.set_to_invoice(true);
//       this.render(true);
//     }
//   }
//   toggleIsToInvoice() {
//     if (!this.env.pos.config.is_automatic_print) {
//       super.toggleIsToInvoice();
//     }
//   }
// }

/** @odoo-module */

// import { _t } from "@web/core/l10n/translation"
// import {registry} from "@web/core/registry";
// import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
// import {onMounted} from "@odoo/owl";
// import { patch } from "@web/core/utils/patch"

// patch(PaymentScreen.prototype,{
//   setup(){
//     super.setup(...arguments);
//     console.log("Setup method called");

//     onMounted(()=>{

//       if (this.env.pos.config.is_automatic_print){
//         console.log("Automatic pos invoice")
//         this.currentOrder.set_to_invoice(true);
//         this.render(true)
//       }

//     })
//   }
// })
