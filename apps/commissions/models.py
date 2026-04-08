from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords

from apps.core.models import CompanyBoundModel


class CommissionType(CompanyBoundModel):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=80)
    description = models.TextField(blank=True)

    class Meta:
        unique_together = [("company", "slug")]
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class ProjectCommissionType(models.Model):
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="project_commission_types")
    commission_type = models.ForeignKey(CommissionType, on_delete=models.CASCADE, related_name="project_links")
    is_active = models.BooleanField(default=True)
    config = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = [("project", "commission_type")]


class PeriodState(models.TextChoices):
    DRAFT = "draft", "Borrador"
    REVIEW = "review", "En revisión"
    CLOSED = "closed", "Cerrado"


class FxPolicy(models.TextChoices):
    OPERATION_DATE = "operation_date", "Fecha de operación"
    PERIOD_END = "period_end", "Fin de periodo"


class CommissionPeriod(CompanyBoundModel):
    name = models.CharField(max_length=120)
    start_date = models.DateField()
    end_date = models.DateField()
    state = models.CharField(max_length=16, choices=PeriodState.choices, default=PeriodState.DRAFT)
    fx_policy = models.CharField(max_length=32, choices=FxPolicy.choices, default=FxPolicy.OPERATION_DATE)
    is_locked = models.BooleanField(default=False)

    class Meta:
        ordering = ["-start_date"]
        indexes = [models.Index(fields=["company", "state"])]

    def __str__(self) -> str:
        return self.name


class CommissionEvent(CompanyBoundModel):
    period = models.ForeignKey(CommissionPeriod, on_delete=models.CASCADE, related_name="events")
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="commission_events")
    team = models.ForeignKey("projects.Team", on_delete=models.CASCADE, related_name="commission_events")
    commission_type = models.ForeignKey(
        CommissionType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="events",
    )
    employee = models.ForeignKey(
        "staff.Employee",
        on_delete=models.CASCADE,
        related_name="commission_events",
    )
    event_kind = models.CharField(max_length=120)
    occurred_on = models.DateField()
    fx_rate = models.ForeignKey(
        "fx.FxRate",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="commission_events",
        help_text=(
            "Opcional. Si se elige, el monto está en fx_rate.currency_code; "
            "value del tipo de cambio = unidades de moneda base de la compañía por 1 unidad de esa moneda."
        ),
    )
    amount_usd = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    hours = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_business_hours = models.BooleanField(null=True, blank=True)
    sales_channel = models.CharField(max_length=120, blank=True)
    attributes = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_commission_events",
    )

    class Meta:
        ordering = ["-occurred_on", "-id"]
        indexes = [
            models.Index(fields=["company", "period", "project"]),
        ]

    def __str__(self) -> str:
        label = f"#{self.pk}" if self.pk else "Evento (nuevo)"
        emp = f"{self.employee}" if self.employee_id else "—"
        amt = self.amount_usd if self.amount_usd is not None else "—"
        return f"{label} {self.event_kind} · {emp} · {self.occurred_on} · {amt}"


class LineState(models.TextChoices):
    PENDING = "pending", "Pendiente"
    PENDING_APPROVAL = "pending_approval", "Pendiente aprobación"
    APPROVED = "approved", "Aprobado"
    REJECTED = "rejected", "Rechazado"
    ADJUSTED = "adjusted", "Ajustado"
    PAID = "paid", "Pagado"


class CommissionLine(CompanyBoundModel):
    event = models.ForeignKey(CommissionEvent, on_delete=models.CASCADE, related_name="lines")
    employee = models.ForeignKey("staff.Employee", on_delete=models.CASCADE, related_name="commission_lines")
    commission_type = models.ForeignKey(
        CommissionType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lines",
    )
    rule = models.ForeignKey(
        "rules.CommissionRule",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lines",
    )
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    state = models.CharField(max_length=32, choices=LineState.choices, default=LineState.PENDING)
    rule_snapshot = models.JSONField(default=dict, blank=True)
    calculation_explanation = models.TextField(blank=True)
    fx_rate_used = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["-id"]
        indexes = [
            models.Index(fields=["company", "employee", "state"]),
        ]

    def __str__(self) -> str:
        label = f"#{self.pk}" if self.pk else "Línea (nueva)"
        emp = f"{self.employee}" if self.employee_id else "—"
        st = self.get_state_display()
        date = self.event.occurred_on if self.event_id and self.event else "—"
        return f"{label} {emp} · {self.amount} {self.currency} · {st} · {date}"


class CalculationRun(CompanyBoundModel):
    period = models.ForeignKey(CommissionPeriod, on_delete=models.CASCADE, related_name="calculation_runs")
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="calculation_runs",
    )
    status = models.CharField(max_length=32, default="running")
    log = models.TextField(blank=True)

    class Meta:
        ordering = ["-started_at"]


class AdjustmentKind(models.TextChoices):
    CORRECTION = "correction", "Corrección"
    REFUND = "refund", "Reembolso"
    SUSPENSION = "suspension", "Suspensión"
    EXTRA_DISCOUNT = "extra_discount", "Descuento extraordinario"
    OTHER = "other", "Otro"


class Adjustment(CompanyBoundModel):
    line = models.ForeignKey(
        CommissionLine,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="adjustments",
    )
    event = models.ForeignKey(
        CommissionEvent,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="adjustments",
    )
    kind = models.CharField(max_length=32, choices=AdjustmentKind.choices)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    reason = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="commission_adjustments",
    )

    class Meta:
        ordering = ["-id"]
