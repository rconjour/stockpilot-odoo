# Copyright (C) 2025 WeSolved BV <https://wesolved.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class TestCountryFbaWarehouse(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.country_nl = cls.env["res.country"].search([("code", "=", "NL")], limit=1)
        cls.default_warehouse = cls.env["stock.warehouse"].search([], limit=1)
        cls.external_warehouse = cls.env["stock.warehouse"].create(
            {"name": "External Warehouse", "code": "EXTWH"}
        )
        cls.fba_warehouse_1 = cls.env["stock.warehouse"].create(
            {"name": "FBA Warehouse 1", "code": "FBA1"}
        )
        cls.fba_warehouse_2 = cls.env["stock.warehouse"].create(
            {"name": "FBA Warehouse 2", "code": "FBA2"}
        )
        cls.configuration = cls.env["stockpilot.configuration"].create(
            {
                "name": "Test Configuration",
                "default_warehouse_id": cls.default_warehouse.id,
                "external_warehouse_id": cls.external_warehouse.id,
            }
        )

    def test_fba_warehouse_falls_back_to_external_warehouse_without_mapping(self):
        warehouse = self.env["sale.order"]._get_warehouse(
            self.configuration, self.country_nl.code, is_external=True
        )
        self.assertEqual(warehouse, self.external_warehouse)

    def test_fba_warehouse_single_mapping_is_used(self):
        self.env["country.fba.warehouse"].create(
            {
                "stockpilot_configuration_id": self.configuration.id,
                "country_id": self.country_nl.id,
                "warehouse_id": self.fba_warehouse_1.id,
            }
        )
        warehouse = self.env["sale.order"]._get_warehouse(
            self.configuration, self.country_nl.code, is_external=True
        )
        self.assertEqual(warehouse, self.fba_warehouse_1)

    def test_fba_warehouse_multiple_mappings_without_products_uses_sequence(self):
        self.env["country.fba.warehouse"].create(
            {
                "stockpilot_configuration_id": self.configuration.id,
                "country_id": self.country_nl.id,
                "warehouse_id": self.fba_warehouse_2.id,
                "sequence": 20,
            }
        )
        self.env["country.fba.warehouse"].create(
            {
                "stockpilot_configuration_id": self.configuration.id,
                "country_id": self.country_nl.id,
                "warehouse_id": self.fba_warehouse_1.id,
                "sequence": 10,
            }
        )
        warehouse = self.env["sale.order"]._get_warehouse(
            self.configuration, self.country_nl.code, is_external=True
        )
        self.assertEqual(warehouse, self.fba_warehouse_1)

    def test_fba_warehouse_multiple_mappings_picks_highest_stock(self):
        product = self.env["product.product"].create(
            {"name": "FBA Test Product", "type": "product"}
        )
        stockpilot_product = self.env["stockpilot.product.product"].create(
            {
                "stockpilot_configuration_id": self.configuration.id,
                "product_product_id": product.id,
                "stockpilot_id": "sp-test-product-1",
            }
        )
        self.env["country.fba.warehouse"].create(
            {
                "stockpilot_configuration_id": self.configuration.id,
                "country_id": self.country_nl.id,
                "warehouse_id": self.fba_warehouse_1.id,
                "sequence": 10,
            }
        )
        self.env["country.fba.warehouse"].create(
            {
                "stockpilot_configuration_id": self.configuration.id,
                "country_id": self.country_nl.id,
                "warehouse_id": self.fba_warehouse_2.id,
                "sequence": 20,
            }
        )
        self.env["stock.quant"]._update_available_quantity(
            product, self.fba_warehouse_2.lot_stock_id, 10
        )

        order_payload = {
            "line_items": [
                {
                    "product_id": stockpilot_product.stockpilot_id,
                    "quantity": 1,
                }
            ]
        }
        warehouse = self.env["sale.order"]._get_warehouse(
            self.configuration,
            self.country_nl.code,
            is_external=True,
            order=order_payload,
        )
        self.assertEqual(warehouse, self.fba_warehouse_2)

    def test_non_external_orders_are_unaffected_by_fba_mapping(self):
        self.env["country.warehouse"].create(
            {
                "stockpilot_configuration_id": self.configuration.id,
                "country_id": self.country_nl.id,
                "warehouse_id": self.fba_warehouse_1.id,
            }
        )
        self.env["country.fba.warehouse"].create(
            {
                "stockpilot_configuration_id": self.configuration.id,
                "country_id": self.country_nl.id,
                "warehouse_id": self.fba_warehouse_2.id,
            }
        )
        warehouse = self.env["sale.order"]._get_warehouse(
            self.configuration, self.country_nl.code, is_external=False
        )
        self.assertEqual(warehouse, self.fba_warehouse_1)
