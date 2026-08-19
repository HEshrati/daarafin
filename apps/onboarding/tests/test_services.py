import pytest

from apps.identity.tests.factories import UserFactory
from apps.onboarding.models import OnboardingCase
from apps.onboarding.services import create_case, transition_case
from apps.organizations.models import Organization, UserMembership
from common.errors import DomainError

pytestmark = pytest.mark.django_db


def make_case():
    user = UserFactory()
    org = Organization.objects.create(name="شرکت", type="manufacturer", national_id="10101010101")
    return OnboardingCase.objects.create(organization=org, requested_by=user), user


def test_valid_transition():
    case, user = make_case()
    case = transition_case(case=case, target="submitted", actor=user)
    assert case.status == "submitted"


def test_invalid_direct_approval():
    case, user = make_case()
    with pytest.raises(DomainError):
        transition_case(case=case, target="approved", actor=user)


@pytest.mark.parametrize("target", ["approved", "rejected", "suspended"])
def test_terminal_states(target):
    case, requester = make_case()
    reviewer = UserFactory()
    if target == "suspended":
        case = transition_case(case=case, target=target, actor=reviewer)
    else:
        case = transition_case(case=case, target="submitted", actor=requester)
        case = transition_case(case=case, target="under_review", actor=reviewer)
        case = transition_case(
            case=case, target=target, actor=reviewer, reason="بررسی" if target == "rejected" else ""
        )
    assert case.status == target


def test_existing_organization_cannot_be_claimed_by_national_id():
    organization = Organization.objects.create(
        name="مالک اصلی", type="manufacturer", national_id="90909090909"
    )
    attacker = UserFactory()

    with pytest.raises(DomainError):
        create_case(
            actor=attacker,
            name="نام جعلی",
            national_id=organization.national_id,
            organization_type="manufacturer",
        )

    assert not UserMembership.objects.filter(user=attacker, organization=organization).exists()
