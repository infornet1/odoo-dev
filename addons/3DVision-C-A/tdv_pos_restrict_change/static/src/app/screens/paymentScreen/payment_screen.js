/** @odoo-module **/

import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { _t } from "@web/core/l10n/translation";

patch(PaymentScreen.prototype, {
	async _isOrderValid(isForceValidate) {
		const baseIsValid = await super._isOrderValid(isForceValidate);
		if (!baseIsValid) return false;

		const order = this.currentOrder;
		if (!order || !order.get_change) return false;

		const change = order.get_change();
		const roundedChange = this.env.utils && this.env.utils.roundCurrency
			? this.env.utils.roundCurrency(change, order.pos.currency)
			: Math.round(change * 1000) / 1000;

		if (roundedChange > 0) {
			await this.popup.add(ErrorPopup, {
				title: _t('Change must be zero'),
				body: _t('Please adjust payments so there is no change to return.'),
			});
			return false;
		}

		return true;
	},
});
