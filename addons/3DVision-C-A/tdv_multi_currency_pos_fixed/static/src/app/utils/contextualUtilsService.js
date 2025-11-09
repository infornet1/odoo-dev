/** @odoo-module */
import { formatMonetary } from "@web/views/fields/formatters";
import {
    formatFloat,
    roundDecimals,
    floatIsZero as genericFloatIsZero,
} from "@web/core/utils/numbers";
import { escapeRegExp } from "@web/core/utils/strings";
import { registry } from "@web/core/registry";
import { parseFloat } from "@web/views/fields/parsers";

/**
 * This service introduces `utils` namespace in the `env` which can contain
 * functions that are parameterized by the data in `pos` service.
 */
export const contextualUtilsService = {
    dependencies: ["pos", "localization"],
    start(env, { pos, localization }) {
        const currency = pos.currency;
        const productUoMDecimals = pos.dp["Product Unit of Measure"];
        const decimalPoint = localization.decimalPoint;
        const thousandsSep = localization.thousandsSep;
        // Replace the thousands separator and decimal point with regex-escaped versions
        const escapedDecimalPoint = escapeRegExp(decimalPoint);
        let floatRegex;
        if (thousandsSep) {
            const escapedThousandsSep = escapeRegExp(thousandsSep);
            floatRegex = new RegExp(
                `^-?(?:\\d+(${escapedThousandsSep}\\d+)*)?(?:${escapedDecimalPoint}\\d*)?$`
            );
        } else {
            floatRegex = new RegExp(`^-?(?:\\d+)?(?:${escapedDecimalPoint}\\d*)?$`);
        }

        const formatProductQty = (qty) => {
            return formatFloat(qty, { digits: [true, productUoMDecimals] });
        };

        const formatStrCurrency = (valueStr, hasSymbol = true) => {
            return formatCurrency(parseFloat(valueStr), hasSymbol);
        };

        const formatCurrency = (value, hasSymbol=true, currency, noConvert=false) => {
            if (!noConvert){
                value = convertAmount(value, currency);
            }
            return formatMonetary(value, {
                currencyId: (currency && currency.id) || pos.currency.id,
                noSymbol: !hasSymbol,
            });
        };
        const floatIsZero = (value) => {
            return genericFloatIsZero(value, currency.decimal_places);
        };

        const roundCurrency = (value, currency) => {
            return roundDecimals(value, (currency && currency.decimal_places || pos.currency.decimal_places));
        };

        const isValidFloat = (inputValue) => {
            return ![decimalPoint, "-"].includes(inputValue) && floatRegex.test(inputValue);
        };
        const convertAmount = (value, currency) => {
            if (currency && currency != pos.currency)
                return value * currency.rate;
            // if (currency && currency != pos.currency) {
            //     // Usar una precisión más alta para evitar errores de redondeo
            //     const converted = value * currency.rate;
            //     // Redondear con la precisión de la moneda de destino
            //     return roundDecimals(converted, currency.decimal_places);
            // }
            return value
        };
        const inverseConvertAmount = (value, currency) => {
            if (currency && currency != pos.currency)
                return value / currency.rate;
            // if (currency && currency != pos.currency) {
            //     // Usar una precisión más alta para evitar errores de redondeo
            //     const converted = value / currency.rate;
            //     // Redondear con la precisión de la moneda principal
            //     return roundDecimals(converted, pos.currency.decimal_places);
            // }
            return value
        }

        env.utils = {
            formatCurrency,
            formatStrCurrency,
            roundCurrency,
            formatProductQty,
            isValidFloat,
            floatIsZero,
            convertAmount,
            inverseConvertAmount,
        };
    },
};

registry.category("services").add("contextual_utils_service", contextualUtilsService, {force: true});
