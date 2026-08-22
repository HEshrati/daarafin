from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.organizations import selectors, services
from apps.organizations.models import (
    BankAccount,
    DistributorBranch,
    OrganizationContact,
    UserMembership,
)
from apps.organizations.permissions import OrganizationScopedPermission
from common.permissions import ensure_active_scope, request_organization_id

from .serializers import (
    BankAccountSerializer,
    DistributorBranchSerializer,
    ImportResultSerializer,
    MasterDataImportSerializer,
    MembershipSerializer,
    OrganizationContactSerializer,
    OrganizationSerializer,
)


class OrganizationListCreateView(generics.ListCreateAPIView):
    serializer_class = OrganizationSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        org_type = self.request.query_params.get("type")
        qs = selectors.organizations_for_directory(
            self.request.user,
            organization_type=org_type,
        )
        province = self.request.query_params.get("province")
        gln = self.request.query_params.get("gln")
        if org_type:
            qs = qs.filter(type=org_type)
        if province:
            qs = qs.filter(province=province)
        if gln:
            qs = qs.filter(gln=gln)
        return qs.order_by("name", "pk")

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


class ContactListCreateView(generics.ListCreateAPIView):
    serializer_class = OrganizationContactSerializer
    permission_classes = (IsAuthenticated, OrganizationScopedPermission)
    required_scope = "manage_organization"

    def organization(self):
        return generics.get_object_or_404(
            selectors.organizations_for_user(self.request.user), pk=self.kwargs["pk"]
        )

    def get_queryset(self):
        organization = self.organization()
        self.check_object_permissions(self.request, organization)
        return OrganizationContact.objects.filter(organization=organization)

    def perform_create(self, serializer):
        organization = self.organization()
        self.check_object_permissions(self.request, organization)
        serializer.save(organization=organization)


class BranchListCreateView(generics.ListCreateAPIView):
    serializer_class = DistributorBranchSerializer
    permission_classes = (IsAuthenticated, OrganizationScopedPermission)
    required_scope = "manage_organization"

    def organization(self):
        return generics.get_object_or_404(
            selectors.organizations_for_user(self.request.user), pk=self.kwargs["pk"]
        )

    def get_queryset(self):
        organization = self.organization()
        self.check_object_permissions(self.request, organization)
        return DistributorBranch.objects.filter(organization=organization)

    def perform_create(self, serializer):
        organization = self.organization()
        self.check_object_permissions(self.request, organization)
        serializer.save(organization=organization)


class MasterDataImportView(APIView):
    permission_classes = (IsAuthenticated,)
    parser_classes = (MultiPartParser, FormParser)
    serializer_class = MasterDataImportSerializer

    kind_importers = {
        "suppliers": services.import_suppliers_xlsx,
        "pharmacies": services.import_pharmacies_xlsx,
        "distributors": services.import_distributors_xlsx,
    }

    @extend_schema(request=MasterDataImportSerializer, responses=ImportResultSerializer)
    def post(self, request, kind):
        importer = self.kind_importers.get(kind)
        if importer is None:
            return Response(
                {"code": "unknown_import_kind", "message": "نوع ایمپورت نامعتبر است."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        organization_id = request_organization_id(request)
        if not organization_id and not request.user.is_staff:
            return Response(
                {
                    "code": "organization_required",
                    "message": "شناسه سازمان برای بررسی دسترسی لازم است.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not request.user.is_staff:
            ensure_active_scope(
                user=request.user,
                organization_id=organization_id,
                scope="import_master_data",
            )
        upload = request.FILES.get("file")
        if upload is None:
            return Response(
                {"code": "file_required", "message": "فایل اکسل الزامی است."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        result = importer(file_bytes=upload.read())
        return Response(result)
