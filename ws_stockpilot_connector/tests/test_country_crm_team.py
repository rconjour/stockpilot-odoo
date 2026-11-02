# Copyright (C) 2025 WeSolved BV <https://wesolved.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import psycopg2

from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


class TestCountryCrmTeam(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.country_be = cls.env.ref("base.be")
        cls.country_nl = cls.env.ref("base.nl")
        cls.generic_team = cls.env["crm.team"].create({"name": "Generic Team"})
        cls.be_team = cls.env["crm.team"].create({"name": "Belgian Team"})
        cls.configuration = cls.env["stockpilot.configuration"].create(
            {
                "name": "Test Configuration",
                "crm_team_id": cls.generic_team.id,
            }
        )
        cls.env["country.crm.team"].create(
            {
                "stockpilot_configuration_id": cls.configuration.id,
                "country_id": cls.country_be.id,
                "crm_team_id": cls.be_team.id,
            }
        )

    def test_country_specific_team_is_used(self):
        """A country with a dedicated mapping uses that CRM team."""
        team = self.env["sale.order"]._get_crm_team(
            self.configuration, self.country_be.code
        )
        self.assertEqual(team, self.be_team)

    def test_fallback_to_generic_team(self):
        """A country without a dedicated mapping falls back to the generic team."""
        team = self.env["sale.order"]._get_crm_team(
            self.configuration, self.country_nl.code
        )
        self.assertEqual(team, self.generic_team)

    def test_fallback_when_country_code_missing(self):
        """A missing/empty country code also falls back to the generic team."""
        team = self.env["sale.order"]._get_crm_team(self.configuration, False)
        self.assertEqual(team, self.generic_team)

    def test_no_fallback_configured_returns_empty_team(self):
        """When no generic team is configured either, the lookup returns empty."""
        configuration = self.env["stockpilot.configuration"].create(
            {"name": "No Fallback Configuration"}
        )
        team = self.env["sale.order"]._get_crm_team(
            configuration, self.country_nl.code
        )
        self.assertFalse(team)

    def test_unique_constraint_per_country(self):
        """Only one CRM team can be configured per country and configuration."""
        with mute_logger("odoo.sql_db"), self.assertRaises(psycopg2.IntegrityError):
            self.env["country.crm.team"].create(
                {
                    "stockpilot_configuration_id": self.configuration.id,
                    "country_id": self.country_be.id,
                    "crm_team_id": self.generic_team.id,
                }
            )
            self.env.flush_all()
