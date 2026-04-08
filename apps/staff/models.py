from django.conf import settings
from django.db import models

from apps.core.models import CompanyBoundModel


class Employee(CompanyBoundModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employee_profiles",
    )
    first_name = models.CharField(max_length=120)
    last_name = models.CharField(max_length=120)
    employee_code = models.CharField(max_length=64, blank=True)
    is_active = models.BooleanField(default=True)
    teams = models.ManyToManyField(
        "projects.Team",
        through="staff.EmployeeTeam",
        related_name="employees",
        blank=True,
    )
    projects = models.ManyToManyField(
        "projects.Project",
        through="staff.EmployeeProject",
        related_name="employees_direct",
        blank=True,
    )

    class Meta:
        ordering = ["last_name", "first_name"]
        indexes = [
            models.Index(fields=["company", "is_active"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "user"],
                condition=models.Q(user__isnull=False),
                name="staff_employee_unique_user_per_company",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}"


class EmployeeTeam(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="employee_teams")
    team = models.ForeignKey("projects.Team", on_delete=models.CASCADE, related_name="employee_teams")

    class Meta:
        unique_together = [("employee", "team")]


class EmployeeProject(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="employee_projects")
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="employee_projects")

    class Meta:
        unique_together = [("employee", "project")]
