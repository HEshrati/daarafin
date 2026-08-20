from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.medicines.models import Medicine, MedicineInsurancePrice
from apps.organizations.models import DistributorBranch, Organization, PharmacyProfile
from apps.organizations.selectors import organizations_for_user


class MasterDataSummaryView(APIView):
    """خلاصه شمارشی مستر دیتا برای داشبورد/گزارش."""

    permission_classes = (IsAuthenticated,)

    def get(self, request):
        orgs = organizations_for_user(request.user)
        return Response(
            {
                "organizations": {
                    "total": orgs.count(),
                    "manufacturers": orgs.filter(type=Organization.Type.MANUFACTURER).count(),
                    "distributors": orgs.filter(type=Organization.Type.DISTRIBUTOR).count(),
                    "pharmacies": orgs.filter(type=Organization.Type.PHARMACY).count(),
                },
                "pharmacy_profiles": PharmacyProfile.objects.filter(
                    organization__in=orgs
                ).count(),
                "distributor_branches": DistributorBranch.objects.filter(
                    organization__in=orgs
                ).count(),
                "medicines": Medicine.objects.count(),
                "insurance_prices": MedicineInsurancePrice.objects.count(),
            }
        )
