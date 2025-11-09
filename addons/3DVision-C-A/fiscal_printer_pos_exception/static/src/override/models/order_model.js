/** @odoo-module **/

import { Order } from "@point_of_sale/app/store/models"
import { patch } from "@web/core/utils/patch"

patch(Order.prototype, {
    impresa: null,
    num_factura: null,
    fiscal_date: null,
    fiscal_serial: null,
    refund_num_factura: null,
    refund_fiscal_date: null,
    refund_fiscal_serial: null,
    num_report_z: null,
    constructor(obj, options) {
        super.constructor(obj, options);
        this.num_factura ||= false;
        this.impresa ||= false;
        this.fiscal_date ||= false;
        this.fiscal_serial ||= false;
        this.refund_num_factura ||= false;
        this.refund_fiscal_date ||= false;
        this.refund_fiscal_serial ||= false;
        this.num_report_z ||= false;
    },

    init_from_JSON(json) {
        super.init_from_JSON(json);
        this.num_factura = json.num_factura;
        this.impresa = json.impresa;
        this.fiscal_date = json.fiscal_date;
        this.fiscal_serial = json.fiscal_serial;
        this.refund_num_factura = json.refund_num_factura;
        this.refund_fiscal_date = json.refund_fiscal_date;
        this.refund_fiscal_serial = json.refund_fiscal_serial;
        this.num_report_z = json.num_report_z;
    },

    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        json.num_factura = this.num_factura;
        json.fiscal_date = this.fiscal_date;
        json.fiscal_serial = this.fiscal_serial;
        json.refund_num_factura = this.refund_num_factura;
        json.refund_fiscal_date = this.refund_fiscal_date;
        json.refund_fiscal_serial = this.refund_fiscal_serial;
        json.num_report_z = this.num_report_z;
        return json;
    }
});
