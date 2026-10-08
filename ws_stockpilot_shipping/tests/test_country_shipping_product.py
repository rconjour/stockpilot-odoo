# Copyright (C) 2026 WeSolved BV <https://wesolved.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import psycopg2

from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


class TestCountryShippingProduct(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.country_be = cls.env.ref("base.be")
        cls.country_nl = cls.env.ref("base.nl")
        cls.generic_shipping_product = cls.env["product.product"].create(
            {"name": "Generic Shipping", "type": "service"}
        )
        cls.be_shipping_product = cls.env["product.product"].create(
            {"name": "Belgian Shipping", "type": "service"}
        )
        cls.configuration = cls.env["stockpilot.configuration"].create(
            {
                "name": "Test Configuration",
                "shipping_product": cls.generic_shipping_product.id,
            }
        )
        cls.env["country.shipping.product"].create(
            {
                "stockpilot_configuration_id": cls.configuration.id,
                "country_id": cls.country_be.id,
                "shipping_product_id": cls.be_shipping_product.id,
            }
        )

    def test_country_specific_product_is_used(self):
        """A country with a dedicated mapping uses that shipping product."""
        product = self.env["sale.order"]._get_shipping_product(
            self.configuration, self.country_be.code
        )
        self.assertEqual(product, self.be_shipping_product)

    def test_fallback_to_generic_product(self):
        """A country without a dedicated mapping falls back to the generic product."""
        product = self.env["sale.order"]._get_shipping_product(
            self.configuration, self.country_nl.code
        )
        self.assertEqual(product, self.generic_shipping_product)

    def test_fallback_when_country_code_missing(self):
        """A missing/empty country code also falls back to the generic product."""
        product = self.env["sale.order"]._get_shipping_product(
            self.configuration, False
        )
        self.assertEqual(product, self.generic_shipping_product)

    def test_unique_constraint_per_country(self):
        """Only one shipping product can be configured per country and configuration."""
        with mute_logger("odoo.sql_db"), self.assertRaises(psycopg2.IntegrityError):
            self.env["country.shipping.product"].create(
                {
                    "stockpilot_configuration_id": self.configuration.id,
                    "country_id": self.country_be.id,
                    "shipping_product_id": self.generic_shipping_product.id,
                }
            )
            self.env.flush_all()
