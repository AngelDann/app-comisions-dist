"""Catálogo de campos disponibles para condiciones de reglas (alineado con build_context)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from apps.rules.models import RuleFieldDefinition


@dataclass(frozen=True)
class ContextFieldSpec:
    key: str
    label: str
    data_type: str  # string | number | boolean | date


# Campos que expone apps.commissions.engine.build_context (y attributes del evento).
BUILTIN_CONTEXT_FIELDS: tuple[ContextFieldSpec, ...] = (
    ContextFieldSpec("project_id", "Proyecto (ID)", "number"),
    ContextFieldSpec("team_id", "Equipo (ID)", "number"),
    ContextFieldSpec("event_kind", "Tipo de evento (código)", "string"),
    ContextFieldSpec("amount_usd", "Monto (referencia en moneda base)", "number"),
    ContextFieldSpec("hours", "Horas", "number"),
    ContextFieldSpec("is_business_hours", "Horario laboral", "boolean"),
    ContextFieldSpec("sales_channel", "Canal de venta", "string"),
    ContextFieldSpec("period_id", "Periodo (ID)", "number"),
    ContextFieldSpec("client_count", "Número de clientes", "number"),
)

OPS_BY_TYPE: dict[str, tuple[tuple[str, str], ...]] = {
    "string": (
        ("eq", "es igual a"),
        ("ne", "no es igual a"),
        ("in", "está en (lista)"),
    ),
    "number": (
        ("eq", "es igual a"),
        ("ne", "no es igual a"),
        ("gte", "mayor o igual"),
        ("lte", "menor o igual"),
        ("gt", "mayor que"),
        ("lt", "menor que"),
        ("in", "está en (lista)"),
    ),
    "boolean": (("eq", "es"), ("ne", "no es")),
    "date": (
        ("eq", "es igual a"),
        ("ne", "no es igual a"),
        ("gte", "mayor o igual"),
        ("lte", "menor o igual"),
        ("gt", "después de"),
        ("lt", "antes de"),
    ),
}

DEFAULT_OPS = OPS_BY_TYPE["string"]

ALL_OPERATOR_CHOICES: tuple[tuple[str, str], ...] = (
    ("eq", "es igual a"),
    ("ne", "no es igual a"),
    ("gte", "mayor o igual"),
    ("lte", "menor o igual"),
    ("gt", "mayor que"),
    ("lt", "menor que"),
    ("in", "está en (lista separada por comas)"),
)


def ops_for_field(data_type: str) -> tuple[tuple[str, str], ...]:
    return OPS_BY_TYPE.get(data_type, DEFAULT_OPS)


def merged_field_specs(company_id: int) -> list[dict[str, Any]]:
    """Lista de dicts {key, label, data_type} para selects: built-in + RuleFieldDefinition."""
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for s in BUILTIN_CONTEXT_FIELDS:
        out.append({"key": s.key, "label": s.label, "data_type": s.data_type})
        seen.add(s.key)
    for row in RuleFieldDefinition.objects.filter(company_id=company_id).order_by("key"):
        if row.key in seen:
            continue
        out.append({"key": row.key, "label": row.label, "data_type": row.data_type})
        seen.add(row.key)
    return out


def spec_by_key(company_id: int) -> dict[str, dict[str, Any]]:
    return {s["key"]: s for s in merged_field_specs(company_id)}
