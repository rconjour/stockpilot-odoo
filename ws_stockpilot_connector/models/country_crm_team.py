# Copyright (C) 2025 WeSolved BV <https://wesolved.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class CountryCrmTeam(models.Model):
    _name = "country.crm.team"
    _description = "Country CRM Team"

    country_id = fields.Many2one("res.country", required=True)
    crm_team_id = fields.Many2one("crm.team", string="CRM Team", required=True)
    stockpilot_configuration_id = fields.Many2one(
        "stockpilot.configuration", required=True, ondelete="cascade"
    )

    _sql_constraints = [
        (
            "country_configuration_uniq",
            "unique(country_id, stockpilot_configuration_id)",
            "A CRM team is already defined for this country.",
        )
    ]
