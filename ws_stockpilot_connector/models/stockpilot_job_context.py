# Copyright (C) 2025 WeSolved BV <https://wesolved.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import uuid

from odoo import _, api, fields, models


class StockpilotJobContext(models.Model):
    """
    Standalone snapshot of the configuration data a queued job needs to run.

    Queued jobs (e.g. sale.order._import_stockpilot_order) used to carry a
    live reference to the stockpilot.configuration record that triggered
    them, so every job depended on that record still existing, and on its
    fields staying unchanged, until the job eventually ran. A
    stockpilot.job.context record is created once, upfront, with a copy of
    the data the job actually needs, so the job no longer depends on the
    configuration record ("batch") itself.
    """

    _name = "stockpilot.job.context"
    _description = "Stockpilot Job Context"

    name = fields.Char(required=True)
    batch_reference = fields.Char(
        string="Batch Reference",
        required=True,
        index=True,
        copy=False,
        help="Stable identifier kept for traceability, independent of the "
        "configuration foreign key below which may become empty if the "
        "configuration is later deleted.",
    )
    stockpilot_configuration_id = fields.Many2one(
        "stockpilot.configuration",
        string="Source Configuration",
        ondelete="set null",
        help="Optional link back to the configuration this context was "
        "built from. Kept only for traceability, never required to "
        "execute the job(s) carrying this context.",
    )

    # Snapshotted configuration fields. These are plain copies taken at
    # creation time, not related fields, so they stay stable even if the
    # source configuration is later changed, archived or deleted.
    stock_calculator = fields.Selection(
        [
            ("qty_available", "QTY Available"),
            ("virtual_available", "Virtual available"),
            ("free_qty", "Free quantity"),
            ("incoming_qty", "Incoming quantity"),
            ("outgoing_qty", "Outgoing quantity"),
        ],
        default="qty_available",
    )
    crm_team_id = fields.Many2one("crm.team")
    auto_confirm_orders = fields.Boolean()
    pricelist_id = fields.Many2one("product.pricelist")
    default_warehouse_id = fields.Many2one("stock.warehouse")
    external_warehouse_id = fields.Many2one("stock.warehouse")
    default_tax_id = fields.Many2one("account.tax")
    shipping_product = fields.Many2one("product.product")
    discount_product = fields.Many2one("product.product")

    def _stockpilot_config_id(self):
        """
        Id of the configuration this context was built from, for lookups
        against models keyed on stockpilot_configuration_id (e.g.
        country.warehouse). Returns False when the source configuration no
        longer exists, callers are expected to fall back gracefully.
        """
        self.ensure_one()
        return self.stockpilot_configuration_id.id

    def _get_connection(self):
        """
        Fall back to the source configuration's API connection, for the rare
        operations that genuinely need live credentials. Returns False when
        the source configuration is no longer available.
        """
        self.ensure_one()
        if not self.stockpilot_configuration_id:
            return False
        return self.stockpilot_configuration_id._get_connection()

    @api.model
    def _create_from_configuration(self, configuration):
        """
        Snapshot a stockpilot.configuration into a standalone job context
        record, so queued jobs stop depending on the configuration record.

        Args:
            configuration (recordset): The stockpilot.configuration to
                snapshot.

        Returns:
            recordset: The created stockpilot.job.context record.
        """
        configuration.ensure_one()
        return self.create(
            {
                "name": _("Job context for %s") % configuration.name,
                "batch_reference": "cfg-%s-%s"
                % (configuration.id, uuid.uuid4().hex[:12]),
                "stockpilot_configuration_id": configuration.id,
                "stock_calculator": configuration.stock_calculator,
                "crm_team_id": configuration.crm_team_id.id,
                "auto_confirm_orders": configuration.auto_confirm_orders,
                "pricelist_id": configuration.pricelist_id.id,
                "default_warehouse_id": configuration.default_warehouse_id.id,
                "external_warehouse_id": configuration.external_warehouse_id.id,
                "default_tax_id": configuration.default_tax_id.id,
                "shipping_product": configuration.shipping_product.id,
                "discount_product": configuration.discount_product.id,
            }
        )
