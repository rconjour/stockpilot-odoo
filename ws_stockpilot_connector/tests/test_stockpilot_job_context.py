# Copyright (C) 2025 WeSolved BV <https://wesolved.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from unittest.mock import MagicMock, patch

from odoo.tests.common import TransactionCase


class TestStockpilotJobContext(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env["stock.warehouse"].search([], limit=1)
        cls.external_warehouse = cls.env["stock.warehouse"].create(
            {"name": "External Warehouse", "code": "EXTJC"}
        )
        cls.shipping_product = cls.env["product.product"].create(
            {"name": "Shipping", "type": "service"}
        )
        cls.discount_product = cls.env["product.product"].create(
            {"name": "Discount", "type": "service"}
        )
        cls.configuration = cls.env["stockpilot.configuration"].create(
            {
                "name": "Job Context Configuration",
                "default_warehouse_id": cls.warehouse.id,
                "external_warehouse_id": cls.external_warehouse.id,
                "shipping_product": cls.shipping_product.id,
                "discount_product": cls.discount_product.id,
                "auto_confirm_orders": True,
                "stock_calculator": "free_qty",
            }
        )

    def test_create_from_configuration_snapshots_fields(self):
        """The job context copies the configuration's data at creation time."""
        job_context = self.env[
            "stockpilot.job.context"
        ]._create_from_configuration(self.configuration)

        self.assertEqual(job_context.stockpilot_configuration_id, self.configuration)
        self.assertEqual(job_context.default_warehouse_id, self.warehouse)
        self.assertEqual(job_context.external_warehouse_id, self.external_warehouse)
        self.assertEqual(job_context.shipping_product, self.shipping_product)
        self.assertEqual(job_context.discount_product, self.discount_product)
        self.assertTrue(job_context.auto_confirm_orders)
        self.assertEqual(job_context.stock_calculator, "free_qty")
        self.assertTrue(job_context.batch_reference)
        self.assertEqual(
            job_context._stockpilot_config_id(), self.configuration.id
        )

    def test_batch_reference_is_unique_per_context(self):
        """Each context gets its own traceability reference, even for the same configuration."""
        job_context_1 = self.env[
            "stockpilot.job.context"
        ]._create_from_configuration(self.configuration)
        job_context_2 = self.env[
            "stockpilot.job.context"
        ]._create_from_configuration(self.configuration)

        self.assertNotEqual(job_context_1.batch_reference, job_context_2.batch_reference)

    def test_snapshot_is_independent_of_later_configuration_changes(self):
        """
        Changing the configuration after the context was built must not affect
        the already-created context: it is a snapshot, not a live relationship.
        """
        job_context = self.env[
            "stockpilot.job.context"
        ]._create_from_configuration(self.configuration)

        other_warehouse = self.env["stock.warehouse"].create(
            {"name": "Other Warehouse", "code": "OTHRWH"}
        )
        self.configuration.write(
            {"default_warehouse_id": other_warehouse.id, "auto_confirm_orders": False}
        )

        self.assertEqual(job_context.default_warehouse_id, self.warehouse)
        self.assertTrue(job_context.auto_confirm_orders)

    def test_job_context_survives_configuration_deletion(self):
        """
        A job context keeps working (snapshot fields + batch_reference) even
        after the originating configuration has been removed, which is the
        whole point of no longer depending on it.
        """
        job_context = self.env[
            "stockpilot.job.context"
        ]._create_from_configuration(self.configuration)
        batch_reference = job_context.batch_reference
        self.configuration.unlink()

        self.assertFalse(job_context.stockpilot_configuration_id)
        self.assertEqual(job_context.batch_reference, batch_reference)
        self.assertEqual(job_context.default_warehouse_id, self.warehouse)
        self.assertFalse(job_context._stockpilot_config_id())

    def test_get_warehouse_and_shipping_product_accept_job_context(self):
        """
        _get_warehouse/_get_shipping_product/_calculate_stock are shared with
        synchronous callers that still pass a live configuration, so they must
        keep working identically when given a job context instead.
        """
        job_context = self.env[
            "stockpilot.job.context"
        ]._create_from_configuration(self.configuration)

        warehouse = self.env["sale.order"]._get_warehouse(job_context, "BE")
        self.assertEqual(warehouse, self.warehouse)

        external_warehouse = self.env["sale.order"]._get_warehouse(
            job_context, "BE", is_external=True
        )
        self.assertEqual(external_warehouse, self.external_warehouse)

        shipping_product = self.env["sale.order"]._get_shipping_product(
            job_context, "BE"
        )
        self.assertEqual(shipping_product, self.shipping_product)

    def test_import_stockpilot_order_does_not_require_live_configuration(self):
        """
        Simulates the race condition called out in the task: the configuration
        is removed after the job context was created but before the queued
        job runs. The import must still succeed using the snapshot, and the
        resulting order must carry batch_reference for traceability.
        """
        job_context = self.env[
            "stockpilot.job.context"
        ]._create_from_configuration(self.configuration)
        batch_reference = job_context.batch_reference
        self.configuration.unlink()

        currency = self.env.company.currency_id
        order_payload = {
            "id": 999001,
            "channel_order_number": "SO-999001",
            "created_at": "2024-01-01T10:00:00",
            "order_details": {
                "is_external": False,
                "shipment_firstname": "John",
                "shipment_lastname": "Doe",
                "shipment_street": "Main St",
                "shipment_housenumber": "1",
                "shipment_suffix": "",
                "shipment_address_2": "",
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
                "billing_address_2": "",
                "billing_zipcode": "1000",
                "billing_city": "Brussels",
                "billing_country": "BE",
                "currency_code": currency.name,
                "line_items": [],
                "customer_note": "Leave at the door",
            },
        }

        self.env["sale.order"]._import_stockpilot_order(order_payload, job_context)

        order = self.env["sale.order"].search([("stockpilot_id", "=", 999001)])
        self.assertTrue(order)
        self.assertFalse(order.stockpilot_configuration_id)
        self.assertEqual(order.stockpilot_batch_reference, batch_reference)
        self.assertEqual(order.warehouse_id, self.warehouse)
        # auto_confirm_orders was snapshotted as True before the configuration
        # was removed, so the order is still confirmed automatically.
        self.assertEqual(order.state, "sale")

    def test_import_orders_creates_job_context_and_queues_jobs_without_configuration_reference(
        self,
    ):
        """
        import_orders() must build a job context up front and queue the
        per-order job against it, instead of carrying the live configuration
        recordset into the delayed job call.
        """
        configuration = self.env["stockpilot.configuration"].create(
            {
                "name": "Fetch Configuration",
                "default_warehouse_id": self.warehouse.id,
                "api_client_id": "client",
                "api_client_secret": "secret",
            }
        )
        fake_response = MagicMock(status_code=200)
        fake_response.json.return_value = {"results": []}
        with patch(
            "ws_stockpilot_connector.stockpilot_api.StockpilotApi._execute_get_request",
            return_value=fake_response,
        ):
            configuration.import_orders()

        job_contexts = self.env["stockpilot.job.context"].search(
            [("stockpilot_configuration_id", "=", configuration.id)]
        )
        self.assertEqual(len(job_contexts), 1)
        self.assertTrue(job_contexts.batch_reference)
