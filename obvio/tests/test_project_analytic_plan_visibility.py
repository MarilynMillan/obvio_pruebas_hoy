from odoo.tests import TransactionCase


class TestProjectAnalyticPlanVisibility(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env["res.company"].create({"name": "Visibility Company A"})
        cls.company_b = cls.env["res.company"].create({
            "name": "Visibility Company B",
            "parent_id": cls.company_a.id,
        })

        cls.company_a_plan = cls.env["account.analytic.plan"].create({"name": "Company A Plan"})
        cls.company_b_plan = cls.env["account.analytic.plan"].create({"name": "Company B Plan"})
        cls.shared_plan = cls.env["account.analytic.plan"].create({
            "name": "Shared Plan",
            "show_on_all_companies": True,
        })
        cls.shared_account_plan = cls.env["account.analytic.plan"].create({"name": "Shared Account Plan"})
        cls.project_plan, _other_plans = cls.env["account.analytic.plan"]._get_all_plans()

        cls.company_a_account = cls.env["account.analytic.account"].create({
            "name": "Company A Account",
            "plan_id": cls.company_a_plan.id,
            "company_id": cls.company_a.id,
        })
        cls.company_b_account = cls.env["account.analytic.account"].create({
            "name": "Company B Account",
            "plan_id": cls.company_b_plan.id,
            "company_id": cls.company_b.id,
        })
        cls.env["account.analytic.account"].create({
            "name": "Shared Account",
            "plan_id": cls.shared_account_plan.id,
            "company_id": False,
        })
        cls.project_company_a_account = cls.env["account.analytic.account"].create({
            "name": "Project Account A",
            "plan_id": cls.project_plan.id,
            "company_id": cls.company_a.id,
        })

    def test_company_filter_keeps_shared_plan_visible(self):
        visible_field_names = self.env["project.project"].sudo().with_company(
            self.company_a
        )._get_company_visible_analytic_plan_field_names()

        self.assertIn(self.company_a_plan._column_name(), visible_field_names)
        self.assertIn(self.shared_plan._column_name(), visible_field_names)
        self.assertNotIn(self.company_b_plan._column_name(), visible_field_names)
        self.assertNotIn(self.shared_account_plan._column_name(), visible_field_names)

    def test_view_cache_key_changes_per_company(self):
        company_a_key = self.env["project.project"].with_company(self.company_a)._get_view_cache_key()
        company_b_key = self.env["project.project"].with_company(self.company_b)._get_view_cache_key()

        self.assertNotEqual(company_a_key, company_b_key)

    def test_analytic_view_visibility_depends_on_project_company_field(self):
        arch, _view = self.env["project.project"]._get_view(view_type="form")
        analytic_page = arch.xpath("//page[@name='analytic']")[0]

        company_a_field = analytic_page.xpath(f".//field[@name='{self.company_a_plan._column_name()}']")[0]
        company_b_field = analytic_page.xpath(f".//field[@name='{self.company_b_plan._column_name()}']")[0]
        shared_field = analytic_page.xpath(f".//field[@name='{self.shared_plan._column_name()}']")[0]
        shared_account_field = analytic_page.xpath(f".//field[@name='{self.shared_account_plan._column_name()}']")[0]

        self.assertEqual(company_a_field.get("invisible"), f"company_id not in [{self.company_a.id}]")
        self.assertEqual(company_b_field.get("invisible"), f"company_id not in [{self.company_b.id}]")
        self.assertIsNone(shared_field.get("invisible"))
        self.assertEqual(shared_account_field.get("invisible"), "True")

    def test_onchange_company_id_clears_analytic_fields(self):
        project = self.env["project.project"].new({
            "name": "Project Onchange Reset",
            "company_id": self.company_a.id,
        })
        project.account_id = self.project_company_a_account
        project[self.company_a_plan._column_name()] = self.company_a_account

        project.company_id = self.company_b
        project._onchange_company_id()

        self.assertFalse(project.account_id)
        self.assertFalse(project[self.company_a_plan._column_name()])

    def test_write_company_id_clears_analytic_fields(self):
        project = self.env["project.project"].create({
            "name": "Project Write Reset",
            "company_id": self.company_a.id,
            "account_id": self.project_company_a_account.id,
            self.company_a_plan._column_name(): self.company_a_account.id,
        })

        project.write({"company_id": self.company_b.id})

        self.assertEqual(project.company_id, self.company_b)
        self.assertFalse(project.account_id)
        self.assertFalse(project[self.company_a_plan._column_name()])

    def test_plan_visibility_updates_after_plan_write(self):
        arch, _view = self.env["project.project"]._get_view(view_type="form")
        analytic_page = arch.xpath("//page[@name='analytic']")[0]
        shared_field = analytic_page.xpath(f".//field[@name='{self.shared_plan._column_name()}']")[0]
        self.assertIsNone(shared_field.get("invisible"))

        self.shared_plan.write({"show_on_all_companies": False})

        arch, _view = self.env["project.project"]._get_view(view_type="form")
        analytic_page = arch.xpath("//page[@name='analytic']")[0]
        shared_field = analytic_page.xpath(f".//field[@name='{self.shared_plan._column_name()}']")[0]
        self.assertEqual(shared_field.get("invisible"), "True")


class TestProjectPrivacyVisibilityDefault(TransactionCase):
    def test_project_visibility_defaults_to_invited_internal_users(self):
        defaults = self.env["project.project"].default_get(["privacy_visibility"])
        self.assertEqual(defaults["privacy_visibility"], "followers")

        project = self.env["project.project"].create({"name": "Private Default Project"})
        self.assertEqual(project.privacy_visibility, "followers")

    def test_generated_project_from_template_defaults_to_private_visibility(self):
        partner = self.env["res.partner"].create({"name": "Generated Project Customer"})
        product = self.env["product.product"].create({
            "name": "Generated Project Service",
            "type": "service",
        })
        order = self.env["sale.order"].create({"partner_id": partner.id})
        sale_line = self.env["sale.order.line"].create({
            "order_id": order.id,
            "product_id": product.id,
            "name": product.name,
            "product_uom_qty": 1.0,
            "price_unit": 100.0,
        })
        template = self.env["project.project"].create({
            "name": "Public Template",
            "name_copy": "Public Template",
            "is_template": True,
            "privacy_visibility": "portal",
        })

        generated_project = template.copy({
            "name": "Generated From Public Template",
            "name_copy": "Generated From Public Template",
            "is_template": False,
            "partner_id": partner.id,
            "sale_line_id": sale_line.id,
        })

        self.assertEqual(generated_project.privacy_visibility, "followers")
