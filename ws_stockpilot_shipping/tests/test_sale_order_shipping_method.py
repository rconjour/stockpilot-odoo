# Copyright (C) 2026 WeSolved BV <https://wesolved.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class TestSaleOrderShippingMethod(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.configuration = cls.env["stockpilot.configuration"].create(
            {"name": "Test Configuration"}
        )
        cls.partner = cls.env["res.partner"].create({"name": "Test Customer"})
        carrier_product = cls.env["product.product"].create(
            {"name": "Express Delivery", "type": "service"}
        )
        cls.carrier = cls.env["delivery.carrier"].create(
            {"name": "Express", "product_id": carrier_product.id}
        )
        cls.env["stockpilot.shipping.method"].create(
            {
                "stockpilot_configuration_id": cls.configuration.id,
                "stockpilot_name": "Express Shipping",
                "carrier_id": cls.carrier.id,
            }
        )

    def setUp(self):
        super().setUp()
        self.order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "stockpilot_configuration_id": self.configuration.id,
            }
        )

    def _order_info(self, method_title):
        return {"metadata": {"shippingLines": [{"method_title": method_title}]}}

    def test_mapped_shipping_method_applies_carrier(self):
        """A recognized Stockpilot shipping method sets the order's delivery carrier."""
        order = self.env["sale.order"].override_order(
            self.order, self._order_info("Express Shipping")
        )
        self.assertEqual(order.carrier_id, self.carrier)

    def test_unmapped_shipping_method_leaves_carrier_unset(self):
        """An unrecognized shipping method does not set a delivery carrier."""
        order = self.env["sale.order"].override_order(
            self.order, self._order_info("Unknown Method")
        )
        self.assertFalse(order.carrier_id)

    def test_missing_metadata_does_not_crash(self):
        """A payload without a 'metadata' key is handled gracefully (regression)."""
        order = self.env["sale.order"].override_order(self.order, {"order_number": "1"})
        self.assertFalse(order.carrier_id)

    def test_missing_shipping_lines_leaves_carrier_unset(self):
        """Orders without shipping line metadata still import without errors."""
        order = self.env["sale.order"].override_order(
            self.order, {"metadata": {}}
        )
        self.assertFalse(order.carrier_id)
