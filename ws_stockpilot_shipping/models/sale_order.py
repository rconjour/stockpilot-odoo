# Copyright (C) 2026 WeSolved BV <https://wesolved.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _get_shipping_product(self, stockpilot_configuration_id, country_code):
        """
        Get the shipping product based on the country code using the
        CountryShippingProduct mapping. Falls back to the configuration's
        generic shipping product when no country-specific mapping exists.
        """
        country_shipping_product = self.env["country.shipping.product"].search(
            [
                (
                    "stockpilot_configuration_id",
                    "=",
                    stockpilot_configuration_id.id,
                ),
                ("country_id.code", "=", country_code),
            ],
            limit=1,
        )
        if country_shipping_product:
            return country_shipping_product.shipping_product_id
        return super()._get_shipping_product(stockpilot_configuration_id, country_code)

    def override_order(self, order, order_info):
        """
        Apply the Stockpilot shipping method to the order as an actual Odoo
        delivery carrier, based on the configuration's shipping method
        mapping, so the delivery method is applied to the order rather than
        only reflected through the "Shipping" order line.
        """
        order = super().override_order(order, order_info)
        shipping_lines = ((order_info or {}).get("metadata") or {}).get(
            "shippingLines"
        ) or []
        shipping_title = shipping_lines[0].get("method_title") if shipping_lines else False

        if not shipping_title:
            return order

        mapping = self.env["stockpilot.shipping.method"].search(
            [
                ("stockpilot_configuration_id", "=", order.stockpilot_configuration_id.id),
                ("stockpilot_name", "=", shipping_title),
            ],
            limit=1,
        )
        if mapping and mapping.carrier_id:
            order.carrier_id = mapping.carrier_id.id

        return order
