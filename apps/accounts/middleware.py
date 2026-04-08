from django.utils.functional import SimpleLazyObject

from apps.accounts.models import MembershipRole, UserMembership


def _get_company(request):
    if not request.user.is_authenticated:
        return None
    if request.user.is_superuser:
        cid = request.session.get("active_company_id")
        if cid:
            from apps.companies.models import Company

            try:
                return Company.objects.get(pk=cid)
            except Company.DoesNotExist:
                return None
        return None

    memberships = UserMembership.objects.filter(user=request.user).select_related("company")
    cid = request.session.get("active_company_id")
    if cid:
        m = memberships.filter(company_id=cid).first()
        if m:
            return m.company
    primary = memberships.filter(is_primary=True).first()
    if primary:
        return primary.company
    first = memberships.first()
    return first.company if first else None


def _get_membership(request):
    if not request.user.is_authenticated:
        return None
    company = _get_company(request)
    if company is None:
        return None
    return (
        UserMembership.objects.filter(user=request.user, company=company)
        .select_related("company")
        .first()
    )


class CompanyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.company = SimpleLazyObject(lambda: _get_company(request))
        request.membership = SimpleLazyObject(lambda: _get_membership(request))
        response = self.get_response(request)
        return response


def user_has_company_access(user, company) -> bool:
    if user.is_superuser:
        return True
    return UserMembership.objects.filter(user=user, company=company).exists()


def membership_role(user, company):
    if user.is_superuser:
        return MembershipRole.SUPER_ADMIN
    m = UserMembership.objects.filter(user=user, company=company).first()
    return m.role if m else None


def is_company_admin(user, company) -> bool:
    role = membership_role(user, company)
    return user.is_superuser or role in (
        MembershipRole.COMPANY_ADMIN,
        MembershipRole.COMMISSIONS_LEAD,
        MembershipRole.SUPER_ADMIN,
    )


def scoped_projects_queryset(user, company):
    from apps.projects.models import Project

    qs = Project.objects.filter(company=company, is_active=True)
    if user.is_superuser:
        return qs
    role = membership_role(user, company)
    if role in (
        MembershipRole.COMPANY_ADMIN,
        MembershipRole.COMMISSIONS_LEAD,
        MembershipRole.SUPER_ADMIN,
    ):
        return qs
    from apps.accounts.models import UserProjectScope

    ids = UserProjectScope.objects.filter(user=user, company=company).values_list(
        "project_id", flat=True
    )
    return qs.filter(pk__in=ids)


def scoped_teams_queryset(user, company):
    from apps.projects.models import Team

    qs = Team.objects.filter(company=company, is_active=True)
    if user.is_superuser:
        return qs
    role = membership_role(user, company)
    if role in (
        MembershipRole.COMPANY_ADMIN,
        MembershipRole.COMMISSIONS_LEAD,
        MembershipRole.SUPER_ADMIN,
    ):
        return qs
    from apps.accounts.models import UserTeamScope

    ids = UserTeamScope.objects.filter(user=user, company=company).values_list("team_id", flat=True)
    return qs.filter(pk__in=ids)
