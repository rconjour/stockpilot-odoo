# Copyright (C) 2025 WeSolved BV <https://wesolved.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class StockpilotShippingMethod(models.Model):
    _name = "stockpilot.shipping.method"
    _description = "Stockpilot Shipping Method"

    stockpilot_configuration_id = fields.Many2one(
        "stockpilot.configuration", required=True, ondelete="cascade"
    )
    stockpilot_name = fields.Char(required=True)
    carrier_id = fields.Many2one("delivery.carrier", required=True)
