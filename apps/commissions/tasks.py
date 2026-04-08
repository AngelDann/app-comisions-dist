from celery import shared_task
from django.utils import timezone

from apps.commissions.engine import CommissionEngine
from apps.commissions.models import CalculationRun, CommissionEvent, CommissionPeriod


@shared_task
def recalculate_period(period_id: int, user_id: int | None = None) -> str:
    period = CommissionPeriod.objects.select_related("company").get(pk=period_id)
    run = CalculationRun.objects.create(
        company=period.company,
        period=period,
        triggered_by_id=user_id,
        status="running",
    )
    try:
        qs = CommissionEvent.objects.filter(company=period.company, period=period).select_related(
            "company", "fx_rate"
        )
        count = 0
        for ev in qs.iterator():
            CommissionEngine.evaluate(ev)
            count += 1
        run.status = "done"
        run.log = f"Recalculados {count} eventos."
        run.finished_at = timezone.now()
        run.save(update_fields=["status", "log", "finished_at"])
    except Exception as exc:  # noqa: BLE001
        run.status = "error"
        run.log = str(exc)
        run.finished_at = timezone.now()
        run.save(update_fields=["status", "log", "finished_at"])
        raise
    return run.log or ""
