from django.db import models


class CompanyBoundModel(models.Model):
    """Abstract base: all tenant-scoped rows point at Company (single schema)."""

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="%(class)ss",
    )

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=["company"]),
        ]
