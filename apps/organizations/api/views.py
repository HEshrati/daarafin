from rest_framework import generics
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated

from apps.organizations import selectors, services
from apps.organizations.models import BankAccount, UserMembership
from apps.organizations.permissions import OrganizationScopedPermission

from .serializers import BankAccountSerializer, MembershipSerializer, OrganizationSerializer


class OrganizationListCreateView(generics.ListCreateAPIView):
    serializer_class = OrganizationSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return selectors.organizations_for_user(self.request.user)

    def perform_create(self, serializer):
        serializer.instance = services.create_organization(
            actor=self.request.user, data=serializer.validated_data
        )


class OrganizationDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = OrganizationSerializer
    permission_classes = (IsAuthenticated, OrganizationScopedPermission)
    required_scope = "manage_organization"

    def get_queryset(self):
        return selectors.organizations_for_user(self.request.user)


class MemberListCreateView(generics.ListCreateAPIView):
    serializer_class = MembershipSerializer
    permission_classes = (IsAuthenticated, OrganizationScopedPermission)
    required_scope = "manage_members"

    def organization(self):
        return generics.get_object_or_404(
            selectors.organizations_for_user(self.request.user), pk=self.kwargs["pk"]
        )

    def get_queryset(self):
        organization = self.organization()
        self.check_object_permissions(self.request, organization)
        return UserMembership.objects.filter(organization=organization)

    def perform_create(self, serializer):
        organization = self.organization()
        self.check_object_permissions(self.request, organization)
        serializer.instance = services.add_member(
            organization=organization, data=serializer.validated_data
        )


class BankAccountListView(generics.ListAPIView):
    serializer_class = BankAccountSerializer
    permission_classes = (IsAuthenticated, OrganizationScopedPermission)
    required_scope = "view_bank_accounts"

    def get_queryset(self):
        organization = generics.get_object_or_404(
            selectors.organizations_for_user(self.request.user), pk=self.kwargs["pk"]
        )
        self.check_object_permissions(self.request, organization)
        token_org = (
            self.request.auth.get("organization_id")
            if self.request.auth and hasattr(self.request.auth, "get")
            else None
        )
        if token_org is not None and str(token_org) != str(organization.pk):
            raise PermissionDenied("سازمان فعال توکن با درخواست هم‌خوان نیست.")
        return BankAccount.objects.filter(organization=organization)
