# Copyright (C) 2025 WeSolved BV <https://wesolved.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class TestJobContextWarehouse(TransactionCase):
    """
    Regression tests making sure the country/FBA warehouse routing added by
    this module keeps working when the queued job carries a
    stockpilot.job.context snapshot instead of a live stockpilot.configuration
    recordset, including after the originating configuration is gone.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.country_nl = cls.env["res.country"].search([("code", "=", "NL")], limit=1)
        cls.default_warehouse = cls.env["stock.warehouse"].search([], limit=1)
        cls.country_warehouse = cls.env["stock.warehouse"].create(
            {"name": "NL Warehouse", "code": "NLWH"}
        )
        cls.external_warehouse = cls.env["stock.warehouse"].create(
            {"name": "External Warehouse", "code": "EXTWH2"}
        )
        cls.configuration = cls.env["stockpilot.configuration"].create(
            {
                "name": "Job Context Warehouse Configuration",
                "default_warehouse_id": cls.default_warehouse.id,
                "external_warehouse_id": cls.external_warehouse.id,
            }
        )
        cls.env["country.warehouse"].create(
            {
                "stockpilot_configuration_id": cls.configuration.id,
                "country_id": cls.country_nl.id,
                "warehouse_id": cls.country_warehouse.id,
            }
        )

    def test_country_mapping_is_resolved_from_job_context(self):
        """The country.warehouse mapping lookup works from a job context snapshot."""
        job_context = self.env[
            "stockpilot.job.context"
        ]._create_from_configuration(self.configuration)

        warehouse = self.env["sale.order"]._get_warehouse(
            job_context, self.country_nl.code, is_external=False
        )
        self.assertEqual(warehouse, self.country_warehouse)

    def test_country_mapping_still_resolved_after_configuration_deleted(self):
        """
        The job context is built before the configuration is removed, so the
        queued job can still run correctly afterwards, with a graceful
        fallback to the context's own default warehouse since the
        configuration-keyed mapping can no longer be looked up by id.
        """
        job_context = self.env[
            "stockpilot.job.context"
        ]._create_from_configuration(self.configuration)
        self.configuration.unlink()

        warehouse = self.env["sale.order"]._get_warehouse(
            job_context, self.country_nl.code, is_external=False
        )
        self.assertEqual(warehouse, self.default_warehouse)

        external_warehouse = self.env["sale.order"]._get_warehouse(
            job_context, self.country_nl.code, is_external=True
        )
        self.assertEqual(external_warehouse, self.external_warehouse)
