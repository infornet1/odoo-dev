odoo.define("tdv_multi_currency_pos.ProductItem", function (require) {
    'use strict';

    const Registries = require("point_of_sale.Registries");
    const ProductItemPos = require("point_of_sale.ProductItem");

    const ProductItem = (ProductItemPos) =>
        class extends ProductItemPos {

            get refPrice() {
                let pos = this.env.pos;
                const formattedUnitPrice = pos.format_currency(
                    pos.convertAmount(this.props.product.get_display_price(this.pricelist, 1), pos.secondCurrency),
                    'Product Price',
                    pos.secondCurrency
                );
                if (this.props.product.to_weight) {
                    return `${formattedUnitPrice}/${this.env.pos.units_by_id[this.props.product.uom_id[0]].name
                        }`;
                } else {
                    return formattedUnitPrice;
                }
            }
        }

    Registries.Component.extend(ProductItemPos, ProductItem);
    return ProductItem;
});