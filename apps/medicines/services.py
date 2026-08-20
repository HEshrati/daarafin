from django.db import transaction
from django.db.models import Q

from common.errors import DomainError
from common.excel import (
    iter_ods_rows,
    iter_xlsx_rows,
    map_insurance_price_row,
    map_medicine_row,
    parse_date,
    parse_datetime,
    parse_decimal,
)

from .models import Medicine, MedicineInsurancePrice


def medicines_queryset(*, search=""):
    qs = Medicine.objects.all().order_by("name", "pk")
    if search:
        qs = qs.filter(
            Q(name__icontains=search)
            | Q(molecule__icontains=search)
            | Q(atc_code__icontains=search)
            | Q(formulary_code__icontains=search)
            | Q(external_id__icontains=search)
        )
    return qs


@transaction.atomic
def upsert_medicine_from_row(*, row):
    external_id = (row.get("external_id") or "").strip()
    name = (row.get("name") or "").strip()
    if not external_id or not name:
        raise DomainError("invalid_medicine_row", "شناسه و نام دارو الزامی است.")
    medicine, created = Medicine.objects.update_or_create(
        external_id=external_id,
        defaults={
            "name": name,
            "strength": row.get("strength", ""),
            "molecule": row.get("molecule", ""),
            "route": row.get("route", ""),
            "dosage_form": row.get("dosage_form", ""),
            "atc_code": row.get("atc_code", ""),
            "formulary_code": row.get("formulary_code", ""),
            "access_level": row.get("access_level", ""),
            "drug_type": row.get("drug_type", ""),
            "clinical_use": row.get("clinical_use", ""),
            "formulary_entry_date": row.get("formulary_entry_date", ""),
        },
    )
    return medicine, created


def import_medicines_xlsx(*, file_bytes: bytes):
    created = updated = 0
    errors = []
    for row_number, mapping, row in iter_xlsx_rows(file_bytes):
        try:
            payload = map_medicine_row(mapping, row)
            _, was_created = upsert_medicine_from_row(row=payload)
            created += int(was_created)
            updated += int(not was_created)
        except DomainError as exc:
            errors.append({"row": row_number, "message": exc.detail.get("message", str(exc))})
        except Exception as exc:  # noqa: BLE001
            errors.append({"row": row_number, "message": str(exc)})
    return {"created": created, "updated": updated, "errors": errors}


@transaction.atomic
def upsert_insurance_price_from_row(*, row):
    generic_code = (row.get("generic_code") or "").strip()
    if not generic_code:
        raise DomainError("invalid_price_row", "کد generic الزامی است.")
    insurance_price = parse_decimal(row.get("insurance_price"))
    subsidy_price = parse_decimal(row.get("subsidy_price"), default="0")
    if insurance_price is None or subsidy_price is None:
        raise DomainError("invalid_price_row", "قیمت بیمه/یارانه نامعتبر است.")

    medicine = Medicine.objects.filter(external_id=generic_code).first()
    letter_miladi = parse_date(row.get("letter_miladi_date"))
    package_number = str(row.get("package_number") or "").strip()
    insurance_type = str(row.get("insurance_type") or "").strip()

    price, created = MedicineInsurancePrice.objects.update_or_create(
        generic_code=generic_code,
        letter_miladi_date=letter_miladi,
        package_number=package_number,
        insurance_type=insurance_type,
        defaults={
            "medicine": medicine,
            "generic_name": row.get("generic_name", ""),
            "insurance_price": insurance_price,
            "subsidy_price": subsidy_price,
            "letter_shamsi_date": row.get("letter_shamsi_date", ""),
            "last_update_date": parse_date(row.get("last_update_date")),
            "source_created_at": parse_datetime(row.get("source_created_at")),
            "source_updated_at": parse_datetime(row.get("source_updated_at")),
        },
    )
    return price, created


def import_insurance_prices_ods(*, file_bytes: bytes):
    created = updated = 0
    errors = []
    for row_number, mapping, row in iter_ods_rows(file_bytes):
        try:
            payload = map_insurance_price_row(mapping, row)
            _, was_created = upsert_insurance_price_from_row(row=payload)
            created += int(was_created)
            updated += int(not was_created)
        except DomainError as exc:
            errors.append({"row": row_number, "message": exc.detail.get("message", str(exc))})
        except Exception as exc:  # noqa: BLE001
            errors.append({"row": row_number, "message": str(exc)})
    return {"created": created, "updated": updated, "errors": errors}
