# Copyright 2021 ACSONE SA/NV
# Copyright 2023 Quartile Limited
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class MrpProduction(models.Model):
    _name = "mrp.production"
    _inherit = ["mrp.production", "analytic.mixin"]

    analytic_distribution = fields.Json(
        inverse="_inverse_analytic_distribution",
        compute="_compute_analytic_distribution",
        store=True,
        readonly=False,
        copy=True,
    )
    analytic_account_ids = fields.Many2many(
        "account.analytic.account",
        compute="_compute_analytic_account_ids",
        store=True,
    )

    @api.depends("product_id")
    def _compute_analytic_distribution(self):
        """Compute analytic distribution from distribution model."""
        for record in self:
            record.analytic_distribution = self.env[
                "account.analytic.distribution.model"
            ]._get_distribution(
                {
                    "product_id": record.product_id.id,
                    "product_categ_id": record.product_id.categ_id.id,
                    "company_id": record.company_id.id,
                }
            )

    @api.depends("analytic_distribution")
    def _compute_analytic_account_ids(self):
        """Extract analytic account IDs from distribution for easy access."""
        for record in self:
            record.analytic_account_ids = (
                bool(record.analytic_distribution)
                and self.env["account.analytic.account"]
                .browse(
                    list(
                        {
                            int(account_id)
                            for ids in record.analytic_distribution
                            for account_id in ids.split(",")
                        }
                    )
                )
                .exists()
            )

    def _inverse_analytic_distribution(self):
        """If analytic distribution is set on production, write it on all component
        moves and finished product moves.
        """
        for production in self:
            # Propagate to raw material consumption moves
            production.move_raw_ids.write(
                {"analytic_distribution": production.analytic_distribution}
            )
            # Propagate to finished product moves
            production.move_finished_ids.write(
                {"analytic_distribution": production.analytic_distribution}
            )

    @api.constrains("analytic_distribution")
    def _check_analytic(self):
        """Validate analytic distribution."""
        for record in self:
            params = {
                "business_domain": "manufacturing_order",
                "company_id": record.company_id.id,
            }
            if record.product_id:
                params["product"] = record.product_id.id
            record.with_context({"validate_analytic": True})._validate_distribution(
                **params
            )

    def write(self, vals):
        """Update analytic lines when distribution changes."""
        res = super().write(vals)
        if "analytic_distribution" in vals:
            for production in self:
                if production.state != "draft":
                    # Update raw material moves with new distribution
                    production.move_raw_ids.write(
                        {"analytic_distribution": production.analytic_distribution}
                    )
                    # Update finished product moves with new distribution
                    production.move_finished_ids.write(
                        {"analytic_distribution": production.analytic_distribution}
                    )
        return res

    def action_view_analytic_accounts(self):
        """Action to view related analytic accounts."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.analytic.account",
            "domain": [("id", "in", self.analytic_account_ids.ids)],
            "name": "Analytic Accounts",
            "view_mode": "tree,form",
        }
