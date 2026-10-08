# Copyright (C) 2025 WeSolved BV <https://wesolved.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class TestSaleOrderExternalWarehouse(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.default_warehouse = cls.env["stock.warehouse"].search([], limit=1)
        cls.external_warehouse = cls.env["stock.warehouse"].create(
            {"name": "External Warehouse", "code": "EXTWH"}
        )
        cls.configuration = cls.env["stockpilot.configuration"].create(
            {
                "name": "Test Configuration",
                "default_warehouse_id": cls.default_warehouse.id,
                "external_warehouse_id": cls.external_warehouse.id,
            }
        )

    def test_is_external_stockpilot_order_top_level_flag(self):
        self.assertTrue(
            self.env["sale.order"]._is_external_stockpilot_order({"is_external": True})
        )

    def test_is_external_stockpilot_order_nested_flag(self):
        self.assertTrue(
            self.env["sale.order"]._is_external_stockpilot_order(
                {"order_details": {"is_external": True}}
            )
        )

    def test_is_external_stockpilot_order_false_by_default(self):
        self.assertFalse(
            self.env["sale.order"]._is_external_stockpilot_order({"order_number": "1"})
        )
        self.assertFalse(self.env["sale.order"]._is_external_stockpilot_order(None))

    def test_get_warehouse_external_uses_external_warehouse(self):
        warehouse = self.env["sale.order"]._get_warehouse(
            self.configuration, "NL", is_external=True
        )
        self.assertEqual(warehouse, self.external_warehouse)

    def test_get_warehouse_non_external_uses_default_warehouse(self):
        warehouse = self.env["sale.order"]._get_warehouse(
            self.configuration, "NL", is_external=False
        )
        self.assertEqual(warehouse, self.default_warehouse)
