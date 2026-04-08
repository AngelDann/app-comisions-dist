"""Ensamblaje de condiciones desde POST visual."""

from django.test import SimpleTestCase

from apps.rules.condition_builder import build_conditions_from_visual_post, conditions_to_visual_rows
from apps.rules.validators import validate_conditions

# Tipos alineados con build_context (sin tocar BD).
_FDT = {
    "project_id": "number",
    "team_id": "number",
    "event_kind": "string",
    "amount_usd": "number",
    "hours": "number",
    "is_business_hours": "boolean",
    "sales_channel": "string",
    "period_id": "number",
    "client_count": "number",
}


class ConditionBuilderTests(SimpleTestCase):
    def test_empty_visual_is_match_all(self):
        fdt = dict(_FDT)
        c = build_conditions_from_visual_post({}, field_data_types=fdt)
        self.assertEqual(c, {"kind": "group", "op": "AND", "children": []})
        validate_conditions(c)

    def test_single_leaf_and_group(self):
        fdt = dict(_FDT)
        post = {
            "cg_0_l_0_field": "event_kind",
            "cg_0_l_0_op": "eq",
            "cg_0_l_0_value": "sale",
        }
        c = build_conditions_from_visual_post(post, field_data_types=fdt)
        validate_conditions(c)
        self.assertEqual(c["kind"], "group")
        self.assertEqual(c["op"], "AND")
        self.assertEqual(len(c["children"]), 1)
        leaf = c["children"][0]
        self.assertEqual(leaf["kind"], "leaf")
        self.assertEqual(leaf["field"], "event_kind")
        self.assertEqual(leaf["value"], "sale")

    def test_or_of_two_and_groups(self):
        fdt = dict(_FDT)
        post = {
            "cg_0_l_0_field": "event_kind",
            "cg_0_l_0_op": "eq",
            "cg_0_l_0_value": "a",
            "cg_1_l_0_field": "amount_usd",
            "cg_1_l_0_op": "gte",
            "cg_1_l_0_value": "100",
        }
        c = build_conditions_from_visual_post(post, field_data_types=fdt)
        validate_conditions(c)
        self.assertEqual(c["kind"], "group")
        self.assertEqual(c["op"], "OR")
        self.assertEqual(len(c["children"]), 2)

    def test_round_trip_rows(self):
        c = {
            "kind": "group",
            "op": "OR",
            "children": [
                {
                    "kind": "group",
                    "op": "AND",
                    "children": [
                        {"kind": "leaf", "field": "event_kind", "op": "eq", "value": "x"},
                        {"kind": "leaf", "field": "amount_usd", "op": "gte", "value": 1},
                    ],
                },
                {"kind": "leaf", "field": "hours", "op": "lte", "value": 5},
            ],
        }
        rows = conditions_to_visual_rows(c)
        self.assertEqual(len(rows), 2)
        self.assertEqual(len(rows[0]), 2)
        self.assertEqual(len(rows[1]), 1)
