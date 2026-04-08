from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.decorators import company_admin_required
from apps.projects.forms_web import ProjectForm, ProjectTeamForm, TeamForm
from apps.projects.models import Project, ProjectTeam, Team


def _c(request):
    return request.company


@company_admin_required
def project_list(request):
    company = _c(request)
    items = Project.objects.filter(company=company).order_by("name")
    return render(request, "projects/project_list.html", {"projects": items})


@company_admin_required
def project_create(request):
    company = _c(request)
    if request.method == "POST":
        form = ProjectForm(request.POST, company=company)
        if form.is_valid():
            form.save()
            return redirect("projects:project_list")
    else:
        form = ProjectForm(company=company)
    return render(request, "projects/project_form.html", {"form": form, "title": "Nuevo proyecto"})


@company_admin_required
def project_edit(request, pk: int):
    company = _c(request)
    obj = get_object_or_404(Project, pk=pk, company=company)
    if request.method == "POST":
        form = ProjectForm(request.POST, instance=obj, company=company)
        if form.is_valid():
            form.save()
            return redirect("projects:project_list")
    else:
        form = ProjectForm(instance=obj, company=company)
    links = ProjectTeam.objects.filter(project=obj).select_related("team")
    link_form = ProjectTeamForm(company=company, project=obj)
    return render(
        request,
        "projects/project_detail.html",
        {"form": form, "project": obj, "links": links, "link_form": link_form},
    )


@company_admin_required
@require_POST
def project_delete(request, pk: int):
    company = _c(request)
    obj = get_object_or_404(Project, pk=pk, company=company)
    obj.delete()
    return redirect("projects:project_list")


@company_admin_required
def project_add_team(request, pk: int):
    company = _c(request)
    project = get_object_or_404(Project, pk=pk, company=company)
    if request.method == "POST":
        form = ProjectTeamForm(request.POST, company=company, project=project)
        if form.is_valid():
            link = form.save(commit=False)
            if not link.project_id:
                link.project = project
            link.save()
    return redirect("projects:project_edit", pk=pk)


@company_admin_required
def project_remove_team(request, pk: int, team_id: int):
    company = _c(request)
    project = get_object_or_404(Project, pk=pk, company=company)
    ProjectTeam.objects.filter(project=project, team_id=team_id).delete()
    return redirect("projects:project_edit", pk=pk)


@company_admin_required
def team_list(request):
    company = _c(request)
    items = Team.objects.filter(company=company).order_by("name")
    return render(request, "projects/team_list.html", {"teams": items})


@company_admin_required
def team_create(request):
    company = _c(request)
    if request.method == "POST":
        form = TeamForm(request.POST, company=company)
        if form.is_valid():
            form.save()
            return redirect("projects:team_list")
    else:
        form = TeamForm(company=company)
    return render(request, "projects/team_form.html", {"form": form, "title": "Nuevo equipo"})


@company_admin_required
@require_POST
def team_delete(request, pk: int):
    company = _c(request)
    obj = get_object_or_404(Team, pk=pk, company=company)
    obj.delete()
    return redirect("projects:team_list")


@company_admin_required
def team_edit(request, pk: int):
    company = _c(request)
    obj = get_object_or_404(Team, pk=pk, company=company)
    if request.method == "POST":
        form = TeamForm(request.POST, instance=obj, company=company)
        if form.is_valid():
            form.save()
            return redirect("projects:team_list")
    else:
        form = TeamForm(instance=obj, company=company)
    return render(request, "projects/team_form.html", {"form": form, "title": f"Editar {obj}"})
