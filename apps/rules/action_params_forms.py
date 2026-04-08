"""Formularios Django para action_params por action_type (serializan a dict validado por Pydantic)."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any

from django import forms

from apps.rules.validators import ACTION_TYPE_MAP, validate_action_params

AP_TIER_RE = re.compile(r"^ap_tier_(\d+)_min$")


class PercentOfAmountActionForm(forms.Form):
    percent = forms.DecimalField(
        label="Porcentaje",
        min_value=Decimal("0"),
        max_value=Decimal("100"),
        max_digits=7,
        decimal_places=4,
    )


class FixedPerEventActionForm(forms.Form):
    amount = forms.DecimalField(label="Monto fijo", min_value=Decimal("0"), max_digits=14, decimal_places=4)


class UnlockBonusActionForm(forms.Form):
    threshold_amount = forms.DecimalField(
        label="Umbral de monto",
        min_value=Decimal("0"),
        max_digits=14,
        decimal_places=4,
    )
    bonus_amount = forms.DecimalField(
        label="Monto del bono",
        min_value=Decimal("0"),
        max_digits=14,
        decimal_places=4,
    )


class SplitPoolActionForm(forms.Form):
    pool_amount = forms.DecimalField(
        label="Monto total de la bolsa",
        min_value=Decimal("0"),
        max_digits=14,
        decimal_places=4,
    )
    employee_ids = forms.CharField(
        label="IDs de empleados (separados por coma)",
        widget=forms.TextInput(attrs={"placeholder": "1, 2, 3"}),
    )

    def clean_employee_ids(self):
        raw = self.cleaned_data.get("employee_ids") or ""
        ids: list[int] = []
        for part in raw.replace(";", ",").split(","):
            part = part.strip()
            if not part:
                continue
            try:
                ids.append(int(part))
            except ValueError as exc:
                raise forms.ValidationError(f"ID inválido: {part}") from exc
        if not ids:
            raise forms.ValidationError("Indica al menos un ID de empleado.")
        return ids

    def clean(self):
        data = super().clean()
        if "employee_ids" in data and isinstance(data["employee_ids"], list):
            data["employee_ids"] = data["employee_ids"]
        return data


class PenaltyNextPeriodActionForm(forms.Form):
    percent = forms.DecimalField(
        label="Porcentaje de penalización",
        min_value=Decimal("0"),
        max_value=Decimal("100"),
        max_digits=7,
        decimal_places=4,
    )


class RequireApprovalActionForm(forms.Form):
    message = forms.CharField(label="Mensaje", required=False, widget=forms.Textarea(attrs={"rows": 2}))


class FixedPerClientActionForm(forms.Form):
    amount_per_client = forms.DecimalField(
        label="Monto por cliente",
        min_value=Decimal("0"),
        max_digits=14,
        decimal_places=4,
    )


class SplitPoolAmongTeamActionForm(forms.Form):
    pool_amount = forms.DecimalField(
        label="Monto total de la bolsa",
        min_value=Decimal("0"),
        max_digits=14,
        decimal_places=4,
    )
    team_id = forms.IntegerField(
        label="ID del equipo",
        min_value=1,
    )


class ClawbackIfCancelledBeforeActionForm(forms.Form):
    months = forms.IntegerField(
        label="Meses mínimos de permanencia",
        min_value=1,
    )
    percent = forms.DecimalField(
        label="Porcentaje a descontar",
        min_value=Decimal("0"),
        max_value=Decimal("100"),
        max_digits=7,
        decimal_places=4,
    )


ACTION_FORM_CLASSES: dict[str, type[forms.Form]] = {
    "percent_of_amount": PercentOfAmountActionForm,
    "fixed_per_event": FixedPerEventActionForm,
    "unlock_bonus_if_threshold": UnlockBonusActionForm,
    "split_pool_among": SplitPoolActionForm,
    "penalty_percent_next_period": PenaltyNextPeriodActionForm,
    "require_approval": RequireApprovalActionForm,
    "fixed_per_client": FixedPerClientActionForm,
    "split_pool_among_team": SplitPoolAmongTeamActionForm,
    "clawback_if_cancelled_before": ClawbackIfCancelledBeforeActionForm,
}


def parse_tiered_brackets_from_post(post: dict[str, Any]) -> list[dict[str, Any]]:
    indices: set[int] = set()
    for key in post:
        m = AP_TIER_RE.match(key)
        if m:
            indices.add(int(m.group(1)))
    brackets: list[dict[str, Any]] = []
    for i in sorted(indices):
        prefix = f"ap_tier_{i}_"
        min_raw = (post.get(prefix + "min") or "").strip()
        max_raw = (post.get(prefix + "max") or "").strip()
        pct_raw = (post.get(prefix + "percent") or "").strip()
        if not min_raw and not max_raw and not pct_raw:
            continue
        try:
            min_amount = Decimal(min_raw or "0")
        except InvalidOperation as exc:
            raise forms.ValidationError(f"Tramo {i + 1}: mínimo inválido") from exc
        max_amount: Decimal | None
        if max_raw:
            try:
                max_amount = Decimal(max_raw)
            except InvalidOperation as exc:
                raise forms.ValidationError(f"Tramo {i + 1}: máximo inválido") from exc
        else:
            max_amount = None
        try:
            percent = Decimal(pct_raw)
        except InvalidOperation as exc:
            raise forms.ValidationError(f"Tramo {i + 1}: porcentaje inválido") from exc
        d: dict[str, Any] = {"min_amount": min_amount, "percent": percent}
        if max_amount is not None:
            d["max_amount"] = max_amount
        brackets.append(d)
    return brackets


def build_action_params_from_post(action_type: str, post: dict[str, Any]) -> dict[str, Any]:
    """Construye dict listo para validate_action_params desde POST modo estructurado."""
    if action_type in ("tiered_percent", "tiered_percent_period_aggregate"):
        brackets = parse_tiered_brackets_from_post(post)
        if not brackets:
            raise forms.ValidationError("Añade al menos un tramo con mínimo y porcentaje.")
        raw = {"brackets": brackets}
        validate_action_params(action_type, raw)
        return raw

    form_cls = ACTION_FORM_CLASSES.get(action_type)
    if form_cls is None:
        raise ValueError(f"Sin formulario estructurado para action_type={action_type}")

    form = form_cls(data=post)
    if not form.is_valid():
        parts = []
        for field, errs in form.errors.items():
            parts.append(f"{field}: {', '.join(str(e) for e in errs)}")
        raise forms.ValidationError("; ".join(parts))
    cleaned = form.cleaned_data
    if action_type == "split_pool_among":
        return {"pool_amount": cleaned["pool_amount"], "employee_ids": cleaned["employee_ids"]}
    if action_type == "require_approval":
        return {"message": cleaned.get("message") or ""}
    return dict(cleaned)


def initial_from_action_params(action_type: str, params: dict[str, Any]) -> dict[str, Any]:
    """Valores iniciales para repoblar formularios / partial."""
    if not params:
        return {}
    if action_type in ("tiered_percent", "tiered_percent_period_aggregate"):
        return {"brackets": params.get("brackets") or []}
    if action_type == "split_pool_among":
        ids = params.get("employee_ids") or []
        return {
            "pool_amount": params.get("pool_amount"),
            "employee_ids": ", ".join(str(x) for x in ids),
        }
    if action_type == "require_approval":
        return {"message": params.get("message") or ""}
    return dict(params)


def action_type_choices() -> list[tuple[str, str]]:
    labels = {
        "percent_of_amount": "Porcentaje sobre monto",
        "fixed_per_event": "Monto fijo por evento",
        "tiered_percent": "Porcentaje por tramos",
        "unlock_bonus_if_threshold": "Bono si alcanza umbral",
        "split_pool_among": "Repartir bolsa entre empleados",
        "penalty_percent_next_period": "Penalización % (siguiente periodo)",
        "require_approval": "Requiere aprobación",
        "fixed_per_client": "Monto fijo por cliente",
        "tiered_percent_period_aggregate": "% por tramos (acumulado del periodo)",
        "split_pool_among_team": "Repartir bolsa entre equipo",
        "clawback_if_cancelled_before": "Clawback por cancelación anticipada",
    }
    return [(k, labels.get(k, k)) for k in ACTION_TYPE_MAP]
