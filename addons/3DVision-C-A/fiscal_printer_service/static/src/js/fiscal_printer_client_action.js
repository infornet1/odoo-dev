/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class FiscalPrinterTestAction extends Component {
    setup() {
        this.notification = useService("notification");
        this.rpc = useService("rpc");
        this.action = useService("action");
        this.printerService = useService("fiscal_printer");
        // Execute the action immediately when the component is created
        this.execute(this.props.action.params);
    }

    async execute(params) {
        try {
            // Show loading notification
            this.notification.add("Conectando con la impresora fiscal...", {
                type: "info",
                sticky: false,
            });

            // Configure printer service
            this.printerService.printerConfig = {
                x_fiscal_command_baudrate: 9600,
                connection_type: "serial",
                x_fiscal_commands_time: 750,
            };

            // Set printer details if available
            if (params.usb_vendor_id && params.usb_product_id) {
                this.printerService.printerDetails = {
                    usbVendorId: params.usb_vendor_id,
                    usbProductId: params.usb_product_id,
                };
            }

            // Connect to printer
            const connected = await this.printerService.setPort();
            if (!connected) {
                throw new Error("No se pudo conectar con la impresora fiscal");
            }

            // Send S1 command to get status and registration number
            this.notification.add("Obteniendo información de la impresora fiscal...", {
                type: "info",
                sticky: false,
            });

            const s1Response = await this.printerService.write_s2();

            const s3Response = await this.printerService.write_s3();
            let num_factura = "00000000";
            let num_factura_cn = "00000000";
            let flag_21 = "00";
            let flag_50 = "00";
            let flag_63 = "00";
            if (s3Response && s3Response.machine_flags) {
                flag_21 = s3Response.machine_flags[21];
                flag_50 = s3Response.machine_flags[50];
                flag_63 = s3Response.machine_flags[63];
            }

            if (s1Response && s1Response.num_factura) {
                num_factura = s1Response.num_factura;
            }
            if (s1Response && s1Response.num_refund) {
                num_factura_cn = s1Response.num_refund;
            }

            // Extract registration number from S1 response
            let registrationNumber = null;
            if (s1Response && s1Response.registration_number) {
                // The S1 response contains the registration number in num_factura field
                registrationNumber = s1Response.registration_number.trim();
            } else {
                console.warn("No se pudo obtener el número de registro de la máquina");
                this.notification.add(
                    "Advertencia: No se pudo obtener el número de registro de la máquina",
                    { type: "warning" }
                );
            }
            let current_z_report = "1".padStart(8, '0');
            if (s1Response && s1Response.z_report) {
                current_z_report = s1Response.z_report;
            } else {
                console.warn("No se pudo obtener el número de Z report de la máquina");
                this.notification.add(
                    "Advertencia: No se pudo obtener el número de Z report de la máquina",
                    { type: "warning" }
                );
            }

            const printer_error = await this.printerService.check_printer_status();


            // Close the port
            if (this.printerService.port) {
                await this.printerService.port.close();
            }

            // Call API to test printer with registration number
            const result = await this.rpc("/fiscal_printer/test_connection", {
                printer_id: params.active_id || params.printer_id,
                data: {
                    connection_type: "serial",
                    usb_vendor_id: this.printerService.printerDetails.usbVendorId,
                    usb_product_id: this.printerService.printerDetails.usbProductId,
                    registration_number: registrationNumber,
                    flag_21: flag_21,
                    flag_50: flag_50,
                    flag_63: flag_63,
                    current_z_report: current_z_report,
                    num_factura: num_factura,
                    num_factura_cn: num_factura_cn,
                }
            });

            if (result.success) {
                let message = result.message || "Impresora fiscal conectada correctamente";
                if (registrationNumber) {
                    message += ` - Número de Registro: ${registrationNumber}`;
                }
                this.notification.add(message, { type: "success" });
            } else {
                this.notification.add(
                    result.error || "Error al conectar con la impresora",
                    { type: "danger" }
                );
            }
        } catch (error) {
            console.error("Error al conectar con la impresora:", error);
            this.notification.add(
                `Error de conexión: ${error.message}`,
                { type: "danger" }
            );
        }

        // Redirect to the printer form after testing
        this.action.doAction({
            name: "Impresora Fiscal",
            type: "ir.actions.act_window",
            res_model: "x.pos.fiscal.printer",
            views: [[false, "form"]],
            target: "current",
            res_id: params.active_id || params.printer_id,
        });
    }
}

FiscalPrinterTestAction.template = 'fiscal_printer_service.TestAction';

class FiscalPrinterConnectAction extends Component {
    setup() {
        this.notification = useService("notification");
        this.rpc = useService("rpc");
        this.action = useService("action");
        this.printerService = useService("fiscal_printer");
        // Execute the action immediately when the component is created
        this.execute(this.props.action.params);
    }

    async execute(params) {
        try {
            this.notification.add("Conectando con la impresora fiscal...", {
                type: "info",
                sticky: false,
            });

            // Configure printer service
            this.printerService.printerConfig = {
                x_fiscal_command_baudrate: 9600,
                connection_type: "serial",
                x_fiscal_commands_time: 750,
            };

            // Set printer details if available
            if (params.usb_vendor_id && params.usb_product_id) {
                this.printerService.printerDetails = {
                    usbVendorId: params.usb_vendor_id,
                    usbProductId: params.usb_product_id,
                };
            }

            // Connect to printer
            const connected = await this.printerService.setPort();
            if (!connected) {
                throw new Error("No se pudo conectar con la impresora fiscal");
            }

            const xResponse = await this.printerService.print_report(params.report_type);

            if (params.report_type === "x") {
                this.notification.add("Reporte X impreso correctamente", {
                    type: "success",
                });
            } else if (params.report_type === "z") {
                this.notification.add("Reporte Z impreso correctamente", {
                    type: "success",
                });
                const response = await this.printerService.write_s2();

                await this.rpc("/fiscal_printer/test_connection", {
                    printer_id: params.active_id || params.printer_id,
                    data: {
                        current_z_report: response.z_report,
                    }
                });

            }

            // Close the port
            if (this.printerService.port) {
                await this.printerService.port.close();
            }

        } catch (error) {
            console.error("Error al conectar con la impresora:", error);
            this.notification.add(
                `Error de conexión: ${error.message}`,
                { type: "danger" }
            );
        }

        // Redirect to the printer form after testing
        this.action.doAction({
            name: "Impresora Fiscal",
            type: "ir.actions.act_window",
            res_model: "x.pos.fiscal.printer",
            views: [[false, "form"]],
            target: "current",
            res_id: params.active_id || params.printer_id,
        });
    }
}

FiscalPrinterConnectAction.template = 'fiscal_printer_service.ConnectAction';



// Register the client actions
registry.category("actions").add("fiscal_printer_test", FiscalPrinterTestAction);
registry.category("actions").add("fiscal_printer_connect", FiscalPrinterConnectAction);