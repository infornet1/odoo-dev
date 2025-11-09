/** @odoo-module **/

import { formView } from "@web/views/form/form_view";
import { registry } from "@web/core/registry";
import { FiscalPrinterFormController } from "./fiscal_printer_form_controller";
import "./fiscal_printer_client_action";
import "../services/printer_service";

// Register the custom form view with our controller
registry.category("views").add("fiscal_printer_form", {
    ...formView,
    Controller: FiscalPrinterFormController,
}); 