from django.db import transaction

from common.errors import DomainError
from common.excel import (
    iter_xlsx_rows,
    map_distributor_row,
    map_pharmacy_row,
    map_supplier_row,
)

from .models import (
    DistributorBranch,
    Organization,
    OrganizationContact,
    PharmacyProfile,
    UserMembership,
)

DEFAULT_ROLE_SCOPES = {
    "owner": [
        "manage_organization",
        "manage_members",
        "manage_onboarding",
        "view_bank_accounts",
        "change_bank_account",
        "create_invoice",
        "dispute_invoice",
        "view_invoice",
        "manage_facility",
        "reserve_facility",
        "view_facility",
        "create_financing",
        "view_financing",
        "import_master_data",
        "view_medicines",
        "manage_medicines",
    ],
    "operator": [
        "create_invoice",
        "dispute_invoice",
        "view_invoice",
        "reserve_facility",
        "view_facility",
        "create_financing",
        "view_financing",
        "import_master_data",
        "view_medicines",
    ],
    "approver": [
        "approve_financing",
        "reject_financing",
        "view_financing",
        "verify_invoice",
        "view_invoice",
        "view_medicines",
    ],
    "risk_expert": [
        "view_risk",
        "assess_risk",
        "review_onboarding",
        "verify_invoice",
        "view_invoice",
        "view_medicines",
    ],
    "bank_finance": [
        "view_ledger",
        "approve_payment",
        "disburse_financing",
        "view_financing",
        "view_medicines",
    ],
    "support": ["view_support_case", "view_medicines"],
}

ORG_PROFILE_FIELDS = (
    "gln",
    "company_type",
    "country",
    "province",
    "county",
    "city",
    "address",
    "postal_code",
    "phone",
    "email",
)


@transaction.atomic
def create_organization(*, actor, data):
    organization = Organization.objects.create(**data)
    UserMembership.objects.create(
        user=actor,
        organization=organization,
        role=UserMembership.Role.OWNER,
        scopes=DEFAULT_ROLE_SCOPES["owner"].copy(),
    )
    return organization


@transaction.atomic
def add_member(*, organization, data):
    data.setdefault("scopes", DEFAULT_ROLE_SCOPES[data["role"]].copy())
    return UserMembership.objects.create(organization=organization, **data)


def _upsert_contact(*, organization, role, full_name="", national_id="", mobile="", email=""):
    if not any([full_name, national_id, mobile, email]):
        return None
    qs = OrganizationContact.objects.filter(organization=organization, role=role)
    if national_id:
        existing = qs.filter(national_id=national_id).first()
    else:
        existing = qs.filter(full_name=full_name, mobile=mobile).first()
    if existing:
        existing.full_name = full_name or existing.full_name
        existing.national_id = national_id or existing.national_id
        existing.mobile = mobile or existing.mobile
        existing.email = email or existing.email
        existing.save()
        return existing
    return OrganizationContact.objects.create(
        organization=organization,
        role=role,
        full_name=full_name,
        national_id=national_id,
        mobile=mobile,
        email=email,
    )


def _apply_org_fields(organization, payload):
    for field in ORG_PROFILE_FIELDS:
        value = payload.get(field)
        if value not in (None, ""):
            setattr(organization, field, value)
    if payload.get("name"):
        organization.name = payload["name"]
    organization.save()


def _find_organization(*, national_id="", gln=""):
    if national_id:
        found = Organization.objects.filter(national_id=national_id).first()
        if found:
            return found
    if gln:
        return Organization.objects.filter(gln=gln).exclude(gln="").first()
    return None


@transaction.atomic
def upsert_supplier_from_row(*, row):
    national_id = row.get("national_id") or ""
    gln = row.get("gln") or ""
    name = row.get("name") or ""
    if not name:
        raise DomainError("invalid_supplier_row", "نام تامین‌کننده الزامی است.")
    if not national_id and not gln:
        raise DomainError("invalid_supplier_row", "شناسه شرکت یا GLN الزامی است.")
    if not national_id:
        national_id = f"GLN-{gln}"

    organization = _find_organization(national_id=national_id, gln=gln)
    created = False
    if organization is None:
        organization = Organization.objects.create(
            name=name,
            type=Organization.Type.MANUFACTURER,
            national_id=national_id,
            gln=gln,
        )
        created = True
    else:
        if organization.type != Organization.Type.MANUFACTURER:
            organization.type = Organization.Type.MANUFACTURER
    _apply_org_fields(organization, row)
    _upsert_contact(
        organization=organization,
        role=OrganizationContact.Role.CEO,
        full_name=row.get("ceo_name", ""),
        national_id=row.get("ceo_national_id", ""),
    )
    _upsert_contact(
        organization=organization,
        role=OrganizationContact.Role.TECHNICAL,
        full_name=row.get("technical_name", ""),
        national_id=row.get("technical_national_id", ""),
        mobile=row.get("mobile", ""),
        email=row.get("email", ""),
    )
    return organization, created


