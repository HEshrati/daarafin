from .models import Organization, UserMembership


def organizations_for_user(user):
    if user.is_staff:
        return Organization.objects.all()
    return Organization.objects.filter(
        memberships__user=user, memberships__is_active=True
    ).distinct()


def active_membership(*, user, organization_id):
    return UserMembership.objects.filter(
        user=user, organization_id=organization_id, is_active=True
    ).first()
