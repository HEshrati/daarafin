from .models import Organization, UserMembership


def organizations_for_user(user):
    if user.is_staff:
        return Organization.objects.all()
    return Organization.objects.filter(
        memberships__user=user, memberships__is_active=True
    ).distinct()


def organizations_for_directory(user, *, organization_type=None):
    """Return organizations visible in list views without widening object access.

    Insurance organizations are shared master data used by every authenticated
    participant. Other organization types remain membership-scoped.
    """
    if organization_type == Organization.Type.INSURANCE:
        return Organization.objects.filter(
            type=Organization.Type.INSURANCE,
            status=Organization.Status.ACTIVE,
        )
    return organizations_for_user(user)


def active_membership(*, user, organization_id):
    return UserMembership.objects.filter(
        user=user, organization_id=organization_id, is_active=True
    ).first()
