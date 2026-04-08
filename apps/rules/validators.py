"""Validación de action_params por action_type (Pydantic v2)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal, Union

from pydantic import BaseModel, Field, TypeAdapter


class PercentOfAmountParams(BaseModel):
    percent: Decimal = Field(ge=0, le=100)


class FixedPerEventParams(BaseModel):
    amount: Decimal


class TierBracket(BaseModel):
    min_amount: Decimal = Field(ge=0)
    max_amount: Decimal | None = None
    percent: Decimal = Field(ge=0, le=100)


class TieredPercentParams(BaseModel):
    brackets: list[TierBracket] = Field(min_length=1)


class UnlockBonusParams(BaseModel):
    threshold_amount: Decimal = Field(ge=0)
    bonus_amount: Decimal = Field(ge=0)


class SplitPoolParams(BaseModel):
    pool_amount: Decimal = Field(ge=0)
    employee_ids: list[int] = Field(min_length=1)


class PenaltyNextPeriodParams(BaseModel):
    percent: Decimal = Field(ge=0, le=100)


class RequireApprovalParams(BaseModel):
    message: str = ""


class FixedPerClientParams(BaseModel):
    amount_per_client: Decimal = Field(ge=0)


class TieredPercentPeriodAggregateParams(BaseModel):
    """Porcentaje escalonado sobre el acumulado del periodo para el empleado."""

    brackets: list[TierBracket] = Field(min_length=1)


class SplitPoolAmongTeamParams(BaseModel):
    """Reparto de bolsa entre todos los miembros activos de un equipo."""

    pool_amount: Decimal = Field(ge=0)
    team_id: int


class ClawbackIfCancelledBeforeParams(BaseModel):
    """Penalización automática si el cliente cancela antes de N meses."""

    months: int = Field(ge=1)
    percent: Decimal = Field(ge=0, le=100)


ACTION_TYPE_MAP: dict[str, type[BaseModel]] = {
    "percent_of_amount": PercentOfAmountParams,
    "fixed_per_event": FixedPerEventParams,
    "tiered_percent": TieredPercentParams,
    "unlock_bonus_if_threshold": UnlockBonusParams,
    "split_pool_among": SplitPoolParams,
    "penalty_percent_next_period": PenaltyNextPeriodParams,
    "require_approval": RequireApprovalParams,
    "fixed_per_client": FixedPerClientParams,
    "tiered_percent_period_aggregate": TieredPercentPeriodAggregateParams,
    "split_pool_among_team": SplitPoolAmongTeamParams,
    "clawback_if_cancelled_before": ClawbackIfCancelledBeforeParams,
}


def validate_action_params(action_type: str, raw: dict[str, Any]) -> BaseModel:
    model = ACTION_TYPE_MAP.get(action_type)
    if model is None:
        raise ValueError(f"Unknown action_type: {action_type}")
    return model.model_validate(raw)


def action_params_to_dict(model: BaseModel) -> dict[str, Any]:
    return model.model_dump(mode="json")


class ConditionLeaf(BaseModel):
    kind: Literal["leaf"] = "leaf"
    field: str
    op: Literal["eq", "ne", "gte", "lte", "gt", "lt", "in"]
    value: Any


class ConditionGroup(BaseModel):
    kind: Literal["group"] = "group"
    op: Literal["AND", "OR"]
    children: list[Union[ConditionGroup, ConditionLeaf]]


ConditionNode = Union[ConditionGroup, ConditionLeaf]
ConditionNodeAdapter: TypeAdapter[ConditionNode] = TypeAdapter(ConditionNode)


def validate_conditions(data: dict[str, Any]) -> ConditionNode:
    return ConditionNodeAdapter.validate_python(data)
