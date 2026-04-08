from django.db import models


class ManualContentFormat(models.TextChoices):
    MARKDOWN = "markdown", "Markdown"
    HTML = "html", "HTML"


class ManualPage(models.Model):
    """Página del manual de usuario (jerárquica, global, sin tenant)."""

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, db_index=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
    )
    sort_order = models.PositiveIntegerField(default=0)
    icon = models.CharField(
        max_length=32,
        blank=True,
        help_text="Emoji o texto corto mostrado junto al título en el índice.",
    )
    content_format = models.CharField(
        max_length=16,
        choices=ManualContentFormat.choices,
        default=ManualContentFormat.MARKDOWN,
    )
    body = models.TextField(blank=True)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["parent_id", "sort_order", "id"]
        indexes = [
            models.Index(fields=["parent", "sort_order"]),
        ]
        verbose_name = "Página del manual"
        verbose_name_plural = "Páginas del manual"

    def __str__(self) -> str:
        return self.title
