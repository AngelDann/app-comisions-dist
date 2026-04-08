"""Tests para los 3 nuevos action_types: tiered_percent_period_aggregate,
split_pool_among_team y clawback_if_cancelled_before."""

from decimal import Decimal

from django.test import TestCase

from apps.commissions.engine import CommissionEngine
from apps.commissions.models import (
    CommissionEvent,
    CommissionPeriod,
    CommissionType,
    ProjectCommissionType,
)
from apps.companies.models import Company
from apps.projects.models import Project, ProjectTeam, Team
from apps.rules.models import CommissionPlan, CommissionRule
from apps.staff.models import Employee, EmployeeTeam


class _BaseSetup(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="TestCo", slug="testco-new")
        self.project = Project.objects.create(
            company=self.company, name="WispHub", slug="wisphub", is_active=True
        )
        self.team = Team.objects.create(
            company=self.company, name="Ventas", slug="ventas-new", is_active=True
        )
        ProjectTeam.objects.create(project=self.project, team=self.team, is_active=True)
        self.ct = CommissionType.objects.create(
            company=self.company, name="Venta", slug="venta-new"
        )
        ProjectCommissionType.objects.create(
            project=self.project, commission_type=self.ct, is_active=True
        )
        self.period = CommissionPeriod.objects.create(
            company=self.company,
            name="Enero 2026",
            start_date="2026-01-01",
            end_date="2026-01-31",
        )
        self.plan = CommissionPlan.objects.create(
            company=self.company, name="Plan test", is_global=True, is_active=True
        )
        self.emp1 = Employee.objects.create(
            company=self.company, first_name="Ana", last_name="López", is_active=True
        )
        self.emp2 = Employee.objects.create(
            company=self.company, first_name="Luis", last_name="García", is_active=True
        )
        self.emp3 = Employee.objects.create(
            company=self.company, first_name="Marta", last_name="Ruiz", is_active=True
        )
        EmployeeTeam.objects.create(employee=self.emp1, team=self.team)
        EmployeeTeam.objects.create(employee=self.emp2, team=self.team)
        EmployeeTeam.objects.create(employee=self.emp3, team=self.team)


