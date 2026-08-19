from .models import Facility

FACILITY_SCOPES = {"view_facility", "manage_facility", "reserve_facility"}


def facilities_for_user(user):
    if user.is_staff:
        return Facility.objects.all()
    organization_ids = [
        organization_id
        for organization_id, scopes in user.memberships.filter(is_active=True).values_list(
            "organization_id", "scopes"
        )
        if FACILITY_SCOPES.intersection(scopes)
    ]
    return Facility.objects.filter(borrower_id__in=organization_ids) | Facility.objects.filter(
        lender_id__in=organization_ids
    )
