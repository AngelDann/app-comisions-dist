from django.conf import settings
from django.db import models


class MembershipRole(models.TextChoices):
    SUPER_ADMIN = "super_admin", "Super administrador"
    COMPANY_ADMIN = "company_admin", "Administrador de empresa"
    COMMISSIONS_LEAD = "commissions_lead", "Encargado de comisiones"
    SUPERVISOR = "supervisor", "Supervisor / líder"
    COLLABORATOR = "collaborator", "Colaborador"
    AUDITOR = "auditor", "Auditor (solo lectura)"


class UserMembership(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    role = models.CharField(max_length=32, choices=MembershipRole.choices, default=MembershipRole.COLLABORATOR)
    is_primary = models.BooleanField(default=False)

    class Meta:
        unique_together = [("user", "company")]
        indexes = [
            models.Index(fields=["user", "company"]),
        ]

    def __str__(self) -> str:
        return f"{self.user} @ {self.company} ({self.role})"


class UserProjectScope(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="project_scopes")
    company = models.ForeignKey("companies.Company", on_delete=models.CASCADE, related_name="user_project_scopes")
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="user_scopes")

    class Meta:
        unique_together = [("user", "company", "project")]


class UserTeamScope(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="team_scopes")
    company = models.ForeignKey("companies.Company", on_delete=models.CASCADE, related_name="user_team_scopes")
    team = models.ForeignKey("projects.Team", on_delete=models.CASCADE, related_name="user_scopes")
    is_team_lead = models.BooleanField(
        default=False,
        help_text="Permisos elevados solo dentro de este equipo (p. ej. aprobar, gestionar miembros del equipo).",
    )

    class Meta:
        unique_together = [("user", "company", "team")]
