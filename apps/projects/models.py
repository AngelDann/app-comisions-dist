from django.db import models

from apps.core.models import CompanyBoundModel


class Project(CompanyBoundModel):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=80)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        unique_together = [("company", "slug")]

    def __str__(self) -> str:
        return self.name


class Team(CompanyBoundModel):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=80)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        unique_together = [("company", "slug")]

    def __str__(self) -> str:
        return self.name


class ProjectTeam(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="project_teams")
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="project_teams")
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [("project", "team")]
        ordering = ["sort_order", "team__name"]

    def __str__(self) -> str:
        return f"{self.project} / {self.team}"
