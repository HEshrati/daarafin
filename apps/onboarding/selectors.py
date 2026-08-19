from .models import OnboardingCase


def cases_for_user(user):
    return OnboardingCase.objects.filter(
        organization__memberships__user=user, organization__memberships__is_active=True
    ).distinct()
