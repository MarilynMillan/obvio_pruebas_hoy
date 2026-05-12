from odoo import api, fields, models, _

class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    margin_percent = fields.Float(string="Margin %", compute="_compute_margin_percent", digits=(16, 2))


    def _compute_margin_percent(self):
        for rec in self:
            if rec.credit:
                rec.margin_percent = ((rec.credit - rec.debit) / rec.credit) * 100
            else: 
                rec.margin_percent = 0.0

    def _clear_project_analytic_templates_cache(self):
        self.env.registry.clear_cache("templates")

    @api.model_create_multi
    def create(self, vals_list):
        accounts = super().create(vals_list)
        accounts._clear_project_analytic_templates_cache()
        return accounts

    def write(self, vals):
        res = super().write(vals)
        self._clear_project_analytic_templates_cache()
        return res

    def unlink(self):
        res = super().unlink()
        self.env.registry.clear_cache("templates")
        return res
