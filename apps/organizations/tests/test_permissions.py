from types import SimpleNamespace

import pytest
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APIClient

from apps.identity.tests.factories import UserFactory
from apps.organizations.models import Organization, UserMembership
from apps.organizations.permissions import OrganizationScopedPermission
from common.permissions import ensure_maker_checker

pytestmark = pytest.mark.django_db


def org():
    return Organization.objects.create(name="آزمایش", type="bank", national_id="14000000000")


def request(user):
    return SimpleNamespace(user=user)


def test_scope_allows_object_access():
    user = UserFactory()
    organization = org()
    UserMembership.objects.create(
        user=user, organization=organization, role="owner", scopes=["manage_organization"]
    )
    assert OrganizationScopedPermission().has_object_permission(
        request(user), SimpleNamespace(required_scope="manage_organization"), organization
    )


def test_missing_scope_denies_object_access():
    user = UserFactory()
    organization = org()
    UserMembership.objects.create(user=user, organization=organization, role="operator", scopes=[])
    assert not OrganizationScopedPermission().has_object_permission(
        request(user), SimpleNamespace(required_scope="manage_organization"), organization
    )


def test_inactive_membership_denies_access():
    user = UserFactory()
    organization = org()
    UserMembership.objects.create(
        user=user,
        organization=organization,
        role="owner",
        scopes=["manage_organization"],
        is_active=False,
    )
    assert not OrganizationScopedPermission().has_object_permission(
        request(user), SimpleNamespace(required_scope="manage_organization"), organization
    )


def test_staff_bypasses_organization_membership_permission():
    user = UserFactory(is_staff=True)
    organization = org()

    assert OrganizationScopedPermission().has_object_permission(
        request(user), SimpleNamespace(required_scope="manage_organization"), organization
    )


def test_maker_cannot_approve_own_record():
    user = UserFactory()
    with pytest.raises(PermissionDenied):
        ensure_maker_checker(actor=user, maker=user)


def test_authenticated_user_can_list_only_active_insurance_directory_entries():
    user = UserFactory()
    Organization.objects.create(
        name="بیمه فعال",
        type=Organization.Type.INSURANCE,
        national_id="14000000001",
    )
    Organization.objects.create(
        name="بیمه غیرفعال",
        type=Organization.Type.INSURANCE,
        national_id="14000000002",
        status=Organization.Status.SUSPENDED,
    )
    Organization.objects.create(
        name="تولیدکننده",
        type=Organization.Type.MANUFACTURER,
        national_id="14000000003",
    )

    client = APIClient()
    client.force_authenticate(user)

    response = client.get("/api/v1/organizations", {"type": "insurance"})

    assert response.status_code == 200
    assert [row["name"] for row in response.data] == ["بیمه فعال"]


def test_master_data_import_rejects_invalid_organization_id():
    client = APIClient()
    client.force_authenticate(UserFactory())

    response = client.post(
        "/api/v1/masterdata/import/suppliers",
        {"organization_id": "invalid"},
        format="multipart",
    )

    assert response.status_code == 400
    assert "organization_id" in response.data["errors"]
