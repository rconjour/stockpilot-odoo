# Copyright (C) 2025 WeSolved BV <https://wesolved.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class TestSaleOrderFiscalPositionTax(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env["stock.warehouse"].search([], limit=1)
        cls.tax_high = cls.env["account.tax"].create(
            {
                "name": "21% Sale",
                "amount": 21.0,
                "amount_type": "percent",
                "type_tax_use": "sale",
            }
        )
        cls.tax_exempt = cls.env["account.tax"].create(
            {
                "name": "0% Sale",
                "amount": 0.0,
                "amount_type": "percent",
                "type_tax_use": "sale",
            }
        )
        cls.fiscal_position = cls.env["account.fiscal.position"].create(
            {
                "name": "Export - Exempt",
                "tax_ids": [
                    (
                        0,
                        0,
                        {
                            "tax_src_id": cls.tax_high.id,
                            "tax_dest_id": cls.tax_exempt.id,
                        },
                    )
                ],
            }
        )
        cls.shipping_product = cls.env["product.product"].create(
            {
                "name": "Shipping",
                "type": "service",
                "taxes_id": [(6, 0, cls.tax_high.ids)],
            }
        )
        cls.discount_product = cls.env["product.product"].create(
            {
                "name": "Discount",
                "type": "service",
                "taxes_id": [(6, 0, cls.tax_high.ids)],
            }
        )
        cls.sale_product = cls.env["product.product"].create(
            {
                "name": "Widget",
                "type": "consu",
                "taxes_id": [(6, 0, cls.tax_high.ids)],
            }
        )
        cls.configuration = cls.env["stockpilot.configuration"].create(
            {
                "name": "Fiscal Position Test Configuration",
                "default_warehouse_id": cls.warehouse.id,
                "shipping_product": cls.shipping_product.id,
                "discount_product": cls.discount_product.id,
            }
        )
        cls.stockpilot_product = cls.env["stockpilot.product.product"].create(
            {
                "stockpilot_configuration_id": cls.configuration.id,
                "product_product_id": cls.sale_product.id,
                "stockpilot_id": "SP-1",
            }
        )
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "John Doe",
                "email": "john.doe@example.com",
                "property_account_position_id": cls.fiscal_position.id,
            }
        )

    def _payload(self, order_id, **order_details_overrides):
        order_details = {
            "shipment_firstname": "John",
            "shipment_lastname": "Doe",
            "shipment_street": "Main St",
            "shipment_housenumber": "1",
            "shipment_suffix": "",
            "shipment_zipcode": "1000",
            "shipment_city": "Brussels",
            "shipment_country": "BE",
            "customer_email": "john.doe@example.com",
            "customer_phone": "",
            "billing_firstname": "John",
            "billing_lastname": "Doe",
            "billing_street": "Main St",
            "billing_housenumber": "1",
            "billing_suffix": "",
            "billing_zipcode": "1000",
            "billing_city": "Brussels",
            "billing_country": "BE",
            "currency_code": self.env.company.currency_id.name,
            "line_items": [],
            "vat_rate": "21",
            "customer_note": "",
        }
        order_details.update(order_details_overrides)
        return {
            "id": order_id,
            "channel_order_number": f"SO-{order_id}",
            "created_at": "2024-01-01T10:00:00",
            "order_details": order_details,
        }

    def test_shipping_line_tax_follows_fiscal_position(self):
        """The shipping line's tax must be mapped through the order's fiscal position."""
        payload = self._payload(600001, shipping_total="12.10")
        self.env["sale.order"]._import_stockpilot_order(payload, self.configuration)

        order = self.env["sale.order"].search([("stockpilot_id", "=", 600001)])
        shipping_line = order.order_line.filtered(lambda l: l.name == "Shipping")
        self.assertTrue(shipping_line)
        self.assertEqual(shipping_line.tax_id, self.tax_exempt)
        self.assertNotEqual(shipping_line.tax_id, self.shipping_product.taxes_id)

    def test_discount_line_tax_follows_fiscal_position(self):
        """
        The order-level discount line's tax must be mapped through the
        fiscal position instead of a raw rate-based account.tax lookup.
        """
        payload = self._payload(600002, discount="5.00")
        self.env["sale.order"]._import_stockpilot_order(payload, self.configuration)

        order = self.env["sale.order"].search([("stockpilot_id", "=", 600002)])
        discount_line = order.order_line.filtered(lambda l: l.name == "Discount")
        self.assertTrue(discount_line)
        self.assertEqual(discount_line.tax_id, self.tax_exempt)
        self.assertNotEqual(discount_line.tax_id, self.discount_product.taxes_id)

    def test_full_order_import_applies_fiscal_position_to_shipping_and_discount(self):
        """Product + shipping + order-level discount: shipping and discount both get the mapped tax."""
        payload = self._payload(
            600003,
            shipping_total="12.10",
            discount="5.00",
            line_items=[
                {
                    "id": 1,
                    "product_id": "SP-1",
                    "quantity": 2,
                    "retail_price": "121.00",
                    "vat_rate": "21",
                    "sales_channel_title": "Widget",
                }
            ],
        )
        self.env["sale.order"]._import_stockpilot_order(payload, self.configuration)

        order = self.env["sale.order"].search([("stockpilot_id", "=", 600003)])
        self.assertEqual(len(order.order_line), 3)
        shipping_line = order.order_line.filtered(lambda l: l.name == "Shipping")
        discount_line = order.order_line.filtered(lambda l: l.name == "Discount")
        self.assertEqual(shipping_line.tax_id, self.tax_exempt)
        self.assertEqual(discount_line.tax_id, self.tax_exempt)

    def test_product_only_order_regression(self):
        """Orders without shipping/discount must keep importing unaffected."""
        payload = self._payload(
            600004,
            line_items=[
                {
                    "id": 1,
                    "product_id": "SP-1",
                    "quantity": 1,
                    "retail_price": "121.00",
                    "vat_rate": "21",
                    "sales_channel_title": "Widget",
                }
            ],
        )
        self.env["sale.order"]._import_stockpilot_order(payload, self.configuration)

        order = self.env["sale.order"].search([("stockpilot_id", "=", 600004)])
        self.assertEqual(len(order.order_line), 1)
        self.assertFalse(
            order.order_line.filtered(lambda l: l.name in ("Shipping", "Discount"))
        )
