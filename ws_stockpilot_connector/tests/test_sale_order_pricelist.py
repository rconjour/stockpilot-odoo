# Copyright (C) 2025 WeSolved BV <https://wesolved.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class TestSaleOrderPricelist(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_currency = cls.env.company.currency_id
        cls.other_currency = cls.env.ref("base.USD")
        if cls.other_currency == cls.company_currency:
            cls.other_currency = cls.env.ref("base.EUR")
        cls.other_currency.active = True

        cls.matching_pricelist = cls.env["product.pricelist"].create(
            {
                "name": "Matching Pricelist",
                "currency_id": cls.company_currency.id,
            }
        )
        cls.mismatched_pricelist = cls.env["product.pricelist"].create(
            {
                "name": "Mismatched Pricelist",
                "currency_id": cls.other_currency.id,
            }
        )
        cls.warehouse = cls.env["stock.warehouse"].search([], limit=1)

    def _configuration(self, pricelist=None):
        return self.env["stockpilot.configuration"].create(
            {
                "name": "Test Configuration",
                "default_warehouse_id": self.warehouse.id,
                "pricelist_id": pricelist.id if pricelist else False,
            }
        )

    def _order_payload(self, order_id, currency_code):
        return {
            "id": order_id,
            "channel_order_number": f"SO-{order_id}",
            "created_at": "2024-01-01T10:00:00",
            "order_details": {
                "shipment_firstname": "John",
                "shipment_lastname": "Doe",
                "shipment_street": "Main St",
                "shipment_housenumber": "1",
                "shipment_suffix": "",
                "shipment_zipcode": "1000",
                "shipment_city": "Brussels",
                "shipment_country": "BE",
                "customer_email": "john.doe@example.com",
                "customer_phone": "123456",
                "billing_firstname": "John",
                "billing_lastname": "Doe",
                "billing_street": "Main St",
                "billing_housenumber": "1",
                "billing_suffix": "",
                "billing_zipcode": "1000",
                "billing_city": "Brussels",
                "billing_country": "BE",
                "currency_code": currency_code,
                "line_items": [],
            },
        }

    # _get_pricelist unit tests

    def test_get_pricelist_matching_currency_is_used(self):
        configuration = self._configuration(self.matching_pricelist)
        pricelist = self.env["sale.order"]._get_pricelist(
            configuration, self.company_currency.name
        )
        self.assertEqual(pricelist, self.matching_pricelist)

    def test_get_pricelist_currency_mismatch_is_skipped(self):
        configuration = self._configuration(self.mismatched_pricelist)
        pricelist = self.env["sale.order"]._get_pricelist(
            configuration, self.company_currency.name
        )
        self.assertFalse(pricelist)

    def test_get_pricelist_no_configuration_returns_empty(self):
        configuration = self._configuration(None)
        pricelist = self.env["sale.order"]._get_pricelist(
            configuration, self.company_currency.name
        )
        self.assertFalse(pricelist)

    # _import_stockpilot_order integration tests

    def test_import_order_applies_configured_pricelist(self):
        configuration = self._configuration(self.matching_pricelist)
        payload = self._order_payload(555001, self.company_currency.name)

        self.env["sale.order"]._import_stockpilot_order(payload, configuration)

        order = self.env["sale.order"].search([("stockpilot_id", "=", 555001)])
        self.assertEqual(order.pricelist_id, self.matching_pricelist)
        self.assertFalse(order.stockpilot_error)

    def test_import_order_skips_mismatched_pricelist_and_flags_order(self):
        configuration = self._configuration(self.mismatched_pricelist)
        payload = self._order_payload(555002, self.company_currency.name)

        self.env["sale.order"]._import_stockpilot_order(payload, configuration)

        order = self.env["sale.order"].search([("stockpilot_id", "=", 555002)])
        self.assertNotEqual(order.pricelist_id, self.mismatched_pricelist)
        self.assertTrue(order.stockpilot_error)

    def test_import_order_without_configured_pricelist_leaves_default(self):
        configuration = self._configuration(None)
        payload = self._order_payload(555003, self.company_currency.name)

        self.env["sale.order"]._import_stockpilot_order(payload, configuration)

        order = self.env["sale.order"].search([("stockpilot_id", "=", 555003)])
        self.assertFalse(order.stockpilot_error)
