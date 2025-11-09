/** @odoo-module **/

import { Order } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";

const originalOrderExportAsJSON = Order.prototype.export_as_JSON;
const originalOrderInitFromJSON = Order.prototype.init_from_JSON;
const originalOrderSetup = Order.prototype.setup;

patch(Order.prototype, {
    setup(_defaultObj, options) {
        originalOrderSetup.apply(this, arguments);

        if (options && options.json && 'is_refund' in options.json) {
            this.is_refund = options.json.is_refund;
        } else {
            this.is_refund = false;
        }
    },
    
    export_as_JSON() {
        const json = originalOrderExportAsJSON.call(this);
        json.is_refund = this.is_refund || false;
        if (!json.extra_data) {
            json.extra_data = {};
        }
        json.extra_data.is_refund = this.is_refund || false;

        return json;
    },
    
    init_from_JSON(json) {
        originalOrderInitFromJSON.call(this, json);
        this.is_refund = json.is_refund || false;
        this.trigger && this.trigger('change', this);
    },
    
    set_is_refund(val) {
        this.is_refund = !!val;
        this.trigger && this.trigger('change', this);
    },
    
    isRefund() {
        const result = !!this.is_refund;
        return result;
    },
});

const originalSetPricelist = Order.prototype.set_pricelist;
patch(Order.prototype, {
    set_pricelist(pricelist, options = {}) {
        const previousPricelist = this.pricelist;
        
        const isForcedRestoration = options.isForcedRestoration || false;
        
        const isDuringPartnerAssignment = this._isDuringPartnerAssignment || false;
        
        originalSetPricelist.call(this, pricelist);
        
        if (!isForcedRestoration && !isDuringPartnerAssignment && this.paymentlines && this.paymentlines.length > 0) {
            if (previousPricelist && pricelist && previousPricelist.id !== pricelist.id) {
                for (let i = this.paymentlines.length - 1; i >= 0; i--) {
                    this.remove_paymentline(this.paymentlines[i], {force: true});
                }
                
            }
        } else if (isForcedRestoration) {
        } else if (isDuringPartnerAssignment) {
        }
    },
});

const originalSetPartner = Order.prototype.set_partner;
patch(Order.prototype, {
    set_partner(partner) {
        const currentPricelist = this.pricelist;
        
        this._isDuringPartnerAssignment = true;
        
        try {
            const result = originalSetPartner.call(this, partner);
            
            if (currentPricelist && currentPricelist.id) {
                if (this.pricelist && this.pricelist.id !== currentPricelist.id) {
                    this.set_pricelist(currentPricelist, { isForcedRestoration: true });
                    
                }
            }
            
            return result;
        } finally {
            this._isDuringPartnerAssignment = false;
        }
    },
});
