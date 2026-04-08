"""Carga datos de demostración (comisiones) para una compañía existente."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from random import Random

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.commissions.engine import CommissionEngine
from apps.commissions.models import (
    CommissionEvent,
    CommissionLine,
    CommissionPeriod,
    CommissionType,
    LineState,
    PeriodState,
    ProjectCommissionType,
)
from apps.companies.models import Company
from apps.projects.models import Project, ProjectTeam, Team
from apps.rules.models import CommissionPlan, CommissionRule
from apps.staff.models import Employee, EmployeeTeam


SEED_ATTR = "_seed"
PLAN_NAME = "[seed] Plan demostración"
RULE_PCT_NAME = "[seed] % sobre monto (ventas)"
RULE_FIXED_NAME = "[seed] Monto fijo (soporte)"
EMP_CODE_PREFIX = "seed-demo-"


def _resolve_company(slug_or_name: str) -> Company:
    s = slug_or_name.strip()
    if not s:
        raise CommandError("Indica slug o nombre de compañía.")
    c = Company.objects.filter(slug__iexact=s).first()
    if c:
        return c
    c = Company.objects.filter(name__iexact=s).first()
    if c:
        return c
    c = Company.objects.filter(name__icontains=s).first()
    if c:
        return c
    raise CommandError(f"No se encontró compañía con slug o nombre: {slug_or_name!r}")


class Command(BaseCommand):
    help = (
        "Crea empleados, tipos, plan, reglas y eventos de prueba con líneas calculadas. "
        "Por defecto busca la compañía 'cobranet'. Usa --reset para borrar datos anteriores marcados como seed."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "company",
            nargs="?",
            default="cobranet",
            help="Slug o nombre de la compañía (por defecto: cobranet)",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Elimina eventos/reglas/plan/empleados creados por este comando antes de volver a cargar.",
        )

    def handle(self, *args, **options):
        company = _resolve_company(options["company"])
        reset = options["reset"]

        if reset:
            self._reset_seed(company)

        existing_events = CommissionEvent.objects.filter(
            company=company,
            attributes__contains={SEED_ATTR: True},
        ).count()
        if existing_events and not reset:
            raise CommandError(
                f"Ya hay {existing_events} eventos semilla. Pasa --reset para reemplazarlos."
            )

        with transaction.atomic():
            project, teams = self._ensure_project_and_teams(company)
            employees = self._ensure_employees(company, teams)
            ct_venta, ct_soporte = self._ensure_commission_types(company, project)
            period = self._ensure_period(company)
            plan = self._ensure_plan_and_rules(company, project, ct_venta, ct_soporte)
            self.stdout.write(self.style.NOTICE(f"Plan: {plan.name} (id={plan.pk})"))

            rng = Random(42)
            base_day = max(period.start_date, date.today() - timedelta(days=60))
            if base_day > period.end_date:
                base_day = period.start_date

            event_specs = [
                ("venta_directa", ct_venta, Decimal("12500.00")),
                ("venta_directa", ct_venta, Decimal("8200.50")),
                ("renovacion", ct_venta, Decimal("45000.00")),
                ("venta_directa", ct_venta, Decimal("3100.00")),
                ("venta_directa", ct_venta, Decimal("27500.75")),
                ("soporte_mensual", ct_soporte, Decimal("0")),
                ("soporte_mensual", ct_soporte, Decimal("0")),
                ("venta_directa", ct_venta, Decimal("990.00")),
                ("venta_directa", ct_venta, Decimal("15600.00")),
                ("soporte_mensual", ct_soporte, Decimal("0")),
                ("venta_directa", ct_venta, Decimal("22000.00")),
                ("renovacion", ct_venta, Decimal("18000.00")),
            ]

            created = 0
            for i, (kind, ct, amount) in enumerate(event_specs):
                emp = employees[i % len(employees)]
                team = teams[i % len(teams)]
                span_days = max(0, (period.end_date - base_day).days)
                offset = timedelta(days=rng.randint(0, min(45, span_days)))
                occurred = base_day + offset
                if occurred > period.end_date:
                    occurred = period.end_date
                if occurred < period.start_date:
                    occurred = period.start_date

                ev = CommissionEvent.objects.create(
                    company=company,
                    period=period,
                    project=project,
                    team=team,
                    commission_type=ct,
                    employee=emp,
                    event_kind=kind,
                    occurred_on=occurred,
                    amount_usd=amount,
                    notes="Evento generado por seed_commission_demo (datos de prueba).",
                    attributes={SEED_ATTR: True, "demo_index": i + 1},
                )
                lines = CommissionEngine.evaluate(ev)
                created += 1
                self.stdout.write(f"  Evento {ev.pk} ({kind}): {len(lines)} línea(s)")

            # Varía estados de líneas para el tablero / resumen
            line_ids = list(
                CommissionLine.objects.filter(
                    event__company=company,
                    event__attributes__contains={SEED_ATTR: True},
                ).values_list("pk", flat=True)
            )
            half = max(1, len(line_ids) // 3)
            CommissionLine.objects.filter(pk__in=line_ids[:half]).update(state=LineState.APPROVED)
            CommissionLine.objects.filter(pk__in=line_ids[half : half * 2]).update(
                state=LineState.PENDING_APPROVAL
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Listo: compañía «{company.name}», {created} eventos y líneas asociadas."
            )
        )

    def _reset_seed(self, company: Company) -> None:
        qs_ev = CommissionEvent.objects.filter(
            company=company,
            attributes__contains={SEED_ATTR: True},
        )
        n_ev = qs_ev.count()
        qs_ev.delete()
        CommissionRule.objects.filter(company=company, name__startswith="[seed]").delete()
        CommissionPlan.objects.filter(company=company, name__startswith="[seed]").delete()
        Employee.objects.filter(company=company, employee_code__startswith=EMP_CODE_PREFIX).delete()
        self.stdout.write(self.style.WARNING(f"Reset: eliminados {n_ev} eventos semilla y datos ligados."))

    def _ensure_project_and_teams(self, company: Company) -> tuple[Project, list[Team]]:
        project = (
            Project.objects.filter(company=company, is_active=True).order_by("id").first()
        )
        if not project:
            project = Project.objects.create(
                company=company,
                name="Proyecto demo",
                slug="demo-proyecto",
                is_active=True,
            )
            self.stdout.write("  Creado proyecto demo.")

        teams = list(Team.objects.filter(company=company, is_active=True).order_by("id")[:3])
        if len(teams) < 2:
            t2, _ = Team.objects.get_or_create(
                company=company,
                slug="seed-equipo-cobranza",
                defaults={"name": "Cobranza (demo)", "is_active": True},
            )
            if t2 not in teams:
                teams.append(t2)
        if len(teams) < 2:
            t3, _ = Team.objects.get_or_create(
                company=company,
                slug="seed-equipo-soporte",
                defaults={"name": "Soporte (demo)", "is_active": True},
            )
            if t3 not in teams:
                teams.append(t3)
        teams = list(
            Team.objects.filter(company=company, is_active=True, pk__in=[t.pk for t in teams]).order_by("id")
        )[:3]

        for t in teams:
            ProjectTeam.objects.get_or_create(
                project=project,
                team=t,
                defaults={"is_active": True, "sort_order": 0},
            )
        return project, teams

    def _ensure_employees(self, company: Company, teams: list[Team]) -> list[Employee]:
        specs = [
            ("María", "García"),
            ("Luis", "Hernández"),
            ("Ana", "Martínez"),
            ("Carlos", "Ruiz"),
        ]
        out: list[Employee] = []
        for i, (fn, ln) in enumerate(specs):
            code = f"{EMP_CODE_PREFIX}{i + 1}"
            emp, created = Employee.objects.get_or_create(
                company=company,
                employee_code=code,
                defaults={"first_name": fn, "last_name": ln, "is_active": True},
            )
            if created:
                self.stdout.write(f"  Empleado {emp}")
            team = teams[i % len(teams)]
            EmployeeTeam.objects.get_or_create(employee=emp, team=team)
            out.append(emp)
        return out

    def _ensure_commission_types(
        self, company: Company, project: Project
    ) -> tuple[CommissionType, CommissionType]:
        ct_venta, _ = CommissionType.objects.get_or_create(
            company=company,
            slug="ventas-demo",
            defaults={"name": "Ventas (demo)", "description": ""},
        )
        ct_soporte, _ = CommissionType.objects.get_or_create(
            company=company,
            slug="soporte-demo",
            defaults={"name": "Soporte (demo)", "description": ""},
        )
        ProjectCommissionType.objects.get_or_create(
            project=project,
            commission_type=ct_venta,
            defaults={"is_active": True},
        )
        ProjectCommissionType.objects.get_or_create(
            project=project,
            commission_type=ct_soporte,
            defaults={"is_active": True},
        )
        return ct_venta, ct_soporte

    def _ensure_period(self, company: Company) -> CommissionPeriod:
        today = date.today()
        period = (
            CommissionPeriod.objects.filter(
                company=company,
                start_date__lte=today,
                end_date__gte=today,
            )
            .exclude(state=PeriodState.CLOSED)
            .order_by("-start_date")
            .first()
        )
        if period:
            return period
        period = CommissionPeriod.objects.create(
            company=company,
            name=f"Periodo operativo {today.year}",
            start_date=date(today.year, 1, 1),
            end_date=date(today.year, 12, 31),
            state=PeriodState.DRAFT,
        )
        self.stdout.write(f"  Creado periodo {period.name}")
        return period

    def _ensure_plan_and_rules(
        self,
        company: Company,
        project: Project,
        ct_venta: CommissionType,
        ct_soporte: CommissionType,
    ) -> CommissionPlan:
        wide_start = date(2020, 1, 1)
        plan, created = CommissionPlan.objects.get_or_create(
            company=company,
            name=PLAN_NAME,
            defaults={
                "description": "Generado por seed_commission_demo",
                "project": project,
                "is_active": True,
                "is_global": True,
                "valid_from": wide_start,
                "valid_to": None,
            },
        )
        if created:
            self.stdout.write(f"  Creado {plan.name}")
        else:
            # Asegura alcance correcto si el plan ya existía
            updates = []
            if plan.project_id != project.id:
                plan.project = project
                updates.append("project")
            if not plan.is_global:
                plan.is_global = True
                updates.append("is_global")
            if not plan.is_active:
                plan.is_active = True
                updates.append("is_active")
            if updates:
                plan.save(update_fields=updates)

        CommissionRule.objects.get_or_create(
            company=company,
            plan=plan,
            name=RULE_PCT_NAME,
            defaults={
                "commission_type": ct_venta,
                "priority": 10,
                "action_type": "percent_of_amount",
                "action_params": {"percent": "6"},
                "conditions": {},
                "is_active": True,
                "valid_from": wide_start,
                "valid_to": None,
                "stop_processing": True,
            },
        )
        CommissionRule.objects.get_or_create(
            company=company,
            plan=plan,
            name=RULE_FIXED_NAME,
            defaults={
                "commission_type": ct_soporte,
                "priority": 20,
                "action_type": "fixed_per_event",
                "action_params": {"amount": "850"},
                "conditions": {
                    "kind": "leaf",
                    "field": "event_kind",
                    "op": "eq",
                    "value": "soporte_mensual",
                },
                "is_active": True,
                "valid_from": wide_start,
                "valid_to": None,
                "stop_processing": True,
            },
        )
        return plan
