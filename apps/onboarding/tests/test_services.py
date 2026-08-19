import pytest

from apps.identity.tests.factories import UserFactory
from apps.onboarding.models import OnboardingCase
from apps.onboarding.services import transition_case
from apps.organizations.models import Organization
from common.errors import DomainError

pytestmark = pytest.mark.django_db


def make_case():
    user = UserFactory()
    org = Organization.objects.create(name="شرکت", type="manufacturer", national_id="10101010101")
    return OnboardingCase.objects.create(organization=org, requested_by=user), user


def test_valid_transition():
    case, user = make_case()
    transition_case(case=case, target="submitted", actor=user)
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
        transition_case(case=case, target=target, actor=reviewer)
    else:
        transition_case(case=case, target="submitted", actor=requester)
        transition_case(case=case, target="under_review", actor=reviewer)
        transition_case(
            case=case, target=target, actor=reviewer, reason="بررسی" if target == "rejected" else ""
        )
    assert case.status == target
