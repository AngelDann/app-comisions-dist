import json

from django import forms
from django.http import HttpResponse, HttpResponseForbidden, QueryDict
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from apps.accounts.decorators import company_admin_required, login_and_company_required
from apps.commissions.date_fields import bind_iso_html_dates
from apps.accounts.permissions import (
    applies_adjustment_self_only_scope,
    filter_commission_events_for_adjustment_form,
    filter_commission_lines_for_adjustment_form,
    is_company_commission_auditor,
    sees_all_company_commissions,
    user_team_lead_ids,
)
from apps.commissions.models import Adjustment, AdjustmentKind, CommissionLine, LineState
from apps.rules.action_params_forms import (
    ACTION_TYPE_MAP,
    action_type_choices,
    build_action_params_from_post,
    initial_from_action_params,
)
from apps.rules.condition_builder import (
    build_conditions_from_visual_post,
    pretty_conditions_json,
    visual_rows_from_conditions,
    visual_rows_from_post,
)
from apps.rules.field_catalog import ALL_OPERATOR_CHOICES, merged_field_specs, ops_for_field, spec_by_key
from apps.rules.models import CommissionPlan, CommissionRule
from apps.rules.validators import action_params_to_dict, validate_action_params, validate_conditions


class AdjustmentForm(forms.ModelForm):
    class Meta:
        model = Adjustment
        fields = ["line", "event", "kind", "amount", "reason"]
        labels = {
            "line": "Línea",
            "event": "Evento",
            "kind": "Tipo",
            "amount": "Importe",
            "reason": "Motivo",
        }

    def __init__(self, *args, company=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._company = company
        self._user = user
        from apps.commissions.models import CommissionEvent

        lines = CommissionLine.objects.filter(company=company).select_related(
            "event",
            "employee",
        )
        lines = filter_commission_lines_for_adjustment_form(lines, user, company)
        evs = filter_commission_events_for_adjustment_form(
            CommissionEvent.objects.filter(company=company).select_related(
                "employee",
                "project",
                "period",
            ),
            user,
            company,
        )
        self.fields["line"].queryset = lines
        self.fields["event"].queryset = evs
        self.fields["line"].required = False
        self.fields["event"].required = False
        for f in self.fields.values():
            f.widget.attrs.setdefault("class", "form-select" if isinstance(f.widget, forms.Select) else "form-control")
        self.fields["reason"].widget.attrs["rows"] = 2

    def clean(self):
        data = super().clean()
        line = data.get("line")
        event = data.get("event")
        if not line and not event:
            raise forms.ValidationError("Indica una línea o un evento.")
        if line and event:
            raise forms.ValidationError(
                "Elige solo uno: la línea o el evento, no ambos. "
                "La línea ya está ligada a su evento; mezclar dos objetivos distintos no es válido."
            )
        return data

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.company = self._company
        obj.created_by = self._user
        if commit:
            obj.save()
        return obj


class CommissionRuleForm(forms.ModelForm):
    conditions_json = forms.CharField(
        label="Condiciones (JSON)",
        required=False,
        widget=forms.Textarea(
            attrs={"rows": 8, "class": "form-control font-monospace small", "spellcheck": "false"}
        ),
        help_text="Modo avanzado: árbol kind/group/leaf. En modo visual se genera al guardar.",
    )
    action_params_json = forms.CharField(
        label="Parámetros de acción (JSON)",
        required=False,
        widget=forms.Textarea(
            attrs={"rows": 6, "class": "form-control font-monospace small", "spellcheck": "false"}
        ),
    )

    class Meta:
        model = CommissionRule
        fields = [
            "name",
            "project",
            "team",
            "commission_type",
            "priority",
            "valid_from",
            "valid_to",
            "action_type",
            "stop_processing",
            "is_active",
        ]
        widgets = {
            # DateField: selector nativo del navegador (calendario). Formato ISO requerido por input type="date".
            "valid_from": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"type": "date"},
            ),
            "valid_to": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"type": "date"},
            ),
        }

    def __init__(self, *args, company=None, lock_plan: CommissionPlan, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.company = company
        self._lock_plan = lock_plan
        self._company = company
        from apps.commissions.models import CommissionType
        from apps.projects.models import Project, Team

        self.fields["project"].queryset = Project.objects.filter(company=company, is_active=True)
        self.fields["team"].queryset = Team.objects.filter(company=company, is_active=True)
        self.fields["commission_type"].queryset = CommissionType.objects.filter(company=company)
        # CharField del modelo no enlaza choices al Select al pintar opciones; usar ChoiceField.
        at_choices = action_type_choices()
        prev = self.fields["action_type"]
        self.fields["action_type"] = forms.TypedChoiceField(
            coerce=str,
            choices=at_choices,
            required=True,
            label=prev.label,
            widget=forms.Select(
                choices=at_choices,
                attrs={
                    "class": "form-select",
                    "id": "id_action_type",
                    "hx-get": reverse("commissions:rule_action_fields_partial"),
                    "hx-trigger": "change",
                    "hx-target": "#action-params-fields",
                    "hx-swap": "innerHTML",
                },
            ),
        )
        # Preserve instance value when replacing the model-backed field at runtime.
        if self.instance.pk and self.instance.action_type:
            self.initial["action_type"] = self.instance.action_type
            self.fields["action_type"].initial = self.instance.action_type
        for n, f in self.fields.items():
            if n in ("conditions_json", "action_params_json"):
                continue
            if isinstance(f.widget, forms.Select) and n != "action_type":
                f.widget.attrs.setdefault("class", "form-select")
            elif isinstance(f.widget, forms.CheckboxInput):
                f.widget.attrs.setdefault("class", "form-check-input")
            else:
                f.widget.attrs.setdefault("class", "form-control")

        default_cond = {"kind": "group", "op": "AND", "children": []}
        cond = self.instance.conditions if self.instance.pk else default_cond
        if not cond:
            cond = default_cond
        self.fields["conditions_json"].initial = pretty_conditions_json(cond)

        ap = self.instance.action_params if self.instance.pk else {}
        if not self.instance.pk:
            ap = {"percent": "20"}
        self.fields["action_params_json"].initial = json.dumps(ap, ensure_ascii=False, indent=2)
        if not self.instance.pk:
            self.initial.setdefault("action_type", "percent_of_amount")

        bind_iso_html_dates(self, "valid_from", "valid_to")
        for name in ("valid_from", "valid_to"):
            self.fields[name].widget.attrs.setdefault("class", "form-control")
            self.fields[name].required = False

    def clean(self):
        super().clean()
        data = self.cleaned_data
        company = self._company
        cond_mode = (self.data.get("conditions_editor_mode") or "visual").strip()
        act_mode = (self.data.get("action_params_editor_mode") or "structured").strip()

        if cond_mode == "advanced":
            c_raw = data.get("conditions_json") or "{}"
            try:
                cond = json.loads(c_raw)
            except json.JSONDecodeError as exc:
                self.add_error("conditions_json", f"JSON inválido: {exc}")
                return data
        else:
            ftypes = {k: v["data_type"] for k, v in spec_by_key(company.pk).items()}
            cond = build_conditions_from_visual_post(self.data, field_data_types=ftypes)

        try:
            validate_conditions(cond)
        except Exception as exc:  # noqa: BLE001
            self.add_error("conditions_json", str(exc))
            return data

        at = data.get("action_type") or (self.instance.action_type if self.instance.pk else None)
        if act_mode == "advanced":
            p_raw = data.get("action_params_json") or "{}"
            try:
                params = json.loads(p_raw)
            except json.JSONDecodeError as exc:
                self.add_error("action_params_json", f"JSON inválido: {exc}")
                return data
        else:
            if not at:
                self.add_error("action_type", "Selecciona un tipo de acción.")
                return data
            try:
                params = build_action_params_from_post(at, self.data)
            except forms.ValidationError as exc:
                msgs = getattr(exc, "messages", None) or [str(exc)]
                self.add_error("action_params_json", " ".join(str(m) for m in msgs))
                return data
            except ValueError as exc:
                self.add_error("action_params_json", str(exc))
                return data

        if at:
            try:
                params_model = validate_action_params(at, params)
                params = action_params_to_dict(params_model)
            except Exception as exc:  # noqa: BLE001
                self.add_error("action_params_json", str(exc))
                return data

        self._parsed_conditions = cond
        self._parsed_action_params = params
        return data

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.plan = self._lock_plan
        obj.conditions = getattr(self, "_parsed_conditions", self.instance.conditions or {})
        obj.action_params = getattr(self, "_parsed_action_params", self.instance.action_params or {})
        if commit:
            obj.save()
        return obj


def _c(request):
    return request.company


def _can_set_line_state(request, line: CommissionLine) -> bool:
    company = _c(request)
    if is_company_commission_auditor(request.user, company):
        return False
    tid = line.event.team_id
    if sees_all_company_commissions(request.user, company):
        return True
    return tid in user_team_lead_ids(request.user, company)


@login_and_company_required
@require_POST
def line_set_state(request, pk: int, state: str):
    company = _c(request)
    line = get_object_or_404(CommissionLine, pk=pk, company=company)
    if not _can_set_line_state(request, line):
        return HttpResponseForbidden()
    if state not in (LineState.APPROVED, LineState.REJECTED, LineState.PENDING):
        return HttpResponseForbidden()
    line.state = state
    line.save(update_fields=["state"])
    next_url = request.POST.get("next") or ""
    if next_url.startswith("/") and not next_url.startswith("//"):
        return redirect(next_url)
    from django.urls import reverse

    return redirect(reverse("commissions:employee_summary"))


@login_and_company_required
def adjustment_create(request):
    company = _c(request)
    user = request.user
    if is_company_commission_auditor(user, company):
        return HttpResponseForbidden("Los auditores no pueden registrar ajustes.")
    if request.method == "POST":
        form = AdjustmentForm(request.POST, company=company, user=user)
        if form.is_valid():
            adj = form.save(commit=False)
            if adj.line_id:
                if not filter_commission_lines_for_adjustment_form(
                    CommissionLine.objects.filter(pk=adj.line_id), user, company
                ).exists():
                    return HttpResponseForbidden()
            if adj.event_id:
                from apps.commissions.models import CommissionEvent

                if not filter_commission_events_for_adjustment_form(
                    CommissionEvent.objects.filter(pk=adj.event_id), user, company
                ).exists():
                    return HttpResponseForbidden()
            adj.save()
            return redirect("commissions:adjustments_list")
    else:
        form = AdjustmentForm(company=company, user=user)
    return render(
        request,
        "commissions/adjustment_form.html",
        {
            "form": form,
            "adjustment_self_only": applies_adjustment_self_only_scope(user, company),
        },
    )


def _rule_redirect_after_save(rule: CommissionRule):
    return redirect(reverse("commissions:plan_detail", kwargs={"pk": rule.plan_id}))


def _condition_groups_for_template(request, form: CommissionRuleForm) -> tuple[list[list[dict]], bool]:
    if request.method == "POST" and getattr(form, "data", None):
        mode = (form.data.get("conditions_editor_mode") or "visual").strip()
        if mode == "visual":
            return visual_rows_from_post(form.data), True
        try:
            c = json.loads(form.data.get("conditions_json") or "{}")
        except json.JSONDecodeError:
            return [[]], False
        return visual_rows_from_conditions(c)

    cond: dict = {"kind": "group", "op": "AND", "children": []}
    if form.instance.pk and isinstance(form.instance.conditions, dict) and form.instance.conditions:
        cond = form.instance.conditions
    return visual_rows_from_conditions(cond)


def _action_type_selected(request, form: CommissionRuleForm) -> str:
    if request.method == "POST" and form.data.get("action_type"):
        return form.data.get("action_type")  # type: ignore[return-value]
    if form.instance.pk and form.instance.action_type:
        return form.instance.action_type
    return "percent_of_amount"


def _action_initial_for_page(request, form: CommissionRuleForm) -> dict:
    at = _action_type_selected(request, form)
    if form.instance.pk:
        params = form.instance.action_params or {}
    else:
        from decimal import Decimal

        params = {"percent": Decimal("20")}
    return initial_from_action_params(at, params)


def _tier_display_rows(
    indices: list[int],
    initial: dict,
    repop: QueryDict | None,
) -> list[dict[str, str | int]]:
    rows: list[dict[str, str | int]] = []
    brackets = list(initial.get("brackets") or [])
    getv = (lambda k: repop.get(k, "")) if repop is not None else None
    for i in indices:
        row: dict[str, str | int] = {"i": i, "min": "", "max": "", "percent": ""}
        if getv is not None:
            row["min"] = str(getv(f"ap_tier_{i}_min") or "")
            row["max"] = str(getv(f"ap_tier_{i}_max") or "")
            row["percent"] = str(getv(f"ap_tier_{i}_percent") or "")
        elif i < len(brackets):
            b = brackets[i]
            row["min"] = str(b.get("min_amount", "") or "")
            mx = b.get("max_amount")
            row["max"] = "" if mx is None else str(mx)
            row["percent"] = str(b.get("percent", "") or "")
        rows.append(row)
    return rows


def _tier_row_indices(request, form: CommissionRuleForm) -> list[int]:
    import re

    r = re.compile(r"^ap_tier_(\d+)_min$")
    if request.method == "POST" and form.errors and form.data:
        idx = [int(m.group(1)) for k in form.data for m in [r.match(k)] if m]
        return sorted(set(idx)) if idx else [0]
    at = _action_type_selected(request, form)
    if at != "tiered_percent":
        return [0]
    init = _action_initial_for_page(request, form)
    brackets = init.get("brackets") or []
    return list(range(max(len(brackets), 1)))


def _conditions_preview_json(request, form: CommissionRuleForm) -> str:
    company = form._company
    mode = (form.data.get("conditions_editor_mode") or "visual").strip() if getattr(form, "data", None) else "visual"
    if request.method == "POST" and form.data:
        if mode == "visual":
            fdt = {k: v["data_type"] for k, v in spec_by_key(company.pk).items()}
            c = build_conditions_from_visual_post(form.data, field_data_types=fdt)
            return pretty_conditions_json(c)
        return (form.data.get("conditions_json") or "").strip() or "{}"
    cond: dict = {"kind": "group", "op": "AND", "children": []}
    if form.instance.pk and isinstance(form.instance.conditions, dict) and form.instance.conditions:
        cond = form.instance.conditions
    return pretty_conditions_json(cond)


def _rule_form_page_context(request, form: CommissionRuleForm, lock_plan: CommissionPlan) -> dict:
    company = lock_plan.company
    cg, cv_ok = _condition_groups_for_template(request, form)
    field_specs = [
        {**s, "ops": ops_for_field(s["data_type"])} for s in merged_field_specs(company.pk)
    ]
    ap_repop = request.POST if request.method == "POST" and form.errors else None
    at_sel = _action_type_selected(request, form)
    action_initial = _action_initial_for_page(request, form)
    tidx = _tier_row_indices(request, form)
    return {
        "field_specs": field_specs,
        "condition_groups": cg,
        "conditions_visual_ok": cv_ok,
        "action_type_selected": at_sel,
        "action_initial": action_initial,
        "tier_row_indices": tidx,
        "tier_display_rows": _tier_display_rows(tidx, action_initial, ap_repop),
        "ap_repop": ap_repop,
        "conditions_preview_json": _conditions_preview_json(request, form),
        "all_operator_choices": ALL_OPERATOR_CHOICES,
    }


@company_admin_required
@require_GET
def rule_action_fields_partial(request):
    """HTMX: cuerpo de campos según action_type (GET incluye query del select)."""
    action_type = request.GET.get("action_type") or "percent_of_amount"
    if action_type not in ACTION_TYPE_MAP:
        action_type = "percent_of_amount"
    initial = initial_from_action_params(action_type, {})
    if action_type == "percent_of_amount":
        p = request.GET.get("percent")
        if p is not None and p != "":
            initial["percent"] = p
    if action_type == "fixed_per_event" and request.GET.get("amount"):
        initial["amount"] = request.GET.get("amount")
    tier_row_indices = [0]
    if action_type == "tiered_percent":
        brackets = initial.get("brackets") or []
        tier_row_indices = list(range(max(len(brackets), 1)))
    tier_display_rows = _tier_display_rows(tier_row_indices, initial, None)
    html = render_to_string(
        "commissions/partials/rule_action_fields.html",
        {
            "action_type": action_type,
            "initial": initial,
            "repop": None,
            "tier_row_indices": tier_row_indices,
            "tier_display_rows": tier_display_rows,
        },
        request=request,
    )
    return HttpResponse(html)


@company_admin_required
def rule_create(request):
    company = _c(request)
    lock_plan = None
    raw_plan = request.GET.get("plan")
    if raw_plan:
        try:
            lock_plan = get_object_or_404(CommissionPlan, pk=int(raw_plan), company=company)
        except ValueError:
            lock_plan = None
    if lock_plan is None:
        return redirect("commissions:plan_list")
    if request.method == "POST":
        form = CommissionRuleForm(request.POST, company=company, lock_plan=lock_plan)
        if form.is_valid():
            rule = form.save()
            return _rule_redirect_after_save(rule)
    else:
        form = CommissionRuleForm(company=company, lock_plan=lock_plan)
    ctx = {
        "form": form,
        "title": "Nueva regla",
        "lock_plan": lock_plan,
    }
    ctx.update(_rule_form_page_context(request, form, lock_plan))
    return render(request, "commissions/rule_form.html", ctx)


@company_admin_required
def rule_edit(request, pk: int):
    company = _c(request)
    rule = get_object_or_404(CommissionRule, pk=pk, company=company)
    lock_plan = rule.plan
    if request.method == "POST":
        form = CommissionRuleForm(request.POST, instance=rule, company=company, lock_plan=lock_plan)
        if form.is_valid():
            form.save()
            return _rule_redirect_after_save(rule)
    else:
        form = CommissionRuleForm(instance=rule, company=company, lock_plan=lock_plan)
    ctx = {
        "form": form,
        "title": f"Editar {rule.name}",
        "lock_plan": lock_plan,
    }
    ctx.update(_rule_form_page_context(request, form, lock_plan))
    return render(request, "commissions/rule_form.html", ctx)


@company_admin_required
@require_POST
def rule_delete(request, pk: int):
    company = _c(request)
    rule = get_object_or_404(CommissionRule, pk=pk, company=company)
    plan_pk = rule.plan_id
    rule.delete()
    return redirect(reverse("commissions:plan_detail", kwargs={"pk": plan_pk}))
