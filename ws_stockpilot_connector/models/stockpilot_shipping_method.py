# Copyright (C) 2025 WeSolved BV <https://wesolved.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class StockpilotShippingMethod(models.Model):
    _name = "stockpilot.shipping.method"
    _description = "Stockpilot Shipping Method"

    country_id = fields.Many2one("res.country", required=True)
    stockpilot_configuration_id = fields.Many2one(
        "stockpilot.configuration", required=True, ondelete="cascade"
    )
    carrier_id = fields.Many2one("delivery.carrier", required=True)

    _sql_constraints = [
        (
            "country_configuration_uniq",
            "unique(country_id, stockpilot_configuration_id)",
            "A delivery carrier is already defined for this country.",
        )
    ]
