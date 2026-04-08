"""Ensamblar / parsear árbol de condiciones para el formulario visual (OR de grupos AND)."""

from __future__ import annotations

import json
import re
from typing import Any

from apps.rules.validators import validate_conditions

# POST: cg_{g}_l_{i}_field, cg_{g}_l_{i}_op, cg_{g}_l_{i}_value
CG_L_RE = re.compile(r"^cg_(\d+)_l_(\d+)_(field|op|value)$")


def _parse_value(op: str, raw: str, *, data_type: str) -> Any:
    raw = (raw or "").strip()
    if op == "in":
        if not raw:
            return []
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        if data_type == "number":
            out: list[Any] = []
            for p in parts:
                try:
                    if "." in p:
                        out.append(float(p))
                    else:
                        out.append(int(p))
                except ValueError:
                    out.append(p)
            return out
        return parts
    if data_type == "boolean":
        return raw.lower() in ("1", "true", "yes", "sí", "si", "on")
    if data_type == "number" and raw:
        try:
            return float(raw) if "." in raw else int(raw)
        except ValueError:
            return raw
    return raw


def build_conditions_from_visual_post(
    post: dict[str, Any],
    *,
    field_data_types: dict[str, str],
) -> dict[str, Any]:
    """Lee claves cg_* del POST y produce JSON de condiciones."""
    buckets: dict[int, dict[int, dict[str, str]]] = {}
    for key, val in post.items():
        m = CG_L_RE.match(key)
        if not m:
            continue
        g, i, part = int(m.group(1)), int(m.group(2)), m.group(3)
        buckets.setdefault(g, {}).setdefault(i, {})[part] = val if isinstance(val, str) else str(val)

    or_children: list[dict[str, Any]] = []
    for g in sorted(buckets.keys()):
        leaves: list[dict[str, Any]] = []
        for i in sorted(buckets[g].keys()):
            cell = buckets[g][i]
            field = (cell.get("field") or "").strip()
            op = (cell.get("op") or "eq").strip()
            raw_val = cell.get("value", "")
            if not field:
                continue
            dt = field_data_types.get(field, "string")
            value = _parse_value(op, raw_val, data_type=dt)
            if op == "in" and value == []:
                continue
            leaves.append({"kind": "leaf", "field": field, "op": op, "value": value})
        if leaves:
            if len(leaves) == 1:
                or_children.append(leaves[0])
            else:
                or_children.append({"kind": "group", "op": "AND", "children": leaves})

    if not or_children:
        return {"kind": "group", "op": "AND", "children": []}
    if len(or_children) == 1:
        node = or_children[0]
        if node.get("kind") == "leaf":
            return {"kind": "group", "op": "AND", "children": [node]}
        return node
    return {"kind": "group", "op": "OR", "children": or_children}


class UnsupportedConditionShape(Exception):
    pass


def conditions_to_visual_rows(conditions: dict[str, Any] | None) -> list[list[dict[str, Any]]]:
    """
    Convierte condiciones guardadas en lista de grupos OR, cada uno lista de hojas {field, op, value_str}.
    value_str es representación para el input (lista 'in' como comma-separated).
    """
    if not conditions or not isinstance(conditions, dict):
        return [[]]

    kind = conditions.get("kind")
    if kind == "leaf":
        return [[_leaf_to_row(conditions)]]

    if kind != "group":
        raise UnsupportedConditionShape()

    op = conditions.get("op")
    children = conditions.get("children") or []

    if op == "AND" and not children:
        return [[]]

    if op == "AND":
        rows: list[dict[str, Any]] = []
        for ch in children:
            if not isinstance(ch, dict) or ch.get("kind") != "leaf":
                raise UnsupportedConditionShape()
            rows.append(_leaf_to_row(ch))
        return [rows]

    if op == "OR":
        groups: list[list[dict[str, Any]]] = []
        for ch in children:
            if not isinstance(ch, dict):
                raise UnsupportedConditionShape()
            if ch.get("kind") == "leaf":
                groups.append([_leaf_to_row(ch)])
            elif ch.get("kind") == "group" and ch.get("op") == "AND":
                inner = ch.get("children") or []
                r2: list[dict[str, Any]] = []
                for leaf in inner:
                    if not isinstance(leaf, dict) or leaf.get("kind") != "leaf":
                        raise UnsupportedConditionShape()
                    r2.append(_leaf_to_row(leaf))
                groups.append(r2)
            else:
                raise UnsupportedConditionShape()
        return groups if groups else [[]]

    raise UnsupportedConditionShape()


def _leaf_to_row(leaf: dict[str, Any]) -> dict[str, Any]:
    op = leaf.get("op") or "eq"
    val = leaf.get("value")
    if op == "in" and isinstance(val, (list, tuple)):
        value_str = ", ".join(str(x) for x in val)
    else:
        value_str = "" if val is None else str(val)
        if isinstance(val, bool):
            value_str = "true" if val else "false"
    return {
        "field": leaf.get("field") or "",
        "op": op,
        "value_str": value_str,
    }


def visual_rows_from_conditions(conditions: dict[str, Any] | None) -> tuple[list[list[dict[str, Any]]], bool]:
    """
    Retorna (rows, ok). Si ok es False, el árbol no es editable en modo visual; usar solo JSON avanzado.
    """
    data = conditions if isinstance(conditions, dict) else {}
    if not data:
        data = {"kind": "group", "op": "AND", "children": []}
    try:
        validate_conditions(data)
    except Exception:
        return [[]], False
    try:
        rows = conditions_to_visual_rows(data)
        return rows, True
    except UnsupportedConditionShape:
        return [[]], False


def pretty_conditions_json(conditions: dict[str, Any]) -> str:
    return json.dumps(conditions or {}, ensure_ascii=False, indent=2)


def visual_rows_from_post(post: dict[str, Any]) -> list[list[dict[str, Any]]]:
    """Reconstruye filas del UI desde POST (mismas claves cg_*), para repoblar tras error de validación."""
    buckets: dict[int, dict[int, dict[str, str]]] = {}
    for key, val in post.items():
        m = CG_L_RE.match(key)
        if not m:
            continue
        g, i, part = int(m.group(1)), int(m.group(2)), m.group(3)
        buckets.setdefault(g, {}).setdefault(i, {})[part] = val if isinstance(val, str) else str(val)

    rows: list[list[dict[str, Any]]] = []
    for g in sorted(buckets.keys()):
        group_rows: list[dict[str, Any]] = []
        for i in sorted(buckets[g].keys()):
            cell = buckets[g][i]
            field = (cell.get("field") or "").strip()
            if not field:
                continue
            group_rows.append(
                {
                    "field": field,
                    "op": (cell.get("op") or "eq").strip(),
                    "value_str": (cell.get("value") or "").strip(),
                }
            )
        rows.append(group_rows)
    return rows if rows else [[]]
