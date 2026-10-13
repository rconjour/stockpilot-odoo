# Copyright (C) 2026 WeSolved BV <https://wesolved.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class CountryShippingProduct(models.Model):
    _name = "country.shipping.product"
    _description = "Country Shipping Product"

    country_id = fields.Many2one("res.country", required=True)
    shipping_product_id = fields.Many2one(
        "product.product",
        string="Shipping Product",
        required=True,
        domain=[("type", "=", "service")],
    )
    stockpilot_configuration_id = fields.Many2one(
        "stockpilot.configuration", required=True, ondelete="cascade"
    )

    _sql_constraints = [
        (
            "country_configuration_uniq",
            "unique(country_id, stockpilot_configuration_id)",
            "A shipping product is already defined for this country.",
        )
    ]
