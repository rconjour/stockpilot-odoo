from odoo import models

import logging

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _get_warehouse(
        self, stockpilot_configuration_id, country_code, is_external=False, order=None
    ):
        """
        Get the warehouse based on the country code using the CountryWarehouse mapping.
        If no specific mapping exists, return the default warehouse from the configuration.

        External orders are routed through the country's configured FBA
        warehouses instead of the plain country mapping (see `_get_fba_warehouse`).
        """
        if is_external:
            return self._get_fba_warehouse(
                stockpilot_configuration_id, country_code, order=order
            )

        _logger.info(stockpilot_configuration_id)
        _logger.info(country_code)
        warehouse_id = (
            self.env["country.warehouse"]
            .search(
                [
                    ("stockpilot_configuration_id", "=", stockpilot_configuration_id.id),
                    ("country_id.code", "=", country_code),
                ],
                limit=1,
            )
            .warehouse_id
        )
        _logger.info(warehouse_id)
        if not warehouse_id:
            warehouse_id = stockpilot_configuration_id.default_warehouse_id

        _logger.info(warehouse_id)
        return warehouse_id

    def _get_fba_warehouse(self, stockpilot_configuration_id, country_code, order=None):
        """
        Resolve the FBA warehouse an external order's destination country should
        be booked on.

        A country can have several FBA warehouses configured (CountryFbaWarehouse
        mapping). When more than one is available, the warehouse holding the
        most stock for the order's products is preferred (using the
        configuration's stock calculator); ties and missing stock data fall
        back to the mapping sequence. When no FBA warehouse is configured for
        the country, the configuration's single external warehouse is used.

        Args:
            stockpilot_configuration_id (recordset): The configuration used for the import.
            country_code (str): Shipping country code of the order.
            order (dict): Stockpilot order payload (order_details section), used
                to look up the ordered products for stock-based selection.

        Returns:
            recordset: The stock.warehouse to use.
        """
        fba_warehouses = self.env["country.fba.warehouse"].search(
            [
                ("stockpilot_configuration_id", "=", stockpilot_configuration_id.id),
                ("country_id.code", "=", country_code),
            ]
        )
        if not fba_warehouses:
            return super()._get_warehouse(
                stockpilot_configuration_id,
                country_code,
                is_external=True,
                order=order,
            )
        if len(fba_warehouses) == 1:
            return fba_warehouses.warehouse_id

        products = self._get_stockpilot_order_products(order)
        if not products:
            return fba_warehouses[0].warehouse_id

        best_warehouse = fba_warehouses[0].warehouse_id
        best_qty = None
        for fba_warehouse in fba_warehouses:
            warehouse = fba_warehouse.warehouse_id
            qty = sum(
                products.with_context(warehouse=warehouse.id).mapped(
                    lambda product: product._calculate_stock(stockpilot_configuration_id)
                )
            )
            if best_qty is None or qty > best_qty:
                best_qty = qty
                best_warehouse = warehouse
        return best_warehouse

    def _get_stockpilot_order_products(self, order):
        """
        Resolve the product.product recordset referenced by a Stockpilot
        order payload's line items.

        Args:
            order (dict): Stockpilot order payload (order_details section).

        Returns:
            recordset: The product.product records ordered by the customer.
        """
        if not order:
            return self.env["product.product"]
        stockpilot_ids = [
            line.get("product_id")
            for line in order.get("line_items") or []
            if line.get("product_id")
        ]
        if not stockpilot_ids:
            return self.env["product.product"]
        return (
            self.env["stockpilot.product.product"]
            .search([("stockpilot_id", "in", stockpilot_ids)])
            .mapped("product_product_id")
        )
