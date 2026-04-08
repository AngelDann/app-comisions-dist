"""Motor de comisiones: evaluación de reglas sobre eventos."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from django.db.models import Sum

from apps.commissions.models import (
    CommissionEvent,
    CommissionLine,
    FxPolicy,
    LineState,
    ProjectCommissionType,
)
from apps.rules.models import (
    CommissionPlan,
    CommissionPlanEmployee,
    CommissionPlanTeam,
    CommissionRule,
)
from apps.rules.validators import validate_action_params


def _assignment_covers_date(d: date, valid_from, valid_to) -> bool:
    if valid_from is not None:
        valid_from = _as_date(valid_from)
        if d < valid_from:
            return False
    if valid_to is not None:
        valid_to = _as_date(valid_to)
        if d > valid_to:
            return False
    return True


def _plan_active_on_date(plan, d: date) -> bool:
    if not plan.is_active:
        return False
    vf, vt = plan.valid_from, plan.valid_to
    if vf is not None:
        vf = _as_date(vf)
        if d < vf:
            return False
    if vt is not None:
        vt = _as_date(vt)
        if d > vt:
            return False
    return True


def _as_date(d) -> date:
    if d is None:
        return timezone.now().date()
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, date):
        return d
    if isinstance(d, str):
        return date.fromisoformat(d[:10])
    return d


def resolve_plan_ids_for_event(event: CommissionEvent) -> set[int]:
    """Planes resueltos por asignación (empleado/equipo) y planes globales vigentes."""
    d = _as_date(event.occurred_on)
    company_id = event.company_id
    ids: set[int] = set()

    for row in CommissionPlanEmployee.objects.filter(
        employee_id=event.employee_id,
        plan__company_id=company_id,
    ).select_related("plan"):
        if not _assignment_covers_date(d, row.valid_from, row.valid_to):
            continue
        if not _plan_active_on_date(row.plan, d):
            continue
        ids.add(row.plan_id)

    for row in CommissionPlanTeam.objects.filter(
        team_id=event.team_id,
        plan__company_id=company_id,
    ).select_related("plan"):
        if not _assignment_covers_date(d, row.valid_from, row.valid_to):
            continue
        if not _plan_active_on_date(row.plan, d):
            continue
        ids.add(row.plan_id)

    for plan in CommissionPlan.objects.filter(
        company_id=company_id,
        is_active=True,
        is_global=True,
    ):
        if not _plan_active_on_date(plan, d):
            continue
        if plan.project_id is not None and plan.project_id != event.project_id:
            continue
        ids.add(plan.id)

    return ids


def lookup_fx_rate_for_event(event: CommissionEvent, currency_code: str) -> Decimal | None:
    """Tipo de cambio de referencia: moneda extranjera respecto a la moneda base de la compañía.

    ``FxRate.value`` = unidades de moneda base por 1 unidad de ``currency_code``.
    """
    company = event.company
    base = (company.base_currency or "MXN").upper()
    code = (currency_code or "USD").upper()
    if code == base:
        return Decimal("1")
    from apps.fx.models import FxRate

    if event.period.fx_policy == FxPolicy.PERIOD_END:
        ref_date = event.period.end_date
    else:
        ref_date = event.occurred_on
    rate = (
        FxRate.objects.filter(
            company=company,
            currency_code=code,
            rate_date__lte=ref_date,
        )
        .order_by("-rate_date")
        .first()
    )
    return rate.value if rate else None


def event_amount_in_base_currency(event: CommissionEvent) -> Decimal:
    """Monto del evento expresado en la moneda base de la compañía (para reglas y tramos)."""
    raw = event.amount_usd
    if raw is None:
        return Decimal("0")
    company = event.company
    base = (company.base_currency or "MXN").upper()
    fx = getattr(event, "fx_rate", None)
    if fx is None:
        return raw
    code = fx.currency_code.upper()
    if code == base:
        return raw
    return (raw * fx.value).quantize(Decimal("0.01"))


def resolve_fx_rate_used_for_event(event: CommissionEvent) -> Decimal | None:
    """TC aplicado al evento: el elegido explícitamente o 1 si el monto ya está en moneda base."""
    fx = getattr(event, "fx_rate", None)
    if fx is not None:
        return fx.value
    base = (event.company.base_currency or "MXN").upper()
    return lookup_fx_rate_for_event(event, base)


def build_context(event: CommissionEvent) -> dict[str, Any]:
    ctx = {
        "project_id": event.project_id,
        "team_id": event.team_id,
        "event_kind": event.event_kind,
        "amount_usd": float(event_amount_in_base_currency(event)),
        "hours": float(event.hours or Decimal("0")),
        "is_business_hours": event.is_business_hours,
        "sales_channel": event.sales_channel or "",
        "period_id": event.period_id,
    }
    if isinstance(event.attributes, dict):
        for k, v in event.attributes.items():
            if k not in ctx:
                ctx[k] = v
    return ctx


def _compare(op: str, left: Any, right: Any) -> bool:
    if op == "eq":
        return left == right
    if op == "ne":
        return left != right
    if op == "gte":
        return left >= right
    if op == "lte":
        return left <= right
    if op == "gt":
        return left > right
    if op == "lt":
        return left < right
    if op == "in":
        if not isinstance(right, (list, tuple, set)):
            return False
        return left in right
    return False


def _eval_leaf(node: dict[str, Any], ctx: dict[str, Any]) -> bool:
    field = node.get("field")
    op = node.get("op")
    value = node.get("value")
    if field is None or op is None:
        return False
    left = ctx.get(field)
    if left is None and field in ctx:
        pass
    if left is None:
        left = ctx.get(field, None)
    try:
        if isinstance(value, (int, float)) and isinstance(left, str):
            left = float(left)
        if isinstance(value, (int, float)) and left is not None:
            left = float(left)
    except (TypeError, ValueError):
        pass
    return _compare(str(op), left, value)


def evaluate_conditions(node: dict[str, Any] | None, ctx: dict[str, Any]) -> bool:
    if not node:
        return True
    kind = node.get("kind")
    if kind == "leaf":
        return _eval_leaf(node, ctx)
    if kind == "group":
        op = node.get("op", "AND")
        children = node.get("children") or []
        if op == "AND":
            return all(evaluate_conditions(c, ctx) for c in children)
        if op == "OR":
            return any(evaluate_conditions(c, ctx) for c in children)
    return False


def _rule_applies_to_context(rule: CommissionRule, event: CommissionEvent, ctx: dict[str, Any]) -> bool:
    if rule.project_id and rule.project_id != event.project_id:
        return False
    if rule.team_id and rule.team_id != event.team_id:
        return False
    today = timezone.now().date()
    if rule.valid_from and today < rule.valid_from:
        return False
    if rule.valid_to and today > rule.valid_to:
        return False
    if event.occurred_on:
        od = event.occurred_on
        if rule.valid_from and od < rule.valid_from:
            return False
        if rule.valid_to and od > rule.valid_to:
            return False
    return evaluate_conditions(rule.conditions if isinstance(rule.conditions, dict) else {}, ctx)


def _period_aggregate_for_employee(event: CommissionEvent) -> Decimal:
    """Suma de amount_usd de todos los eventos del mismo periodo y empleado."""
    total = (
        CommissionEvent.objects.filter(
            company_id=event.company_id,
            period_id=event.period_id,
            employee_id=event.employee_id,
        )
        .aggregate(total=Sum("amount_usd"))["total"]
    )
    return Decimal(str(total or 0))


def _compute_amount(action_type: str, params_model: Any, event: CommissionEvent, ctx: dict[str, Any]) -> tuple[Decimal, str, LineState]:
    from apps.rules import validators as v

    amount = Decimal("0")
    explanation = ""
    state = LineState.PENDING
    base_ccy = (event.company.base_currency or "MXN").upper()

    if action_type == "percent_of_amount":
        p = params_model  # type: v.PercentOfAmountParams
        base = Decimal(str(ctx.get("amount_usd", 0)))
        amount = (base * p.percent / Decimal("100")).quantize(Decimal("0.01"))
        explanation = f"{p.percent}% sobre monto (ref. {base_ccy}) {base} = {amount}"
    elif action_type == "fixed_per_event":
        p = params_model  # type: v.FixedPerEventParams
        amount = p.amount
        explanation = f"Monto fijo por evento: {amount}"
    elif action_type == "tiered_percent":
        p = params_model  # type: v.TieredPercentParams
        base = Decimal(str(ctx.get("amount_usd", 0)))
        pct = Decimal("0")
        for b in sorted(p.brackets, key=lambda x: x.min_amount):
            if base >= b.min_amount and (b.max_amount is None or base <= b.max_amount):
                pct = b.percent
                break
        amount = (base * pct / Decimal("100")).quantize(Decimal("0.01"))
        explanation = f"Tramo: {pct}% sobre {base} {base_ccy} = {amount}"
    elif action_type == "unlock_bonus_if_threshold":
        p = params_model  # type: v.UnlockBonusParams
        base = Decimal(str(ctx.get("amount_usd", 0)))
        if base >= p.threshold_amount:
            amount = p.bonus_amount
            explanation = f"Bono por umbral (>={p.threshold_amount} {base_ccy}): {amount}"
        else:
            explanation = f"Sin bono: monto {base} {base_ccy} < umbral {p.threshold_amount}"
    elif action_type == "fixed_per_client":
        p = params_model  # type: v.FixedPerClientParams
        clients = int(ctx.get("client_count", event.attributes.get("client_count", 1) if isinstance(event.attributes, dict) else 1))
        amount = (p.amount_per_client * Decimal(clients)).quantize(Decimal("0.01"))
        explanation = f"{p.amount_per_client} x {clients} clientes = {amount}"
    elif action_type == "penalty_percent_next_period":
        p = params_model  # type: v.PenaltyNextPeriodParams
        base = Decimal(str(ctx.get("amount_usd", 0)))
        amount = -(base * p.percent / Decimal("100")).quantize(Decimal("0.01"))
        explanation = f"Penalización -{p.percent}% sobre {base} {base_ccy} = {amount}"
    elif action_type == "require_approval":
        p = params_model  # type: v.RequireApprovalParams
        base = Decimal(str(ctx.get("amount_usd", 0)))
        amount = base.quantize(Decimal("0.01")) if base else Decimal("0")
        state = LineState.PENDING_APPROVAL
        explanation = (p.message or "Requiere aprobación") + f" (referencia {amount} {base_ccy})"
    elif action_type == "split_pool_among":
        p = params_model  # type: v.SplitPoolParams
        n = len(p.employee_ids)
        share = (p.pool_amount / Decimal(n)).quantize(Decimal("0.01")) if n else Decimal("0")
        amount = share
        explanation = f"Reparto bolsa {p.pool_amount} entre {n} = {share} c/u"
    elif action_type == "tiered_percent_period_aggregate":
        p = params_model  # type: v.TieredPercentPeriodAggregateParams
        agg = _period_aggregate_for_employee(event)
        pct = Decimal("0")
        matched_bracket = None
        for b in sorted(p.brackets, key=lambda x: x.min_amount, reverse=True):
            if agg >= b.min_amount:
                pct = b.percent
                matched_bracket = b
                break
        base = Decimal(str(ctx.get("amount_usd", 0)))
        amount = (base * pct / Decimal("100")).quantize(Decimal("0.01"))
        min_lbl = matched_bracket.min_amount if matched_bracket else "—"
        explanation = (
            f"Acumulado periodo: {agg} {base_ccy} → tramo >={min_lbl}: "
            f"{pct}% sobre evento {base} {base_ccy} = {amount}"
        )
    elif action_type == "split_pool_among_team":
        pass
    elif action_type == "clawback_if_cancelled_before":
        p = params_model  # type: v.ClawbackIfCancelledBeforeParams
        attrs = event.attributes if isinstance(event.attributes, dict) else {}
        months_active = attrs.get("months_active")
        if months_active is not None and int(months_active) < p.months:
            base = Decimal(str(ctx.get("amount_usd", 0)))
            amount = -(base * p.percent / Decimal("100")).quantize(Decimal("0.01"))
            explanation = (
                f"Clawback: cliente activo {months_active} meses (< {p.months}), "
                f"-{p.percent}% sobre {base} {base_ccy} = {amount}"
            )
        else:
            ma_label = months_active if months_active is not None else "no definido"
            explanation = (
                f"Sin clawback: months_active={ma_label} (umbral {p.months} meses)"
            )
    else:
        explanation = f"Tipo de acción no soportado en cálculo: {action_type}"

    return amount, explanation, state


class CommissionEngine:
    @staticmethod
    @transaction.atomic
    def evaluate(event: CommissionEvent) -> list[CommissionLine]:
        """Evalúa reglas vigentes y crea líneas de comisión para el evento."""
        company = event.company
        ctx = build_context(event)
        base_ccy = (company.base_currency or "MXN").upper()[:3]
        fx_snapshot = resolve_fx_rate_used_for_event(event)

        rules = CommissionRule.objects.filter(company=company, is_active=True).filter(
            Q(project_id__isnull=True) | Q(project_id=event.project_id),
        ).filter(
            Q(team_id__isnull=True) | Q(team_id=event.team_id),
        )
        active_type_ids = ProjectCommissionType.objects.filter(
            project=event.project,
            is_active=True,
        ).values_list("commission_type_id", flat=True)
        rules = rules.filter(commission_type_id__in=active_type_ids)
        if event.commission_type_id:
            rules = rules.filter(commission_type_id=event.commission_type_id)
        resolved_plan_ids = resolve_plan_ids_for_event(event)
        if not resolved_plan_ids:
            rules = rules.none()
        else:
            rules = rules.filter(plan_id__in=resolved_plan_ids)
        rules = rules.select_related("commission_type", "plan").order_by("priority", "id")

        matched: list[CommissionRule] = []
        for rule in rules:
            if not _rule_applies_to_context(rule, event, ctx):
                continue
            matched.append(rule)
            if rule.stop_processing:
                break

        CommissionLine.objects.filter(
            event=event,
            state__in=[LineState.PENDING, LineState.PENDING_APPROVAL],
        ).delete()

        lines: list[CommissionLine] = []
        for rule in matched:
            try:
                params_model = validate_action_params(rule.action_type, rule.action_params or {})
            except Exception as exc:  # noqa: BLE001
                lines.append(
                    CommissionLine.objects.create(
                        company=company,
                        event=event,
                        employee=event.employee,
                        commission_type=rule.commission_type,
                        rule=rule,
                        amount=Decimal("0"),
                        currency=base_ccy,
                        state=LineState.PENDING_APPROVAL,
                        rule_snapshot={
                            "rule_id": rule.id,
                            "action_type": rule.action_type,
                            "error": str(exc),
                        },
                        calculation_explanation=f"Error validando parámetros: {exc}",
                        fx_rate_used=fx_snapshot,
                    )
                )
                continue

            if rule.action_type == "split_pool_among":
                from apps.staff.models import Employee
                from apps.rules.validators import SplitPoolParams

                p = params_model
                if not isinstance(p, SplitPoolParams):
                    lines.append(
                        CommissionLine.objects.create(
                            company=company,
                            event=event,
                            employee=event.employee,
                            commission_type=rule.commission_type,
                            rule=rule,
                            amount=Decimal("0"),
                            currency=base_ccy,
                            state=LineState.PENDING_APPROVAL,
                            rule_snapshot={"error": "split_pool_among params inválidos"},
                            calculation_explanation="Parámetros de reparto inválidos",
                            fx_rate_used=fx_snapshot,
                        )
                    )
                    continue
                n = len(p.employee_ids)
                share = (p.pool_amount / Decimal(n)).quantize(Decimal("0.01")) if n else Decimal("0")
                snapshot = {
                    "rule_id": rule.id,
                    "action_type": rule.action_type,
                    "params": p.model_dump(mode="json"),
                }
                for eid in p.employee_ids:
                    emp = Employee.objects.filter(pk=eid, company=company).first()
                    if not emp:
                        continue
                    lines.append(
                        CommissionLine.objects.create(
                            company=company,
                            event=event,
                            employee=emp,
                            commission_type=rule.commission_type,
                            rule=rule,
                            amount=share,
                            currency=base_ccy,
                            state=LineState.PENDING,
                            rule_snapshot=snapshot,
                            calculation_explanation=f"Reparto bolsa entre {n}: {share}",
                            fx_rate_used=fx_snapshot,
                        )
                    )
                continue

            if rule.action_type == "split_pool_among_team":
                from apps.staff.models import Employee
                from apps.rules.validators import SplitPoolAmongTeamParams

                p = params_model
                if not isinstance(p, SplitPoolAmongTeamParams):
                    lines.append(
                        CommissionLine.objects.create(
                            company=company,
                            event=event,
                            employee=event.employee,
                            commission_type=rule.commission_type,
                            rule=rule,
                            amount=Decimal("0"),
                            currency=base_ccy,
                            state=LineState.PENDING_APPROVAL,
                            rule_snapshot={"error": "split_pool_among_team params inválidos"},
                            calculation_explanation="Parámetros de reparto por equipo inválidos",
                            fx_rate_used=fx_snapshot,
                        )
                    )
                    continue
                team_employees = list(
                    Employee.objects.filter(
                        company=company,
                        is_active=True,
                        employee_teams__team_id=p.team_id,
                    ).distinct()
                )
                n = len(team_employees)
                share = (p.pool_amount / Decimal(n)).quantize(Decimal("0.01")) if n else Decimal("0")
                snapshot = {
                    "rule_id": rule.id,
                    "action_type": rule.action_type,
                    "params": p.model_dump(mode="json"),
                    "resolved_employee_count": n,
                }
                if not team_employees:
                    lines.append(
                        CommissionLine.objects.create(
                            company=company,
                            event=event,
                            employee=event.employee,
                            commission_type=rule.commission_type,
                            rule=rule,
                            amount=Decimal("0"),
                            currency=base_ccy,
                            state=LineState.PENDING_APPROVAL,
                            rule_snapshot=snapshot,
                            calculation_explanation=f"Equipo {p.team_id} sin empleados activos",
                            fx_rate_used=fx_snapshot,
                        )
                    )
                    continue
                for emp in team_employees:
                    lines.append(
                        CommissionLine.objects.create(
                            company=company,
                            event=event,
                            employee=emp,
                            commission_type=rule.commission_type,
                            rule=rule,
                            amount=share,
                            currency=base_ccy,
                            state=LineState.PENDING,
                            rule_snapshot=snapshot,
                            calculation_explanation=f"Reparto equipo ({n} miembros): {share}",
                            fx_rate_used=fx_snapshot,
                        )
                    )
                continue

            amount, explanation, state = _compute_amount(rule.action_type, params_model, event, ctx)
            snapshot = {
                "rule_id": rule.id,
                "action_type": rule.action_type,
                "params": params_model.model_dump(mode="json"),
            }
            lines.append(
                CommissionLine.objects.create(
                    company=company,
                    event=event,
                    employee=event.employee,
                    commission_type=rule.commission_type,
                    rule=rule,
                    amount=amount,
                    currency=base_ccy,
                    state=state,
                    rule_snapshot=snapshot,
                    calculation_explanation=explanation,
                    fx_rate_used=fx_snapshot,
                )
            )

        return lines
