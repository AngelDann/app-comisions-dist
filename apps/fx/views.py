from decimal import Decimal, InvalidOperation

from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.accounts.decorators import company_admin_required, login_and_company_required
from apps.fx.models import FxRate


def _fx_template_context(company, rates):
    """Contexto común para listado y parciales HTMX de tipos de cambio."""
    base = (getattr(company, "base_currency", None) or "MXN").upper()
    return {
        "rates": rates,
        "default_rate_date": timezone.now().date().isoformat(),
        "base_currency": base,
    }


@login_and_company_required
def fx_list(request):
    company = request.company
    rates = FxRate.objects.filter(company=company).order_by("-rate_date", "currency_code")[:200]
    return render(request, "fx/list.html", _fx_template_context(company, rates))


@login_and_company_required
@company_admin_required
@require_POST
def fx_create(request):
    company = request.company
    code = (request.POST.get("currency_code") or "USD").upper()[:3]
    date = request.POST.get("rate_date")
    raw = request.POST.get("value")
    try:
        value = Decimal(raw)
    except (InvalidOperation, TypeError):
        return render(
            request,
            "partials/field_feedback.html",
            {"ok": False, "message": "Valor inválido"},
            status=400,
        )
    FxRate.objects.update_or_create(
        company=company,
        currency_code=code,
        rate_date=date,
        defaults={"value": value, "source": "manual"},
    )
    rates = FxRate.objects.filter(company=company).order_by("-rate_date", "currency_code")[:200]
    if request.headers.get("HX-Request"):
        return render(
            request,
            "fx/partials/rates_table.html",
            _fx_template_context(company, rates),
        )
    return render(request, "fx/list.html", _fx_template_context(company, rates))


@login_and_company_required
@company_admin_required
@require_POST
def fx_delete(request, pk: int):
    company = request.company
    rate = get_object_or_404(FxRate, pk=pk, company=company)
    rate.delete()
    rates = FxRate.objects.filter(company=company).order_by("-rate_date", "currency_code")[:200]
    if request.headers.get("HX-Request"):
        return render(
            request,
            "fx/partials/rates_table.html",
            _fx_template_context(company, rates),
        )
    return redirect("fx:list")


@login_and_company_required
@company_admin_required
@require_POST
def fx_patch(request, pk: int):
    company = request.company
    rate = get_object_or_404(FxRate, pk=pk, company=company)
    key = None
    val = None
    for k, v in request.POST.items():
        if k == "csrfmiddlewaretoken":
            continue
        key, val = k, v
        break
    if key == "value":
        try:
            rate.value = Decimal(val)
            rate.save(update_fields=["value"])
        except (InvalidOperation, TypeError):
            return render(
                request,
                "partials/field_feedback.html",
                {"ok": False, "message": "Valor inválido"},
                status=400,
            )
    return render(request, "partials/field_feedback.html", {"ok": True, "message": "Guardado"})
