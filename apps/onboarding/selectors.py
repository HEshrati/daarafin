from .models import OnboardingCase

CASE_SCOPES = {"manage_onboarding", "review_onboarding"}


def cases_for_user(user):
    if user.is_staff:
        return OnboardingCase.objects.all()
    organization_ids = [
        organization_id
        for organization_id, scopes in user.memberships.filter(is_active=True).values_list(
            "organization_id", "scopes"
        )
        if CASE_SCOPES.intersection(scopes)
    ]
    return OnboardingCase.objects.filter(organization_id__in=organization_ids)
