"""Resolución de planes y motor con planes globales y asignaciones."""

from decimal import Decimal

from django.test import TestCase

from apps.commissions.engine import CommissionEngine, resolve_plan_ids_for_event
from apps.commissions.models import (
    CommissionEvent,
    CommissionPeriod,
    CommissionType,
    ProjectCommissionType,
)
from apps.companies.models import Company
from apps.projects.models import Project, ProjectTeam, Team
from apps.rules.models import (
    CommissionPlan,
    CommissionPlanEmployee,
    CommissionPlanTeam,
    CommissionRule,
)
from apps.staff.models import Employee


class PlanResolutionTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Co", slug="co")
        self.project = Project.objects.create(company=self.company, name="P1", slug="p1", is_active=True)
        self.team = Team.objects.create(company=self.company, name="Ventas", slug="ventas", is_active=True)
        ProjectTeam.objects.create(project=self.project, team=self.team, is_active=True)
        self.employee = Employee.objects.create(
            company=self.company,
            first_name="Ana",
            last_name="López",
            is_active=True,
        )
        self.ct = CommissionType.objects.create(company=self.company, name="Venta", slug="venta")
        ProjectCommissionType.objects.create(project=self.project, commission_type=self.ct, is_active=True)
        self.period = CommissionPeriod.objects.create(
            company=self.company,
            name="Ene",
            start_date="2026-01-01",
            end_date="2026-01-31",
        )
        self.event = CommissionEvent.objects.create(
            company=self.company,
            period=self.period,
            project=self.project,
            team=self.team,
            employee=self.employee,
            commission_type=self.ct,
            event_kind="sale",
            occurred_on="2026-01-15",
            amount_usd=Decimal("1000.00"),
        )

    def test_resolve_empty_without_plans(self):
        self.assertEqual(resolve_plan_ids_for_event(self.event), set())

    def test_global_plan_all_projects(self):
        plan = CommissionPlan.objects.create(
            company=self.company,
            name="Global",
            is_global=True,
            is_active=True,
        )
        ids = resolve_plan_ids_for_event(self.event)
        self.assertIn(plan.id, ids)

    def test_global_plan_scoped_to_other_project_excluded(self):
        p2 = Project.objects.create(company=self.company, name="P2", slug="p2", is_active=True)
        plan = CommissionPlan.objects.create(
            company=self.company,
            name="Solo P2",
            project=p2,
            is_global=True,
            is_active=True,
        )
        self.assertNotIn(plan.id, resolve_plan_ids_for_event(self.event))

    def test_global_plan_inactive_excluded(self):
        plan = CommissionPlan.objects.create(
            company=self.company,
            name="Off",
            is_global=True,
            is_active=False,
        )
        self.assertNotIn(plan.id, resolve_plan_ids_for_event(self.event))

    def test_employee_assignment(self):
        plan = CommissionPlan.objects.create(company=self.company, name="Emp", is_global=False, is_active=True)
        CommissionPlanEmployee.objects.create(plan=plan, employee=self.employee)
        self.assertIn(plan.id, resolve_plan_ids_for_event(self.event))

    def test_team_assignment(self):
        plan = CommissionPlan.objects.create(company=self.company, name="TeamP", is_global=False, is_active=True)
        CommissionPlanTeam.objects.create(plan=plan, team=self.team)
        self.assertIn(plan.id, resolve_plan_ids_for_event(self.event))

    def test_assignment_date_outside_excluded(self):
        plan = CommissionPlan.objects.create(company=self.company, name="Emp", is_global=False, is_active=True)
        CommissionPlanEmployee.objects.create(
            plan=plan,
            employee=self.employee,
            valid_from="2026-02-01",
            valid_to="2026-02-28",
        )
        self.assertNotIn(plan.id, resolve_plan_ids_for_event(self.event))

    def test_engine_no_lines_when_no_plan_resolved(self):
        plan = CommissionPlan.objects.create(company=self.company, name="Aislado", is_global=False, is_active=True)
        CommissionRule.objects.create(
            company=self.company,
            plan=plan,
            commission_type=self.ct,
            name="Sin asignar",
            priority=10,
            action_type="percent_of_amount",
            action_params={"percent": "5"},
            conditions={},
        )
        self.assertEqual(CommissionEngine.evaluate(self.event), [])

    def test_engine_rule_on_global_plan_applies(self):
        plan = CommissionPlan.objects.create(
            company=self.company,
            name="G",
            is_global=True,
            is_active=True,
        )
        CommissionRule.objects.create(
            company=self.company,
            plan=plan,
            commission_type=self.ct,
            name="R1",
            priority=10,
            action_type="percent_of_amount",
            action_params={"percent": "7"},
            conditions={},
        )
        lines = CommissionEngine.evaluate(self.event)
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0].amount, Decimal("70.00"))