@transaction.atomic
def upsert_pharmacy_from_row(*, row):
    gln = row.get("gln") or ""
    name = row.get("name") or ""
    national_id = row.get("national_id") or row.get("customer_national_id") or ""
    if not gln and not national_id:
        raise DomainError("invalid_pharmacy_row", "GLN یا شناسه ملی داروخانه الزامی است.")
    if not name:
        name = row.get("owner_name") or f"داروخانه {gln or national_id}"
    if not national_id:
        national_id = f"PH-{gln}"

    organization = _find_organization(national_id=national_id, gln=gln)
    created = False
    if organization is None:
        organization = Organization.objects.create(
            name=name,
            type=Organization.Type.PHARMACY,
            national_id=national_id,
            gln=gln,
        )
        created = True
    else:
        organization.type = Organization.Type.PHARMACY
    _apply_org_fields(organization, row)

    profile, _ = PharmacyProfile.objects.update_or_create(
        organization=organization,
        defaults={
            "university_name": row.get("university_name", ""),
            "service_type": row.get("service_type", ""),
            "pharmacy_type": row.get("pharmacy_type", ""),
            "customer_national_id": row.get("customer_national_id", "") or national_id,
            "owner_name": row.get("owner_name", ""),
            "responsible_national_id": row.get("responsible_national_id", ""),
            "founder_mobile": row.get("founder_mobile", ""),
            "landline": row.get("landline", ""),
        },
    )
    _upsert_contact(
        organization=organization,
        role=OrganizationContact.Role.OWNER,
        full_name=row.get("owner_name", ""),
        national_id=row.get("responsible_national_id", ""),
        mobile=row.get("founder_mobile", ""),
    )
    return organization, profile, created


@transaction.atomic
def upsert_distributor_from_row(*, row):
    national_id = row.get("national_id") or ""
    gln = row.get("gln") or ""
    name = row.get("name") or ""
    if not name:
        raise DomainError("invalid_distributor_row", "نام شرکت توزیع الزامی است.")
    if not national_id and not gln:
        raise DomainError("invalid_distributor_row", "کد ملی یا GLN الزامی است.")
    if not national_id:
        national_id = f"DIST-{gln}"

    organization = _find_organization(national_id=national_id, gln=gln)
    created = False
    if organization is None:
        organization = Organization.objects.create(
            name=name,
            type=Organization.Type.DISTRIBUTOR,
            national_id=national_id,
            gln=gln,
        )
        created = True
    else:
        organization.type = Organization.Type.DISTRIBUTOR
    _apply_org_fields(organization, row)
    _upsert_contact(
        organization=organization,
        role=OrganizationContact.Role.CEO,
        full_name=row.get("ceo_name", ""),
        national_id=row.get("ceo_national_id", ""),
    )
    _upsert_contact(
        organization=organization,
        role=OrganizationContact.Role.TECHNICAL,
        full_name=row.get("technical_name", ""),
        national_id=row.get("technical_national_id", ""),
        mobile=row.get("mobile", ""),
        email=row.get("email", ""),
    )

    branch = None
    branch_gln = row.get("branch_gln") or ""
    if branch_gln:
        branch, _ = DistributorBranch.objects.update_or_create(
            organization=organization,
            gln=branch_gln,
            defaults={
                "name": row.get("branch_name", ""),
                "postal_code": row.get("branch_postal_code", ""),
                "province": row.get("branch_province", ""),
                "county": row.get("branch_county", ""),
                "city": row.get("branch_city", ""),
                "address": row.get("branch_address", ""),
            },
        )
    return organization, branch, created


def import_suppliers_xlsx(*, file_bytes: bytes):
    created = updated = 0
    errors = []
    for row_number, mapping, row in iter_xlsx_rows(file_bytes):
        try:
            payload = map_supplier_row(mapping, row)
            _, was_created = upsert_supplier_from_row(row=payload)
            created += int(was_created)
            updated += int(not was_created)
        except DomainError as exc:
            errors.append({"row": row_number, "message": exc.detail.get("message", str(exc))})
        except Exception as exc:  # noqa: BLE001
            errors.append({"row": row_number, "message": str(exc)})
    return {"created": created, "updated": updated, "errors": errors}


def import_pharmacies_xlsx(*, file_bytes: bytes):
    created = updated = 0
    errors = []
    for row_number, mapping, row in iter_xlsx_rows(file_bytes):
        try:
            payload = map_pharmacy_row(mapping, row)
            _, _, was_created = upsert_pharmacy_from_row(row=payload)
            created += int(was_created)
            updated += int(not was_created)
        except DomainError as exc:
            errors.append({"row": row_number, "message": exc.detail.get("message", str(exc))})
        except Exception as exc:  # noqa: BLE001
            errors.append({"row": row_number, "message": str(exc)})
    return {"created": created, "updated": updated, "errors": errors}


def import_distributors_xlsx(*, file_bytes: bytes):
    created = updated = 0
    errors = []
    for row_number, mapping, row in iter_xlsx_rows(file_bytes):
        try:
            payload = map_distributor_row(mapping, row)
            _, _, was_created = upsert_distributor_from_row(row=payload)
            created += int(was_created)
            updated += int(not was_created)
        except DomainError as exc:
            errors.append({"row": row_number, "message": exc.detail.get("message", str(exc))})
        except Exception as exc:  # noqa: BLE001
            errors.append({"row": row_number, "message": str(exc)})
    return {"created": created, "updated": updated, "errors": errors}
