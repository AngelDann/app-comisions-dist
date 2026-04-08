from django.db import models
from simple_history.models import HistoricalRecords

from apps.core.models import CompanyBoundModel


class RuleFieldDefinition(CompanyBoundModel):
    """Catálogo extensible de campos disponibles en el rule builder."""

    key = models.SlugField(max_length=64)
    label = models.CharField(max_length=120)
    data_type = models.CharField(
        max_length=32,
        choices=[
            ("string", "Texto"),
            ("number", "Número"),
            ("boolean", "Booleano"),
            ("date", "Fecha"),
        ],
        default="string",
    )

    class Meta:
        unique_together = [("company", "key")]
        ordering = ["key"]

    def __str__(self) -> str:
        return self.label


class CommissionPlan(CompanyBoundModel):
    """Plan de comisión: agrupa reglas y asignaciones a equipos/empleados."""

    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="commission_plans",
    )
    is_active = models.BooleanField(default=True)
    is_global = models.BooleanField(
        default=False,
        help_text="Si está activo, el plan aplica a todos los eventos (filtrado por proyecto del plan si existe).",
    )
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField(null=True, blank=True)
    teams = models.ManyToManyField(
        "projects.Team",
        through="CommissionPlanTeam",
        related_name="commission_plans",
        blank=True,
    )
    employees = models.ManyToManyField(
        "staff.Employee",
        through="CommissionPlanEmployee",
        related_name="commission_plans",
        blank=True,
    )

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class CommissionPlanTeam(models.Model):
    plan = models.ForeignKey(
        CommissionPlan,
        on_delete=models.CASCADE,
        related_name="plan_teams",
    )
    team = models.ForeignKey(
        "projects.Team",
        on_delete=models.CASCADE,
        related_name="commission_plan_teams",
    )
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["plan", "team"]),
            models.Index(fields=["team", "valid_from", "valid_to"]),
        ]


class CommissionPlanEmployee(models.Model):
    plan = models.ForeignKey(
        CommissionPlan,
        on_delete=models.CASCADE,
        related_name="plan_employees",
    )
    employee = models.ForeignKey(
        "staff.Employee",
        on_delete=models.CASCADE,
        related_name="commission_plan_employees",
    )
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["plan", "employee"]),
            models.Index(fields=["employee", "valid_from", "valid_to"]),
        ]


class CommissionRule(CompanyBoundModel):
    plan = models.ForeignKey(
        CommissionPlan,
        on_delete=models.CASCADE,
        related_name="rules",
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="commission_rules",
    )
    team = models.ForeignKey(
        "projects.Team",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="commission_rules",
    )
    commission_type = models.ForeignKey(
        "commissions.CommissionType",
        on_delete=models.CASCADE,
        related_name="rules",
    )
    name = models.CharField(max_length=255)
    priority = models.PositiveIntegerField(default=100)
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField(null=True, blank=True)
    conditions_schema_version = models.PositiveSmallIntegerField(default=1)
    conditions = models.JSONField(default=dict)
    action_type = models.CharField(max_length=64)
    action_params = models.JSONField(default=dict)
    stop_processing = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["priority", "id"]
        indexes = [
            models.Index(fields=["company", "is_active", "priority"]),
            models.Index(fields=["company", "project", "team"]),
            models.Index(fields=["company", "plan"]),
        ]

    def __str__(self) -> str:
        return self.name
