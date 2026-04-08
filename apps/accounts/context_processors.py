def active_company(request):
    ctx = {
        "active_company": getattr(request, "company", None),
        "active_membership": getattr(request, "membership", None),
    }
    company = ctx["active_company"]
    user = getattr(request, "user", None)
    if user and user.is_authenticated and company:
        from apps.accounts.permissions import (
            can_manage_company_users,
            is_company_commission_auditor,
            sees_all_company_commissions,
            user_accessible_team_ids,
            user_linked_employee_id,
            user_team_lead_ids,
        )

        ctx["nav_company_wide"] = sees_all_company_commissions(user, company)
        ctx["nav_commission_auditor"] = is_company_commission_auditor(user, company)
        ctx["nav_linked_employee_id"] = user_linked_employee_id(user, company)
        ctx["nav_can_manage_users"] = can_manage_company_users(user, company)
        ctx["nav_team_lead_ids"] = user_team_lead_ids(user, company)
        ctx["nav_has_team_assignment"] = bool(user_accessible_team_ids(user, company))
    else:
        ctx["nav_company_wide"] = False
        ctx["nav_commission_auditor"] = False
        ctx["nav_linked_employee_id"] = None
        ctx["nav_can_manage_users"] = False
        ctx["nav_team_lead_ids"] = []
        ctx["nav_has_team_assignment"] = False
    return ctx
