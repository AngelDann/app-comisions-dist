from django.db import models

from apps.core.models import CompanyBoundModel


class FxRate(CompanyBoundModel):
    """Tipo de cambio de referencia por moneda y fecha.

    ``value`` = cuántas unidades de la moneda base de la compañía equivalen
    a 1 unidad de ``currency_code`` (p. ej. base MXN, USD, value=17.5 → 1 USD = 17.5 MXN).
    """

    currency_code = models.CharField(max_length=3)
    rate_date = models.DateField(db_index=True)
    value = models.DecimalField(max_digits=18, decimal_places=6)
    source = models.CharField(max_length=64, default="manual")

    class Meta:
        ordering = ["-rate_date", "currency_code"]
        unique_together = [("company", "currency_code", "rate_date")]
        indexes = [
            models.Index(fields=["company", "currency_code", "rate_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.currency_code} {self.rate_date}: {self.value}"
