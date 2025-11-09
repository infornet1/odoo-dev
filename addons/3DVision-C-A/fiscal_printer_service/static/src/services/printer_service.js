/** @odoo-module **/

import { registry } from "@web/core/registry";

const encoder = new TextEncoder();

const CHAR_MAP = {
    "ñ": "n",
    "Ñ": "N",
    "á": "a",
    "é": "e",
    "í": "i",
    "ó": "o",
    "ú": "u",
    "Á": "A",
    "É": "E",
    "Í": "I",
    "Ó": "O",
    "Ú": "U",
    "ä": "a",
    "ë": "e",
    "ï": "i",
    "ö": "o",
    "ü": "u",
    "Ä": "A",
    "Ë": "E",
    "Ï": "I",
    "Ö": "O",
    "Ü": "U",
};

const EXPRESSION = new RegExp(`[${Object.keys(CHAR_MAP).join("")}]`, "g");

export function sanitize(string) {
    return string.replace(EXPRESSION, (char) => CHAR_MAP[char]);
}

export function toBytes(command) {
    const commands = Array.from(encoder.encode(command));

    commands.push(3);
    commands.push(commands.reduce((prev, curr) => prev ^ curr, 0));
    commands.unshift(2);

    return new Uint8Array(commands);
}

export const printerService = {
    start() {

        return {
            timeout: null,
            printerCommands: [],
            printing: false,
            read_s2: false,
            read_Z: false,
            writer: false,
            reader: false,
            serialPort: null,
            verificar_desconexion: false,
            _printerConfig: {
                x_fiscal_command_baudrate: 9600,
                connection_type: "serial",
                x_fiscal_commands_time: 10,
            },
            currentReader: null,
            printerDetails: {
                usbProductId: null,
                usbVendorId: null,
            },

            set printerConfig(config) {
                this._printerConfig = { ...this._printerConfig, ...config };
            },

            get reader() {
                return this.serialPort?.readable?.getReader();
            },

            get port() {
                return this.serialPort;
            },

            set port(serialPort) {
                this.serialPort = serialPort;
            },
            setup(...args) {
                this.setup(...args);
            },
            async forceClosePort() {
                try {
                    if (this.serialPort) {
                        await this.serialPort.close();
                        this.serialPort = null;
                    }
                }
                catch (error) {
                    console.error("Error al cerrar el puerto: ", error);
                }
            },

            async setPort() {
                try {
                    const options = {}
                    if (typeof this.printerDetails.usbProductId === "string") {
                        this.printerDetails.usbProductId = parseInt(this.printerDetails.usbProductId, 10);
                    }
                    if (typeof this.printerDetails.usbVendorId === "string") {
                        this.printerDetails.usbVendorId = parseInt(this.printerDetails.usbVendorId, 10);
                    }
                    if (this.printerDetails.usbProductId && this.printerDetails.usbVendorId) {
                        options.filters = [{ usbVendorId: this.printerDetails.usbVendorId, usbProductId: this.printerDetails.usbProductId }];
                    }
                    const availablePorts = await navigator.serial.getPorts();
                    for (const port of availablePorts) {
                        if (port.getInfo().usbProductId === this.printerDetails.usbProductId && port.getInfo().usbVendorId === this.printerDetails.usbVendorId) {
                            await this.forceClosePort();
                            await port.open({
                                baudRate: this._printerConfig.x_fiscal_command_baudrate || 9600,
                                parity: "even",
                                dataBits: 8,
                                stopBits: 1,
                                bufferSize: 256,
                            });
                            this.serialPort = port;
                            return true;
                        }
                    }
                    const port = await navigator.serial.requestPort(options);
                    await port.open({
                        baudRate: this._printerConfig.x_fiscal_command_baudrate || 9600,
                        parity: "even",
                        dataBits: 8,
                        stopBits: 1,
                        bufferSize: 256,
                    });
                    this.serialPort = port;
                    this.printerDetails = port.getInfo();

                    return true;
                } catch (error) {
                    console.error("Error al abrir el puerto: ", error);
                    this.serialPort = this.printing = this.writer = false;
                    return false;
                }
            },

            async releaseReader() {
                if (this.currentReader) {
                    await this.currentReader.releaseLock();
                    this.currentReader = null;
                }
                this.currentReader = this.port.readable.getReader();
            },

            async releaseWriter() {
                if (this.writer) {
                    await this.writer.releaseLock();
                    this.writer = null;
                }
                this.writer = this.port.writable.getWriter();
            },

            async escribe_leer(command, is_linea) {
                console.log("🚀 ~ escribe_leer ~ command:", command)
                if (!this.port) return false;
                var comando_cod = toBytes(command);
                await this.releaseWriter();
                await this.releaseReader();
                var signals_to_send = { dataTerminalReady: true };
                if (this._printerConfig.connection_type === "usb_serial") {
                    signals_to_send = { requestToSend: true };
                }
                await this.port.setSignals(signals_to_send);
                // var signals = await this.port.getSignals();
                // if (signals.clearToSend || signals.dataSetReady) {
                if (true) {
                    await this.writer.write(comando_cod);
                    await this.writer.releaseLock();
                    this.writer = false;
                    if (this.read_Z) {

                        await new Promise(resolve => setTimeout(resolve, 12000));
                    }

                    while (!this.port.readable) {
                        if (this.currentReader) {
                            await this.currentReader.releaseLock();
                            this.currentReader = false;
                        }
                        await new Promise(resolve => setTimeout(resolve, 50));
                    }
                    await new Promise(resolve => setTimeout(resolve, 10));
                    if (this.currentReader) {
                        await this.currentReader.releaseLock();
                        this.currentReader = false;
                    }
                    if (this.port.readable) {
                        this.currentReader = this.port.readable.getReader();
                        var leer = true;
                    } else {
                        var leer = false;
                    }
                    var esperando = 0;
                    while (leer) {
                        try {
                            await this.releaseReader();
                            const { value, done } = await this.currentReader.read();
                            if (value.byteLength >= 1) {
                                if (value[0] == 6) {
                                    leer = false;
                                    await this.currentReader.releaseLock();
                                    this.currentReader = false;
                                    return true;
                                } else {
                                    leer = false;
                                    await this.currentReader.releaseLock();
                                    this.currentReader = false;
                                    await new Promise(resolve => setTimeout(resolve, 100));
                                    this.writer = this.port.writable.getWriter();
                                    var comando_desbloqueo = ["7"];
                                    var comando_desbloqueo = comando_desbloqueo.map(toBytes);
                                    for (const command of comando_desbloqueo) {
                                        await new Promise(resolve => setTimeout(resolve, 750));
                                        await this.writer.write(command);
                                    }
                                    await this.writer.releaseLock();
                                    this.writer = false;
                                    this.printing = false;
                                    return true;
                                }
                            } else {
                                esperando++;
                                await new Promise(resolve => setTimeout(resolve, 200));
                            }
                            if (esperando > 20) {
                                await this.currentReader.releaseLock();
                                this.currentReader = false;
                                var comando_desbloqueo = ["7"];
                                var comando_desbloqueo = comando_desbloqueo.map(toBytes);
                                this.writer = this.port.writable.getWriter();
                                for (const command of comando_desbloqueo) {
                                    await new Promise(resolve => setTimeout(resolve, 750));
                                    await this.writer.write(command);
                                }
                                await this.writer.releaseLock();
                                this.writer = false;
                                this.printing = false;
                                return true;
                            }
                        } catch (error) {
                            leer = false;
                            if (this.currentReader) {
                                this.currentReader.releaseLock();
                                this.currentReader = false;
                            }
                            var comando_desbloqueo = ["7"];
                            var comando_desbloqueo = comando_desbloqueo.map(toBytes);
                            this.writer = this.port.writable.getWriter();
                            for (const command of comando_desbloqueo) {
                                await new Promise(resolve => setTimeout(resolve, 750));
                                await this.writer.write(command);
                            }
                            await this.writer.releaseLock();
                            this.writer = false;
                            this.printing = false;

                            return false;
                        }
                    }
                } else {
                    await this.writer.releaseLock();
                    this.writer = false;
                    this.printing = false;
                    return false;
                }

            },
            async write() {
                this.modal_imprimiendo = Swal.fire({
                    title: 'Imprimiendo',
                    text: 'Por favor espere.',
                    imageUrl: '/fiscal_printer_service/static/src/image/impresora.gif',
                    imageWidth: 100,
                    imageHeight: 100,
                    imageAlt: 'Imprimiendo',
                    allowOutsideClick: false,
                    allowEscapeKey: false,
                    allowEnterKey: false,
                    showConfirmButton: false,
                });


                const TIME = this._printerConfig.x_fiscal_commands_time || 750;
                this.printing = true;
                // this.printerCommands = ['7', ...this.printerCommands]
                this.printerCommands = this.printerCommands.map(sanitize);

                var cantidad_comandos = this.printerCommands.length;
                for (const command of this.printerCommands) {
                    var is_linea = false;
                    if (command.substring(0, 1) === ' ' || command.substring(0, 1) === '!' || command.substring(0, 1) === 'd' || command.substring(0, 1) === '-') {
                        is_linea = true;
                    }
                    if (this.printing) {

                        await this.escribe_leer(command, is_linea);
                        cantidad_comandos--;
                    }
                }
                this.modal_imprimiendo.close();
                if (cantidad_comandos == 0) {

                    Swal.fire({
                        position: 'top-end',
                        icon: 'success',
                        title: 'Impresión finalizada con éxito',
                        showConfirmButton: false,
                        timer: 1500
                    });
                    if (this.order) {
                        this.order.impresa = true;
                    }

                } else {
                    Swal.fire({
                        position: 'top-end',
                        icon: 'error',
                        title: 'Error en impresion, factura anulada',
                        showConfirmButton: false,
                        timer: 2500
                    });
                }

                window.clearTimeout(this.timeout || 1500);
                this.printerCommands = [];
                this.printing = false;
                if (this.writer) {
                    this.writer.releaseLock();
                }
                this.writer = false;

                let result = {}
                if (this.read_s2 && cantidad_comandos == 0) {
                    await new Promise(resolve => setTimeout(resolve, 1000));
                    const s2Result = await this.write_s2();
                    Object.assign(result, s2Result);
                }
                if (this.read_Z) {
                    const { confirmed } = await this.showPopup("ReporteZPopUp", { cancelKey: "Q", confirmKey: "Y" });
                    if (confirmed) {
                        await this.write_Z();
                    }

                }
                await this.forceClosePort();
                return result;
            },

            async check_printer_status() {
                // INSERT_YOUR_CODE
                /**
                 * Decodes the status byte from the fiscal printer and returns a human-readable message.
                 * @param {string|number} statusByte - The status byte as a hex string (e.g., "0x40") or number.
                 * @returns {string} - The decoded status message.
                 */
                function decodePrinterStatus(statusByte) {

                    switch (statusByte) {

                        case String.fromCharCode(parseInt(0x40, 16)):
                            return "Ningún error";
                        case String.fromCharCode(parseInt(0x48, 16)):
                            return "Error gaveta";
                        case String.fromCharCode(parseInt(0x41, 16)):
                            return "Error sin papel";
                        case String.fromCharCode(parseInt(0x42, 16)):
                            return "Error mecánico de la impresora / papel";
                        case String.fromCharCode(parseInt(0x43, 16)):
                            return "Error mecánico de la impresora y fin de papel";
                        case String.fromCharCode(parseInt(0x60, 16)):
                            return "Error fiscal";
                        case String.fromCharCode(parseInt(0x64, 16)):
                            return "Error en la memoria fiscal";
                        case String.fromCharCode(parseInt(0x6C, 16)):
                            return "Error memoria fiscal llena";
                        default:
                            return `Código de estado desconocido: 0x${statusByte}`;
                    }
                }

                await this.setPort();

                const statusCommand = '\x05';
                await this.sendCommand(statusCommand);
                await new Promise(resolve => setTimeout(resolve, 2000));
                const portResponse = await this.readPortResponse();
                return portResponse;
            },

            async sendCommand(command) {
                this.writer = this.port.writable.getWriter();
                const TIME = this._printerConfig.x_fiscal_commands_time || 750;
                this.printerCommands = [command];
                this.printerCommands = this.printerCommands.map(toBytes);

                for (const cmd in this.printerCommands) {
                    await this.writer.write(this.printerCommands[cmd]);
                }
                window.clearTimeout(this.timeout || 1500);
                this.printerCommands = [];
                await this.writer.releaseLock();
                this.writer = false;
            },

            async readPortResponse() {
                var signals_to_send = { dataTerminalReady: true };
                if (this._printerConfig.connection_type === "usb_serial") {
                    signals_to_send = { requestToSend: true };
                }
                await this.port.setSignals(signals_to_send);
                const signals = await this.port.getSignals();

                // if (signals.clearToSend || signals.dataSetReady) {
                if (true) {
                    if (this.currentReader) {
                        this.currentReader.releaseLock();
                        this.currentReader = false;
                    }
                    if (this.port.readable) {
                        this.currentReader = this.port.readable.getReader();
                    }
                    var leer = true;
                    var contador = 0;
                    var response = {};

                    while (this.port.readable && leer) {
                        try {
                            while (leer) {
                                const { value, done } = await this.currentReader.read();

                                var string = await new TextDecoder().decode(value);

                                if (string.length > 0) {
                                    const myArray = string.split('\n');

                                    // Store the full response array for processing
                                    response.raw_data = myArray;

                                    await this.currentReader.releaseLock();
                                    this.currentReader = false;
                                    leer = false;
                                    break;
                                } else {
                                    contador++;
                                    await new Promise(resolve => setTimeout(resolve, 750));
                                    if (contador > 10) {
                                        await this.currentReader.releaseLock();
                                        this.currentReader = false;
                                        leer = false;
                                        break;
                                    }
                                }
                            }
                        } catch (error) {
                            leer = false;
                            console.error(error);
                        } finally {
                            leer = false;
                            console.error("Finalizado");
                        }
                    }

                    return response;
                }

                return {};
            },

            async write_s2() {
                let maxRetries = 30;
                let attempt = 0;
                let portResponse = {};
                let requiredFieldsPresent = false;

                while (attempt < maxRetries && !requiredFieldsPresent) {
                    await this.setPort();
                    //to obtain the S1 report of the machine
                    await this.sendCommand("S1");
                    await new Promise(resolve => setTimeout(resolve, 1000));
                    portResponse = await this.readPortResponse();

                    if (portResponse.raw_data) {
                        const myArray = portResponse.raw_data;
                        const num_factura = myArray[2];
                        const num_refund = myArray[6];
                        const z_report = myArray[11];
                        const registrationNumber = myArray[13];

                        // Check if all required fields are present
                        if (num_factura && num_refund && registrationNumber && z_report) {
                            requiredFieldsPresent = true;
                        }

                        if (num_factura) {
                            portResponse.num_factura = num_factura;
                            if (registrationNumber) {
                                portResponse.registration_number = registrationNumber;
                            }
                        }
                        if (num_refund) {
                            portResponse.num_refund = num_refund;
                        }
                        if (z_report) {
                            portResponse.z_report = (parseInt(z_report, 10) + 1).toString().padStart(8, '0');
                        }
                    }

                    if (!requiredFieldsPresent) {
                        attempt++;
                        if (attempt < maxRetries) {
                            console.warn(`write_s2: Missing required fields in response, retrying (${attempt}/${maxRetries})...`);
                            // Optionally wait a bit before retrying
                            await new Promise(resolve => setTimeout(resolve, 500));
                        }
                    }
                }

                this.printerCommands = [];
                this.read_s2 = false;
                //i need date in the format 'Y-m-d'
                portResponse.fiscal_date = new Date().toISOString().split("T")[0];
                return portResponse;
            },

            async write_s3() {
                let attempt = 0;
                const maxRetries = 30;
                let portResponse = {};
                let requiredFieldsPresent = false;

                while (attempt < maxRetries && !requiredFieldsPresent) {
                    await this.setPort();
                    await this.sendCommand("S3");
                    await new Promise(resolve => setTimeout(resolve, 1000));
                    portResponse = await this.readPortResponse();

                    if (portResponse.raw_data) {
                        const myArray = portResponse.raw_data;
                        const machineFlags = myArray[3];
                        if (machineFlags) {
                            // machineFlags is a string, separate into an array by every 2 characters
                            const machineFlagsArray = machineFlags.match(/.{1,2}/g) || [];
                            portResponse.machine_flags = machineFlagsArray;
                            // Ensure machineFlagsArray has at least 50 or 63 items
                            if (machineFlagsArray.length >= 63) {
                                requiredFieldsPresent = true;
                            }
                        }
                    }

                    if (!requiredFieldsPresent) {
                        attempt++;
                        if (attempt < maxRetries) {
                            console.warn(`write_s3: Missing required fields in response, retrying (${attempt}/${maxRetries})...`);
                            await new Promise(resolve => setTimeout(resolve, 500));
                        }
                    }
                }

                this.printerCommands = [];
                portResponse.fiscal_date = new Date().toISOString().split("T")[0];
                return portResponse;
            },

            async generateReport(reportType) {
                await this.sendCommand(reportType);
                const portResponse = await this.readPortResponse();

                if (portResponse.raw_data) {
                    const myArray = portResponse.raw_data;

                    // Process response based on report type
                    switch (reportType) {
                        case "S1":
                            var num_factura = myArray[2];
                            const registrationNumber = myArray[13];

                            if (num_factura) {
                                portResponse.num_factura = num_factura;
                                if (registrationNumber) {
                                    portResponse.registration_number = registrationNumber;
                                }
                            }
                            break;
                        case "S2":
                            // Process S2 report data
                            // Add specific S2 processing logic here
                            break;
                        case "S3":
                            // Process S3 report data
                            // Add specific S3 processing logic here
                            break;
                        default:
                        // Process other report types
                    }
                }

                this.printerCommands = [];
                portResponse.fiscal_date = new Date().toISOString().split("T")[0];
                return portResponse;
            },

            async print_report(reportType) {
                await this.setPort();
                switch (reportType) {
                    case "x":
                        await this.sendCommand("I0X");
                        break;
                    case "z":
                        await this.sendCommand("I0Z");
                        break;
                }
                await new Promise(resolve => setTimeout(resolve, 30000));
                const portResponse = await this.readPortResponse();
                return portResponse;

            },

            obtenerComandoU4ConFormatoEspecifico() {
                const fecha = new Date();

                // Obtener día (DD)
                const dia = String(fecha.getDate()).padStart(2, '0');

                // Obtener mes (MMM) - se añade 1 porque getMonth() es base 0, y se padStart a 3 dígitos
                const mes = String(fecha.getMonth() + 1).padStart(3, '0');

                // Obtener año (YY) - los dos últimos dígitos
                const año = String(fecha.getFullYear()).slice(-2);

                // Construir la fecha formateada como DDMMMYY
                const fechaFormateada = dia + mes + año;

                // Construir el comando U4 con la fecha actual como rango de inicio y fin
                const comandoU4 = `U4z${fechaFormateada}${fechaFormateada}`;

                return comandoU4;
            },

            async write_Z() {
                this.writer = this.port.writable.getWriter();
                const TIME = this._printerConfig.x_fiscal_commands_time || 750;
                this.printerCommands = [this.obtenerComandoU4ConFormatoEspecifico()];
                this.printerCommands = this.printerCommands.map(toBytes);

                for (const command in this.printerCommands) {
                    await this.writer.write(this.printerCommands[command]);
                }
                window.clearTimeout(this.timeout || 1500);
                this.printerCommands = [];
                this.writer.releaseLock();
                this.writer = false;
                await new Promise(resolve => setTimeout(resolve, 12000));

                this.currentReader = false;
                if (this.port.readable) {
                    this.currentReader = this.port.readable.getReader();
                }

                while (this.port.readable && this.read_Z) {
                    try {
                        while (this.read_Z) {
                            const { value, done } = await this.currentReader.read();
                            if (done) {

                                this.read_Z = false;
                                this.currentReader.releaseLock();
                                this.currentReader = false;
                                this.read_Z = false;
                                break;
                            }
                            var string = new TextDecoder().decode(value);

                            const myArray = string.split('\n');

                        }
                    } catch (error) {
                        console.error(error);
                        this.read_Z = false;
                    }
                }

                this.printerCommands = [];
                this.read_Z = false;
            },

            async actionPrint() {
                const result = await this.setPort();
                if (!result) throw new Error("Error al abrir el puerto");
                try {
                    return this.write();

                } catch (error) {
                    console.error(error);
                    this.serialPort = this.printing = this.writer = false;
                    return false;
                }
            }
        }
    },
};

registry.category("services").add("fiscal_printer", printerService);
