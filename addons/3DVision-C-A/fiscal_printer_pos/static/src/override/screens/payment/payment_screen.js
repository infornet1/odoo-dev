/** @odoo-module **/

import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { ConfirmPopup } from "@point_of_sale/app/utils/confirm_popup/confirm_popup";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";


export function convert(amount, fixed = 2) {
    return (amount || 0).toFixed(fixed).replace(".", ",");
}

patch(PaymentScreen.prototype, {
    impresa: false,
    setup() {
        super.setup();
        this.currentOrder.set_to_invoice(true);
        this.printerService = useService("fiscal_printer");
        this.printerService.config = {
            x_fiscal_command_baudrate: this.pos.config.x_fiscal_command_baudrate,
            connection_type: this.pos.config.connection_type,
            x_fiscal_commands_time: this.pos.config.x_fiscal_commands_time,
        };

    },
    get order() {
        return (this.constructor.name === "ReprintReceiptScreen")
            ? this.props.order
            : this.currentOrder;
    },
    async validateOrder(isForceValidate) {
        if (!this.currentOrder.partner) {
            const { confirmed } = await this.popup.add(ConfirmPopup, {
                title: _t("Customer Required"),
                body: _t("Customer is required for fiscal printing."),
            });
            if (confirmed) {
                this.selectPartner();
            }
            return;
        }
        try {
            if (!this.currentOrder._isRefundOrder()) {
                const response = await this.doPrinting("fiscal");
                if (response?.continueWithoutInvoice) return await super.validateOrder(isForceValidate);
                if (!response) return false;
            } else {
                const response = await this.doPrinting("notaCredito");
                if (response?.continueWithoutInvoice) return await super.validateOrder(isForceValidate);
                if (!response) return false;
            }
        } catch (error) {
            console.error("Error al imprimir: ", error);
            this.pos.popup.add(ErrorPopup, {
                title: "Error",
                body: error.message,
            });
            return false;
        }
        // return;

        return super.validateOrder(isForceValidate);
    },
    shouldDownloadInvoice() {
        return false;
    },
    toggleIsToInvoice() {
        this.popup.add(ErrorPopup, {
            title: _t("The invoice is required"),
            body: _t("The invoice is required for fiscal printing."),
        });
    },

    async doPrinting(mode) {
        if (!(this.order.get_paymentlines().every(({ x_printer_code }) => Boolean(x_printer_code)))) {
            this.pos.popup.add(ErrorPopup, {
                title: "Error",
                body: "Algunos métodos de pago no tienen código de impresora",
            });
            return;
        }
        if (this.order.impresa) {
            // this.pos.popup.add(ErrorPopup, {
            //     title: "Error",
            //     body: "Documento impreso en máquina fiscal",
            // });
            return true;
        }
        this.printerCommands = [];
        switch (mode) {
            case "noFiscal":
                await this.printNoFiscal();
                break;
            case "fiscal":
                this.printerService.read_s2 = true;
                const invoiceResult = await this.printFiscal();
                if (!invoiceResult || invoiceResult.continueWithoutInvoice) return invoiceResult;
                break;
            case "notaCredito":
                this.printerService.read_s2 = true;
                const result = await this.printNotaCredito();
                if (!result || result.continueWithoutInvoice) return result;

                break;
        }
        //this.printerCommands.unshift("7");

        //debugger;
        if (this.pos.config.connection_type === "api") {
            this.printViaApi();
        } else if (this.pos.config.connection_type === "usb") {
            this.printViaUSB();
        } else {
            const { x_fiscal_printer_usb_vendor_id, x_fiscal_printer_usb_product_id } = this.pos.config;
            if (x_fiscal_printer_usb_vendor_id && x_fiscal_printer_usb_product_id) {
                this.printerService.printerDetails.usbVendorId = x_fiscal_printer_usb_vendor_id;
                this.printerService.printerDetails.usbProductId = x_fiscal_printer_usb_product_id;
            }
            const result = await this.printerService.actionPrint();
            await this.printerService.forceClosePort();
            if (!result) return false;
            this.currentOrder.impresa = true;
            result.z_report = result.z_report || this.pos.config.x_fiscal_printer_z_report_number;
            result.fiscal_date = result.fiscal_date || new Date().toISOString().split("T")[0];
            if (this.currentOrder._isRefundOrder()) {
                if (!result.num_refund) {
                    let askAgain = true;
                    while (askAgain) {
                        const { confirmed: printSuccess } = await this.pos.popup.add(ConfirmPopup, {
                            title: "Impresión de nota de crédito",
                            body: "¿La impresora fiscal imprimió correctamente la nota de crédito?",
                        });
                        if (printSuccess) {
                            const { confirmed, payload } = await this.pos.popup.add(NumberPopup, {
                                title: "Número de nota de crédito",
                                body: "Ingrese el número de la nota de crédito",
                                startingValue: 0,
                                isInputSelected: true,
                                nbrDecimal: 0,
                                inputPrefix: "#",
                            });
                            if (confirmed) {
                                this.currentOrder.refund_num_factura = (payload || "0").padStart(11, "0");
                                this.currentOrder.refund_fiscal_date = new Date().toISOString().split("T")[0];
                                this.currentOrder.refund_fiscal_serial = this.pos.config.x_fiscal_printer_code;
                                this.currentOrder.num_report_z = result.z_report;
                                askAgain = false;
                            } else {
                                // Si no se confirma el número, preguntar si desea reintentar
                                const { confirmed: retry } = await this.pos.popup.add(ConfirmPopup, {
                                    title: "Reintentar",
                                    body: "¿Desea volver a intentar ingresar el número de la nota de crédito?",
                                });
                                askAgain = retry;
                            }
                        } else {
                            // Si la impresión no fue exitosa, preguntar si desea reintentar
                            const { confirmed: retry } = await this.pos.popup.add(ConfirmPopup, {
                                title: "Reintentar impresión",
                                body: "¿Desea volver a intentar la impresión de la nota de crédito?",
                            });
                            if (!retry) {
                                askAgain = false;
                            }
                        }
                    }
                } else {
                    this.currentOrder.refund_num_factura = result.num_refund;
                    this.currentOrder.refund_fiscal_date = result.fiscal_date;
                    this.currentOrder.refund_fiscal_serial = this.pos.config.x_fiscal_printer_code;
                    this.currentOrder.num_report_z = result.z_report;
                }
            } else {
                let askAgain = true;
                if (!result.num_factura) {
                    while (askAgain) {
                        const { confirmed: printSuccess } = await this.pos.popup.add(ConfirmPopup, {
                            title: "Impresión de factura",
                            body: "¿La impresora fiscal imprimió correctamente la factura?",
                        });
                        if (printSuccess) {
                            const { confirmed, payload } = await this.pos.popup.add(NumberPopup, {
                                title: "Número de factura",
                                body: "Ingrese el número de la factura",
                                startingValue: 0,
                                isInputSelected: true,
                                nbrDecimal: 0,
                                inputPrefix: "#",
                            });
                            if (confirmed) {
                                this.currentOrder.num_factura = (payload || "0").padStart(11, "0");
                                this.currentOrder.fiscal_date = new Date().toISOString().split("T")[0];
                                this.currentOrder.fiscal_serial = this.pos.config.x_fiscal_printer_code;
                                this.currentOrder.num_report_z = result.z_report;
                                askAgain = false;
                            }
                        } else {
                            const { confirmed: retry } = await this.pos.popup.add(ConfirmPopup, {
                                title: "Reintentar impresión",
                                body: "¿Desea volver a intentar la impresión de la factura?",
                            });
                            if (!retry) {
                                askAgain = false;
                            }
                        }
                    }
                } else {
                    this.currentOrder.num_factura = result.num_factura;
                    this.currentOrder.fiscal_date = result.fiscal_date;
                    this.currentOrder.fiscal_serial = this.pos.config.x_fiscal_printer_code;
                    this.currentOrder.num_report_z = result.z_report;

                }
            }
            return true;
        }


    },

    async setHeader(payload) {
        const client = this.currentOrder.partner;

        if (payload) {
            if (!payload?.invoiceNumber) {
                const { confirmed } = await this.pos.popup.add(ConfirmPopup, {
                    title: "El numero de factura no esta presente, desea continuar?",
                    body: "¿Desea continuar sin numero de factura?",
                });
                if (confirmed) return { continueWithoutInvoice: true };
            }
            this.printerService.printerCommands.push("iF*" + payload.invoiceNumber.padStart(11, "0"));
            this.printerService.printerCommands.push("iD*" + payload.date);
            this.printerService.printerCommands.push("iI*" + payload.printerCode);
        }
        // Separate client.vat in chunks of 20 characters in a variable named socialReason
        let socialReason = [];
        if (client && client.name) {
            for (let i = 0; i < client.name.length; i += 20) {
                socialReason.push(client.name.substring(i, i + 20));
            }
        }
        this.printerService.printerCommands.push("iR*" + (client.vat || "No tiene"));
        this.printerService.printerCommands.push("iS*" + (socialReason.length > 0 ? socialReason[0] : "No tiene"));

        this.printerService.printerCommands.push("i00Teléfono: " + (client.phone || "No tiene"));
        this.printerService.printerCommands.push("i01Dirección: " + (client.street || "No tiene"));
        this.printerService.printerCommands.push("i02Email: " + (client.email || "No tiene"));
        if (this.order.name) {
            this.printerService.printerCommands.push("i03Ref: " + this.order.name);
        }
        let counter = 0;
        if (socialReason.length > 1) {
            while (counter < socialReason.length && counter < 5) {
                this.printerService.printerCommands.push(`i0${counter + 4}: ` + socialReason[counter]);
                counter++;
            }
        }
        return true;

    },

    setTotal() {
        this.printerService.printerCommands.push("3");
        const aplicar_igtf = this.pos.config.aplicar_igtf;
        const isAboveThreshold = (amount) => amount > 0;
        //validar si todo en divisas
        const es_nota = this.order.get_orderlines().every(({ refunded_orderline_id }) => Boolean(refunded_orderline_id));
        if (es_nota) {
            if (this.order.get_paymentlines().filter(({ amount }) => Boolean(amount < 0)).every(({ isForeignExchange }) => Boolean(isForeignExchange)) && aplicar_igtf) {

                const payment = this.order.get_paymentlines().filter(({ amount }) => Boolean(amount < 0))[0];
                if (payment && Number(payment.x_printer_code) >= 20 && Number(payment.x_printer_code) <= 24) {
                    this.printerService.printerCommands.push("1" + payment.x_printer_code);
                } else {
                    this.printerService.printerCommands.push("122");
                }
            } else {
                this.order.get_paymentlines().filter(({ amount }) => Boolean(amount < 0)).forEach((payment, i, array) => {
                    if (payment.get_ref_amount() < 0) {
                        if ((i + 1) === array.length && this.order.get_paymentlines().filter(({ amount }) => Boolean(amount < 0)).length === 1) {
                            this.printerService.printerCommands.push("1" + payment.x_printer_code);
                        } else {
                            let amount = convert(payment.get_ref_amount());

                            amount = amount.split(",");
                            amount[0] = Math.abs(amount[0]).toString();
                            amount[0] = this.pos.config.flag_21 === '30' ? amount[0].padStart(15, "0") : amount[0].padStart(10, "0");
                            amount = amount.join("");
                            this.printerService.printerCommands.push("2" + payment.x_printer_code + amount);

                        }
                    }
                });
            }
        } else {
            if (this.order.get_paymentlines().filter(({ amount }) => Boolean(amount > 0)).every(({ isForeignExchange }) => Boolean(isForeignExchange)) && aplicar_igtf) {
                const payment = this.order.get_paymentlines().filter(({ amount }) => Boolean(amount > 0))[0];
                if (payment && Number(payment.x_printer_code) >= 20 && Number(payment.x_printer_code) <= 24) {
                    this.printerService.printerCommands.push("1" + payment.x_printer_code);
                } else {
                    this.printerService.printerCommands.push("122");
                }
            } else {
                this.order.get_paymentlines().filter(({ amount }) => Boolean(amount > 0)).forEach((payment, i, array) => {
                    if (payment.get_ref_amount() > 0) {
                        if ((i + 1) === array.length && this.order.get_paymentlines().filter(({ amount }) => Boolean(amount > 0)).length === 1) {
                            this.printerService.printerCommands.push("1" + payment.x_printer_code);
                        } else {
                            let amount = convert(payment.get_ref_amount());

                            amount = amount.split(",");
                            amount[0] = Math.abs(amount[0]).toString();
                            amount[0] = this.pos.config.flag_21 === '30' ? amount[0].padStart(15, "0") : amount[0].padStart(10, "0");
                            amount = amount.join("");
                            this.printerService.printerCommands.push("2" + payment.x_printer_code + amount);

                        }
                    }
                });
            }
        }


        const lastCommand = this.printerService.printerCommands.slice(-1)[0];
        if (!(typeof lastCommand === "string" && /^1\d{2}$/.test(lastCommand))) {
            if (typeof lastCommand === "string" && /^2(\d{2})\d+/.test(lastCommand)) {
                // Replace the last command with "1XX" where XX are the two digits after the "2"
                const match = lastCommand.match(/^2(\d{2})/);
                if (match) {
                    this.printerService.printerCommands[this.printerService.printerCommands.length - 1] = "1" + match[1];
                }
            } else {
                this.printerService.printerCommands.push("101");
            }
        }
        const { x_fiscal_printer_flag_50 } = this.pos.config;
        if (x_fiscal_printer_flag_50 === "01") {
            this.printerService.printerCommands.push("199");
        }
        //this.printerCommands.push("3");
    },

    async printFiscal() {
        const result = await this.setHeader();
        if (!result || result.continueWithoutInvoice) return result;
        this.setLines("GF");
        this.setTotal();
        return true;
    },

    setLines(char) {
        let igtfProduct = null;
        if (this.pos.config.igtf_product_id) {
            igtfProduct = this.pos.db.get_product_by_id(this.pos.config.igtf_product_id[0]);
        }
        this.order
            .get_orderlines()
            .filter((line) => {
                return line.product.id !== igtfProduct?.id && line.get_ref_price_without_tax() !== 0;
            })
            .forEach((line) => {
                //let command = char + "+";
                let command = "";
                const taxes = line.get_taxes();

                if (!(taxes.length) || taxes.every(({ x_tipo_alicuota }) => x_tipo_alicuota === "exento")) {
                    command += "";
                    if (char === "GC") {
                        command += "d0";
                    } else {
                        command += " ";
                    }
                } else if (taxes.every(({ x_tipo_alicuota }) => x_tipo_alicuota === "general")) {

                    if (char === "GC") {
                        command += "d1";
                    } else {
                        command += "!";
                    }
                } else {
                    if (char === "GC") {
                        command += "d0";
                    } else {
                        command += " ";
                    }
                }
                /*else if(taxes.every(({ x_tipo_alicuota }) => x_tipo_alicuota === "reducido")) {
                    command += "2";
                } else {
                    command += "3";
                }*/


                let amount = convert(line.get_ref_price_without_tax() / line.quantity).split(",");
                let quantity = convert(Math.abs(line.quantity), 3).split(",");

                amount[0] = this.pos.config.flag_21 === '30' ? amount[0].padStart(14, "0") : amount[0].padStart(8, "0");
                quantity[0] = this.pos.config.flag_21 === '30' ? quantity[0].padStart(14, "0") : quantity[0].padStart(5, "0");

                amount = amount.join("");
                quantity = quantity.join("");

                command += amount;
                command += `${quantity}`;

                const { product } = line;

                if (product.default_code) {
                    command += `|${product.default_code}|`;
                }

                command += product.display_name;

                this.printerService.printerCommands.push(command);
                //comando tester error
                //this.printerCommands.push('-' + command);

                if (line.discount > 0) {
                    this.printerService.printerCommands.push("q-" + convert(line.discount));
                }

                if (line.customerNote) {
                    if (char === "GC") {
                        this.printerService.printerCommands.push(`A##${line.customerNote}##`);
                    } else {
                        this.printerService.printerCommands.push(`@##${line.customerNote}##`);
                    }
                }

            });
    },

    printNoFiscal() {
        this.order
            .get_orderlines()
            .filter(({ x_is_igtf_line }) => !x_is_igtf_line)
            .forEach((line) => {
                const { product } = line;
                this.printerService.printerCommands.push(`80 ${product.display_name} [${product.default_code}]`);
                this.printerService.printerCommands.push(
                    `80*x${line.quantityStr} ${convert(line.get_ref_price_with_tax())} (${convert(line.get_taxed_lst_unit_price())} C/U)`
                );
            });

        if (this.order.get_change()) {
            this.printerService.printerCommands.push("80*CAMBIO: " + convert(this.order.get_change()));
        }

        this.printerService.printerCommands.push("81$TOTAL: " + convert(this.order.get_total_with_tax()));
    },

    async printNotaCredito() {
        // const { confirmed, payload } = await this.showPopup("NotaCreditoPopUp");
        const { confirmed } = await this.pos.popup.add(ConfirmPopup, {
            title: _t("Nota de crédito"),
            body: _t("¿Desea imprimir la nota de crédito?"),
        });

        if (!confirmed) return false;


        const payload = {
            invoiceNumber: this.currentOrder.num_factura,
            date: this.currentOrder.fiscal_date,
            printerCode: this.currentOrder.fiscal_serial,
        };

        const result = await this.setHeader(payload);
        if (!result || result.continueWithoutInvoice) return result;
        this.setLines("GC");
        this.setTotal();

        return true;
    }
});