class TieredPercentPeriodAggregateTests(_BaseSetup):
    """El % se elige según el acumulado del periodo, no del evento individual."""

    def _create_rule(self):
        return CommissionRule.objects.create(
            company=self.company,
            plan=self.plan,
            commission_type=self.ct,
            name="Tiered agg",
            priority=10,
            action_type="tiered_percent_period_aggregate",
            action_params={
                "brackets": [
                    {"min_amount": "0", "max_amount": "2200", "percent": "3"},
                    {"min_amount": "2200", "max_amount": "3500", "percent": "6"},
                    {"min_amount": "3500", "max_amount": "6000", "percent": "7"},
                    {"min_amount": "6000", "max_amount": "10000", "percent": "8"},
                    {"min_amount": "10000", "percent": "9"},
                ],
            },
            conditions={},
        )

    def test_single_event_below_first_tier(self):
        self._create_rule()
        ev = CommissionEvent.objects.create(
            company=self.company,
            period=self.period,
            project=self.project,
            team=self.team,
            employee=self.emp1,
            commission_type=self.ct,
            event_kind="sale",
            occurred_on="2026-01-10",
            amount_usd=Decimal("1000.00"),
        )
        lines = CommissionEngine.evaluate(ev)
        self.assertEqual(len(lines), 1)
        # acumulado = 1000 → tramo 0-2200 → 3%
        self.assertEqual(lines[0].amount, Decimal("30.00"))

    def test_aggregate_pushes_to_higher_tier(self):
        self._create_rule()
        CommissionEvent.objects.create(
            company=self.company,
            period=self.period,
            project=self.project,
            team=self.team,
            employee=self.emp1,
            commission_type=self.ct,
            event_kind="sale",
            occurred_on="2026-01-05",
            amount_usd=Decimal("2000.00"),
        )
        ev2 = CommissionEvent.objects.create(
            company=self.company,
            period=self.period,
            project=self.project,
            team=self.team,
            employee=self.emp1,
            commission_type=self.ct,
            event_kind="sale",
            occurred_on="2026-01-15",
            amount_usd=Decimal("500.00"),
        )
        lines = CommissionEngine.evaluate(ev2)
        self.assertEqual(len(lines), 1)
        # acumulado = 2000 + 500 = 2500 → tramo 2200-3500 → 6% sobre evento (500)
        self.assertEqual(lines[0].amount, Decimal("30.00"))

    def test_top_tier(self):
        self._create_rule()
        ev = CommissionEvent.objects.create(
            company=self.company,
            period=self.period,
            project=self.project,
            team=self.team,
            employee=self.emp1,
            commission_type=self.ct,
            event_kind="sale",
            occurred_on="2026-01-20",
            amount_usd=Decimal("15000.00"),
        )
        lines = CommissionEngine.evaluate(ev)
        self.assertEqual(len(lines), 1)
        # acumulado = 15000 → tramo >=10000 → 9% sobre 15000
        self.assertEqual(lines[0].amount, Decimal("1350.00"))

    def test_different_employee_not_mixed(self):
        """Acumulado es por empleado, no global."""
        self._create_rule()
        CommissionEvent.objects.create(
            company=self.company,
            period=self.period,
            project=self.project,
            team=self.team,
            employee=self.emp2,
            commission_type=self.ct,
            event_kind="sale",
            occurred_on="2026-01-05",
            amount_usd=Decimal("9000.00"),
        )
        ev = CommissionEvent.objects.create(
            company=self.company,
            period=self.period,
            project=self.project,
            team=self.team,
            employee=self.emp1,
            commission_type=self.ct,
            event_kind="sale",
            occurred_on="2026-01-10",
            amount_usd=Decimal("1000.00"),
        )
        lines = CommissionEngine.evaluate(ev)
        # emp1 acumulado = 1000 → tramo 0-2200 → 3%
        self.assertEqual(lines[0].amount, Decimal("30.00"))


class SplitPoolAmongTeamTests(_BaseSetup):
    """Reparto dinámico entre miembros activos de un equipo."""

    def test_splits_evenly_among_team_members(self):
        CommissionRule.objects.create(
            company=self.company,
            plan=self.plan,
            commission_type=self.ct,
            name="Bono equipo",
            priority=10,
            action_type="split_pool_among_team",
            action_params={"pool_amount": "15000", "team_id": self.team.pk},
            conditions={},
        )
        ev = CommissionEvent.objects.create(
            company=self.company,
            period=self.period,
            project=self.project,
            team=self.team,
            employee=self.emp1,
            commission_type=self.ct,
            event_kind="bono_soporte",
            occurred_on="2026-01-15",
            amount_usd=Decimal("0"),
        )
        lines = CommissionEngine.evaluate(ev)
        self.assertEqual(len(lines), 3)
        # 15000 / 3 = 5000 each
        for line in lines:
            self.assertEqual(line.amount, Decimal("5000.00"))
        emp_ids = {l.employee_id for l in lines}
        self.assertEqual(emp_ids, {self.emp1.pk, self.emp2.pk, self.emp3.pk})

    def test_inactive_employee_excluded(self):
        self.emp3.is_active = False
        self.emp3.save()
        CommissionRule.objects.create(
            company=self.company,
            plan=self.plan,
            commission_type=self.ct,
            name="Bono equipo",
            priority=10,
            action_type="split_pool_among_team",
            action_params={"pool_amount": "6000", "team_id": self.team.pk},
            conditions={},
        )
        ev = CommissionEvent.objects.create(
            company=self.company,
            period=self.period,
            project=self.project,
            team=self.team,
            employee=self.emp1,
            commission_type=self.ct,
            event_kind="bono_soporte",
            occurred_on="2026-01-15",
            amount_usd=Decimal("0"),
        )
        lines = CommissionEngine.evaluate(ev)
        self.assertEqual(len(lines), 2)
        for line in lines:
            self.assertEqual(line.amount, Decimal("3000.00"))

    def test_empty_team_creates_pending_approval_line(self):
        other_team = Team.objects.create(
            company=self.company, name="Vacío", slug="vacio", is_active=True
        )
        ProjectTeam.objects.create(project=self.project, team=other_team, is_active=True)
        CommissionRule.objects.create(
            company=self.company,
            plan=self.plan,
            commission_type=self.ct,
            name="Bono vacío",
            priority=10,
            action_type="split_pool_among_team",
            action_params={"pool_amount": "1000", "team_id": other_team.pk},
            conditions={},
        )
        ev = CommissionEvent.objects.create(
            company=self.company,
            period=self.period,
            project=self.project,
            team=self.team,
            employee=self.emp1,
            commission_type=self.ct,
            event_kind="bono",
            occurred_on="2026-01-15",
            amount_usd=Decimal("0"),
        )
        lines = CommissionEngine.evaluate(ev)
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0].amount, Decimal("0"))
        self.assertEqual(lines[0].state, "pending_approval")


