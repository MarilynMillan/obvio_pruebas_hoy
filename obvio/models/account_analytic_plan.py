from odoo import api, fields, models


class AccountAnalyticPlan(models.Model):
    _inherit = "account.analytic.plan"

    show_on_all_companies = fields.Boolean(
        string="Visible in all companies",
        help="If enabled, this root analytic plan remains visible on projects for every company.",
    )

    def _clear_project_analytic_templates_cache(self):
        self.env.registry.clear_cache("templates")

    @api.model_create_multi
    def create(self, vals_list):
        plans = super().create(vals_list)
        plans._clear_project_analytic_templates_cache()
        return plans

    def write(self, vals):
        res = super().write(vals)
        self._clear_project_analytic_templates_cache()
        return res

    def unlink(self):
        res = super().unlink()
        self.env.registry.clear_cache("templates")
        return res
