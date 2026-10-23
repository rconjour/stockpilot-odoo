# Copyright (C) 2025 WeSolved BV <https://wesolved.com>
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
        cls.country = cls.env.ref("base.nl")
        cls.env["stockpilot.shipping.method"].create(
            {
                "stockpilot_configuration_id": cls.configuration.id,
                "country_id": cls.country.id,
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

    def _order_info(self, country_code):
        return {"order_details": {"shipment_country": country_code}}

    def test_mapped_country_applies_carrier(self):
        """A recognized shipment country sets the order's delivery carrier."""
        order = self.env["sale.order"].override_order(
            self.order, self._order_info(self.country.code)
        )
        self.assertEqual(order.carrier_id, self.carrier)

    def test_unmapped_country_leaves_carrier_unset(self):
        """An unrecognized shipment country does not set a delivery carrier."""
        order = self.env["sale.order"].override_order(
            self.order, self._order_info("XX")
        )
        self.assertFalse(order.carrier_id)

    def test_missing_shipping_metadata_leaves_carrier_unset(self):
        """Orders without shipment country info still import without errors."""
        order = self.env["sale.order"].override_order(self.order, {})
        self.assertFalse(order.carrier_id)
