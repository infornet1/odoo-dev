/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class FiscalPrinterInvoiceAction extends Component {
    setup() {
        this.notification = useService("notification");
        this.rpc = useService("rpc");
        this.action = useService("action");
        this.printerService = useService("fiscal_printer");
        // Execute the action immediately when the component is created
        this.execute(this.props.action.params);
    }

    getLineCommand(line, invoice_type = "out_invoice") {
        if (invoice_type === "out_invoice") {
            switch (line.tax_ids) {
                case "general":
                    return "!";
                case "exento":
                    return " ";
                default:
                    return " ";
            }
        } else if (invoice_type === "out_refund") {
            switch (line.tax_ids) {
                case "general":
                    return "d1";
                case "exento":
                    return "d0";
                default:
                    return "d0";
            }
        }

    }

    convert(amount, fixed = 2) {
        if (typeof amount === "string") {
            amount = parseFloat(amount);
        }
        return (amount || 0).toFixed(fixed).replace(".", ",");
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

            // Print the invoice using the printer service
            this.notification.add("Imprimiendo factura...", {
                type: "info",
                sticky: false,
            });

            // Here you would call the actual printing method from the printer service
            // For now, we'll simulate the printing
            this.printerService.printerCommands = [];
            const invoice = params.invoice_data;
            if (invoice.type === "out_refund") {
                this.printerService.printerCommands.push("iF*" + invoice.ticket_ref.padStart(11, "0"));
                this.printerService.printerCommands.push("iD*" + invoice.fp_serial_date);
                this.printerService.printerCommands.push("iI*" + invoice.fp_serial_num);
            }
            this.printerService.printerCommands.push("iR*" + (invoice.partner_id.vat || "No tiene"));
            this.printerService.printerCommands.push("iS*" + invoice.partner_id.name);
            this.printerService.printerCommands.push("i00Teléfono: " + (invoice.partner_id.phone || "No tiene"));
            this.printerService.printerCommands.push("i01Dirección: " + (invoice.partner_id.street || "No tiene"));
            this.printerService.printerCommands.push("i02Email: " + (invoice.partner_id.email || "No tiene"));
            if (invoice.name) {
                this.printerService.printerCommands.push("i03Ref: " + invoice.name);
            }

            invoice.invoice_line_ids.forEach(line => {
                let command = this.getLineCommand(line, invoice.type);
                let amount = this.convert(line.price_unit, 2).split(",");
                let quantity = this.convert(line.product_qty, 3).split(",");
                amount[0] = params.flag_21 === '30' ? amount[0].padStart(14, "0") : amount[0].padStart(8, "0");
                quantity[0] = params.flag_21 === '30' ? quantity[0].padStart(14, "0") : quantity[0].padStart(5, "0");
                amount = amount.join("");
                quantity = quantity.join("");
                command += amount;
                command += quantity;
                if (line.default_code) {
                    command += "|" + line.default_code + "|";
                }
                command += line.name;
                this.printerService.printerCommands.push(command);
                if (line.discount > 0) {
                    this.printerService.printerCommands.push("q-" + this.convert(line.discount));
                }
                if (line.note) {
                    if (invoice.type === "out_refund") {
                        this.printerService.printerCommands.push(`A##${line.customerNote}##`);
                    } else {
                        this.printerService.printerCommands.push(`@##${line.customerNote}##`);
                    }
                }
            });
            this.printerService.printerCommands.push("3");
            invoice.payment.forEach((payment, i) => {
                if (i === invoice.payment.length - 1) {
                    this.printerService.printerCommands.push("1" + payment.fp_type);
                } else {
                    let amount = this.convert(`${payment.amount}`).split(",");
                    amount[0] = Math.abs(amount[0]).toString();
                    amount[0] = params.flag_21 === '30' ? amount[0].padStart(15, "0") : amount[0].padStart(10, "0");
                    amount = amount.join("");
                    this.printerService.printerCommands.push("2" + payment.fp_type + amount);
                }
            });
            if (params.flag_50 === "01") {
                this.printerService.printerCommands.push("199");
            }
            this.printerService.read_s2 = true;
            const printResult = await this.printerService.actionPrint();

            await this.printerService.forceClosePort();
            const invoice_data = {
                fp_serial_date: printResult.fiscal_date,
                num_report_z: printResult.z_report,
                fp_serial_num: printResult.registration_number,
            }
            if (invoice.type === "out_refund") {
                invoice_data.cn_ticket_ref = printResult.num_refund;
            } else {
                invoice_data.ticket_ref = printResult.num_factura;
            }

            // Call the backend to log the transaction
            const result = await this.rpc("/fiscal_printer/print_invoice", {
                invoice_id: params.res_id,
                invoice_data
            });

            if (result.success) {
                this.notification.add(result.message || "Factura impresa correctamente", {
                    type: "success"
                });
            } else {
                this.notification.add(
                    result.error || "Error al imprimir la factura",
                    { type: "danger" }
                );
            }

        } catch (error) {
            console.error("Error al imprimir factura:", error);
            this.notification.add(
                `Error de impresión: ${error.message}`,
                { type: "danger" }
            );
        }

        // Redirect back to the invoice form
        if (params.res_model && params.res_id) {
            this.action.doAction({
                name: "Factura",
                type: "ir.actions.act_window",
                res_model: params.res_model,
                views: [[false, "form"]],
                target: "current",
                res_id: params.res_id,
            });
        }
    }
}

FiscalPrinterInvoiceAction.template = 'fiscal_printer_service.InvoiceAction';

registry.category("actions").add("fiscal_printer_invoice", FiscalPrinterInvoiceAction); 
