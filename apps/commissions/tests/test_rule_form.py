"""Formulario de reglas: condiciones visuales y parámetros de acción estructurados."""

from decimal import Decimal

from django.test import TestCase

from apps.commissions.ops_views import CommissionRuleForm
from apps.commissions.models import CommissionType
from apps.companies.models import Company
from apps.rules.models import CommissionPlan, CommissionRule


class CommissionRuleFormTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Co", slug="co-rule-form")
        self.plan = CommissionPlan.objects.create(
            company=self.company,
            name="Plan1",
            is_global=True,
            is_active=True,
        )
        self.ct = CommissionType.objects.create(company=self.company, name="Venta", slug="venta-rf")

    def _base_post(self, **extra):
        data = {
            "name": "Regla test",
            "commission_type": str(self.ct.pk),
            "priority": "10",
            "action_type": "percent_of_amount",
            "percent": "12.5",
            "conditions_editor_mode": "visual",
            "action_params_editor_mode": "structured",
            "is_active": "on",
        }
        data.update(extra)
        return data

    def test_visual_conditions_and_percent_action(self):
        data = self._base_post(
            cg_0_l_0_field="event_kind",
            cg_0_l_0_op="eq",
            cg_0_l_0_value="sale",
        )
        form = CommissionRuleForm(data, company=self.company, lock_plan=self.plan)
        self.assertTrue(form.is_valid(), form.errors)
        rule = form.save()
        self.assertEqual(rule.action_type, "percent_of_amount")
        self.assertEqual(rule.action_params.get("percent"), "12.5")
        self.assertEqual(rule.conditions["kind"], "group")
        leaf = rule.conditions["children"][0]
        self.assertEqual(leaf["field"], "event_kind")
        self.assertEqual(leaf["value"], "sale")

    def test_advanced_conditions_json(self):
        cond = '{"kind": "group", "op": "AND", "children": [{"kind": "leaf", "field": "amount_usd", "op": "gte", "value": 500}]}'
        data = self._base_post(
            conditions_editor_mode="advanced",
            conditions_json=cond,
        )
        form = CommissionRuleForm(data, company=self.company, lock_plan=self.plan)
        self.assertTrue(form.is_valid(), form.errors)
        rule = form.save()
        self.assertEqual(rule.conditions["children"][0]["value"], 500)

    def test_tiered_percent_structured(self):
        data = self._base_post(
            action_type="tiered_percent",
            ap_tier_0_min="0",
            ap_tier_0_max="1000",
            ap_tier_0_percent="5",
            ap_tier_1_min="1000",
            ap_tier_1_max="",
            ap_tier_1_percent="10",
        )
        del data["percent"]
        form = CommissionRuleForm(data, company=self.company, lock_plan=self.plan)
        self.assertTrue(form.is_valid(), form.errors)
        rule = form.save()
        self.assertEqual(rule.action_type, "tiered_percent")
        self.assertEqual(len(rule.action_params["brackets"]), 2)
        self.assertEqual(Decimal(str(rule.action_params["brackets"][1]["percent"])), Decimal("10"))

    def test_action_advanced_json(self):
        data = self._base_post(
            action_params_editor_mode="advanced",
            action_params_json='{"percent": "7"}',
        )
        del data["percent"]
        form = CommissionRuleForm(data, company=self.company, lock_plan=self.plan)
        self.assertTrue(form.is_valid(), form.errors)
        rule = form.save()
        self.assertEqual(rule.action_params.get("percent"), "7")

    def test_edit_form_keeps_instance_action_type_selected(self):
        rule = CommissionRule.objects.create(
            company=self.company,
            plan=self.plan,
            commission_type=self.ct,
            name="Regla fija",
            priority=30,
            action_type="fixed_per_event",
            action_params={"amount": "850"},
            conditions={"kind": "group", "op": "AND", "children": []},
            is_active=True,
        )
        form = CommissionRuleForm(instance=rule, company=self.company, lock_plan=self.plan)
        self.assertEqual(form["action_type"].value(), "fixed_per_event")
