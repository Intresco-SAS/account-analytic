# Copyright 2025 Intresco SAS
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models


class StockMove(models.Model):
    _inherit = "stock.move"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Skip if analytic_distribution is already set
            if vals.get("analytic_distribution"):
                continue
            
            production = None
            # Check for raw material moves (components)
            if vals.get("raw_material_production_id"):
                production = self.env["mrp.production"].browse(
                    vals["raw_material_production_id"]
                )
            # Check for finished product moves
            elif vals.get("production_id"):
                production = self.env["mrp.production"].browse(vals["production_id"])
            
            # Propagate analytic distribution from production
            if production and production.analytic_distribution:
                vals["analytic_distribution"] = production.analytic_distribution
        
        return super().create(vals_list)