class ClawbackIfCancelledBeforeTests(_BaseSetup):
    """Descuento automático por cancelación antes de N meses."""

    def _create_rule(self):
        return CommissionRule.objects.create(
            company=self.company,
            plan=self.plan,
            commission_type=self.ct,
            name="Clawback 3m",
            priority=10,
            action_type="clawback_if_cancelled_before",
            action_params={"months": 3, "percent": "100"},
            conditions={
                "kind": "leaf",
                "field": "event_kind",
                "op": "eq",
                "value": "cancellation",
            },
        )

    def test_clawback_triggers_when_months_active_below_threshold(self):
        self._create_rule()
        ev = CommissionEvent.objects.create(
            company=self.company,
            period=self.period,
            project=self.project,
            team=self.team,
            employee=self.emp1,
            commission_type=self.ct,
            event_kind="cancellation",
            occurred_on="2026-01-20",
            amount_usd=Decimal("500.00"),
            attributes={"months_active": 1},
        )
        lines = CommissionEngine.evaluate(ev)
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0].amount, Decimal("-500.00"))
        self.assertIn("Clawback", lines[0].calculation_explanation)

    def test_no_clawback_when_months_active_at_threshold(self):
        self._create_rule()
        ev = CommissionEvent.objects.create(
            company=self.company,
            period=self.period,
            project=self.project,
            team=self.team,
            employee=self.emp1,
            commission_type=self.ct,
            event_kind="cancellation",
            occurred_on="2026-01-20",
            amount_usd=Decimal("500.00"),
            attributes={"months_active": 3},
        )
        lines = CommissionEngine.evaluate(ev)
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0].amount, Decimal("0"))
        self.assertIn("Sin clawback", lines[0].calculation_explanation)

    def test_no_clawback_when_months_active_missing(self):
        self._create_rule()
        ev = CommissionEvent.objects.create(
            company=self.company,
            period=self.period,
            project=self.project,
            team=self.team,
            employee=self.emp1,
            commission_type=self.ct,
            event_kind="cancellation",
            occurred_on="2026-01-20",
            amount_usd=Decimal("500.00"),
            attributes={},
        )
        lines = CommissionEngine.evaluate(ev)
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0].amount, Decimal("0"))

    def test_partial_clawback_percentage(self):
        CommissionRule.objects.create(
            company=self.company,
            plan=self.plan,
            commission_type=self.ct,
            name="Clawback parcial",
            priority=10,
            action_type="clawback_if_cancelled_before",
            action_params={"months": 3, "percent": "50"},
            conditions={
                "kind": "leaf",
                "field": "event_kind",
                "op": "eq",
                "value": "cancellation",
            },
        )
        ev = CommissionEvent.objects.create(
            company=self.company,
            period=self.period,
            project=self.project,
            team=self.team,
            employee=self.emp1,
            commission_type=self.ct,
            event_kind="cancellation",
            occurred_on="2026-01-20",
            amount_usd=Decimal("1000.00"),
            attributes={"months_active": 2},
        )
        lines = CommissionEngine.evaluate(ev)
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0].amount, Decimal("-500.00"))
