from rest_framework.exceptions import PermissionDenied

from apps.organizations.models import UserMembership


def ensure_maker_checker(*, actor, maker) -> None:
    if actor.pk == maker.pk:
        raise PermissionDenied("ثبت‌کننده نمی‌تواند همان رکورد را تأیید یا رد کند.")


def has_active_scope(*, user, organization_id, scope: str) -> bool:
    if user.is_staff:
        return True
    memberships = UserMembership.objects.filter(
        user=user, organization_id=organization_id, is_active=True
    ).values_list("scopes", flat=True)
    return any(scope in scopes for scopes in memberships)


def has_any_active_scope(*, user, organization_id, scopes: set[str]) -> bool:
    if user.is_staff:
        return True
    memberships = UserMembership.objects.filter(
        user=user, organization_id=organization_id, is_active=True
    ).values_list("scopes", flat=True)
    return any(scopes.intersection(membership_scopes) for membership_scopes in memberships)


def has_active_membership(*, user, organization_id) -> bool:
    return (
        user.is_staff
        or UserMembership.objects.filter(
            user=user, organization_id=organization_id, is_active=True
        ).exists()
    )


def ensure_active_scope(*, user, organization_id, scope: str) -> None:
    if not has_active_scope(user=user, organization_id=organization_id, scope=scope):
        raise PermissionDenied("دسترسی لازم برای انجام این عملیات را ندارید.")


def ensure_any_active_scope(*, user, organization_id, scopes: set[str]) -> None:
    if not has_any_active_scope(user=user, organization_id=organization_id, scopes=scopes):
        raise PermissionDenied("دسترسی لازم برای انجام این عملیات را ندارید.")


def ensure_active_membership(*, user, organization_id) -> None:
    if not has_active_membership(user=user, organization_id=organization_id):
        raise PermissionDenied("عضویت فعال در سازمان مربوطه ندارید.")
