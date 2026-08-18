from rest_framework.permissions import BasePermission

from .selectors import active_membership


def object_organization_id(obj):
    return obj.pk if obj.__class__.__name__ == "Organization" else obj.organization_id


class OrganizationScopedPermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        membership = active_membership(
            user=request.user, organization_id=object_organization_id(obj)
        )
        required_scope = getattr(view, "required_scope", None)
        return bool(membership and (required_scope is None or required_scope in membership.scopes))
