# Copyright 2025 Intresco SAS
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class StockRule(models.Model):
    _inherit = "stock.rule"

    def _prepare_mo_vals(self, product_id, product_qty, product_uom, location_dest_id, name, origin, company_id, values, bom):
        """
        Override to include project_id and analytic_distribution in child MOs
        when components with BoM are created from a parent production order.
        """
        res = super()._prepare_mo_vals(product_id, product_qty, product_uom, location_dest_id, name, origin,company_id, values, bom)
        
        # Add analytic_distribution if available in procurement values
        if values.get("analytic_distribution"):
            res["analytic_distribution"] = values["analytic_distribution"]
        if not res.get("project_id") and not values.get("project_id"):
            mo_origin = self.env["mrp.production"].search([("name", "=", res.get("origin"))], limit=1)
            if mo_origin:
                res["project_id"] = mo_origin.project_id.id
        return res
