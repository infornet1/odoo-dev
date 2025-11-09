// @odoo-module

import { patch } from "@web/core/utils/patch";
import { PartnerListScreen } from "@point_of_sale/app/screens/partner_list/partner_list";

// Patch the PartnerListScreen component
patch(PartnerListScreen.prototype, {
    // Override the saveChanges method
    async saveChanges(processedChanges) {
        let posClientCategoryId = this.pos.config.pos_client_category_id;
        if (Array.isArray(posClientCategoryId) && posClientCategoryId.length > 0 && typeof posClientCategoryId[0] === 'number') {
            posClientCategoryId = posClientCategoryId[0];
        }
        if (typeof posClientCategoryId !== 'number') {
            posClientCategoryId = false;
        }

        if (this.pos.config.restrict_partner_by_tag && posClientCategoryId && processedChanges.id === false) {
            let currentCategoryIds = [];

            if (Array.isArray(processedChanges.category_id)) {
                if (processedChanges.category_id.length > 0) {
                    if (Array.isArray(processedChanges.category_id[0]) && processedChanges.category_id[0].length === 3 && processedChanges.category_id[0][0] === 6 && Array.isArray(processedChanges.category_id[0][2])) {
                        currentCategoryIds = processedChanges.category_id[0][2].filter(id => typeof id === 'number');
                    } else if (processedChanges.category_id.every(id => typeof id === 'number')) {
                        currentCategoryIds = processedChanges.category_id.filter(id => typeof id === 'number');
                    } else {
                        currentCategoryIds = [];
                    }
                } else {
                    currentCategoryIds = [];
                }
            } else if (processedChanges.category_id !== null && processedChanges.category_id !== undefined) {
                currentCategoryIds = [];
            } else {
                currentCategoryIds = [];
            }

            if (!currentCategoryIds.includes(posClientCategoryId)) {
                currentCategoryIds.push(posClientCategoryId);
            }
            processedChanges.category_id = [[6, 0, currentCategoryIds]];
        }
        return super.saveChanges(...arguments);
    },
}); 