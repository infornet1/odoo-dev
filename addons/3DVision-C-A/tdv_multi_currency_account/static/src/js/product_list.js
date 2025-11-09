/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { registry } from '@web/core/registry';
import { listView } from '@web/views/list/list_view';
import { ListController } from "@web/views/list/list_controller";

export class ProductListController extends ListController {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.dialogService = useService("dialog");
    }

    async onPrintClick() {
        const selectedIds = await this.getSelectedResIds();
        const dialogProps = {
            body: _t(`You want to update ${selectedIds.length || "all"} products`),
            confirm: async () => {
                await this.orm.call('product.template', 'update_price', [selectedIds]);
            },
            cancel: () => {},
        };

        this.dialogService.add(ConfirmationDialog, dialogProps);
    }
}

registry.category('views').add('tdv_multi_currency_account_product_template_tree', {
    ...listView,
    Controller: ProductListController,
    buttonTemplate: 'ProductListView.update_price_button',
});
