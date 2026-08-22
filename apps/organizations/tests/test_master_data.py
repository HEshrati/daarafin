from decimal import Decimal
from io import BytesIO

import pytest
from openpyxl import Workbook

from apps.medicines.models import Medicine
from apps.medicines.services import import_medicines_xlsx, upsert_medicine_from_row
from apps.organizations.models import Organization, OrganizationContact, PharmacyProfile
from apps.organizations.services import (
    import_pharmacies_xlsx,
    import_suppliers_xlsx,
    upsert_pharmacy_from_row,
    upsert_supplier_from_row,
)

pytestmark = pytest.mark.django_db


def _xlsx_bytes(headers, rows):
    wb = Workbook()
    ws = wb.active
    ws.append(headers)
    for row in rows:
        ws.append(row)
    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def test_upsert_supplier_creates_contacts():
    org, created = upsert_supplier_from_row(
        row={
            "gln": "114500014",
            "name": "روناک",
            "national_id": "10102401208",
            "province": "تهران",
            "ceo_name": "سعید",
            "ceo_national_id": "5899320699",
            "technical_name": "اصغر",
            "technical_national_id": "4073322915",
            "mobile": "9169621390",
            "email": "a@b.com",
        }
    )
    assert created
    assert org.type == Organization.Type.MANUFACTURER
    assert org.gln == "114500014"
    assert OrganizationContact.objects.filter(organization=org).count() == 2


def test_import_suppliers_xlsx():
    content = _xlsx_bytes(
        [
            "کد GLN",
            "نام تامین کننده",
            "شناسه شرکت",
            "نام مسئول فنی",
            "شناسه ملی مسئول فنی",
            "موبایل",
            "ایمیل",
        ],
        [["1", "شرکت الف", "111", "فنی", "222", "0912", "t@t.com"]],
    )
    result = import_suppliers_xlsx(file_bytes=content)
    assert result["created"] == 1
    assert result["errors"] == []
    assert Organization.objects.filter(national_id="111").exists()


def test_pharmacy_import_and_profile():
    org, profile, created = upsert_pharmacy_from_row(
        row={
            "gln": "6267930350931",
            "name": "دکتر حسینی",
            "national_id": "8565114571",
            "customer_national_id": "8565114571",
            "university_name": "دانشگاه علوم پزشکی اصفهان",
            "service_type": "روزانه",
            "owner_name": "عاطفه",
            "province": "اصفهان",
        }
    )
    assert created
    assert org.type == Organization.Type.PHARMACY
    assert profile.university_name.startswith("دانشگاه")
    assert PharmacyProfile.objects.filter(organization=org).exists()

    content = _xlsx_bytes(
        [
            "کد GLN",
            "نام دانشگاه",
            "نوع سرویس داروخانه",
            "نوع داروخانه",
            "نام داروخانه",
            "شناسه ملی مشتری",
            "استان",
        ],
        [["6261", "دانشگاه الف", "روزانه", "", "داروخانه ب", "999", "تهران"]],
    )
    result = import_pharmacies_xlsx(file_bytes=content)
    assert result["created"] == 1


def test_medicine_upsert_and_import():
    med, created = upsert_medicine_from_row(
        row={
            "external_id": "16353",
            "name": "ACETAMINOPHEN / CAFFEINE / ASA",
            "atc_code": "N02BE51",
            "access_level": "OTC",
        }
    )
    assert created
    assert Medicine.objects.get(external_id="16353").atc_code == "N02BE51"

    content = _xlsx_bytes(
        ["شناسه", "نام", "کد ATC", "سطح دسترسی"],
        [["16354", "ACETAMINOPHEN", "N02BE01", "OTC"]],
    )
    result = import_medicines_xlsx(file_bytes=content)
    assert result["created"] == 1
    assert result["errors"] == []


def test_invoice_lines_amount_validation():
    from datetime import date

    from apps.invoices.api.serializers import InvoiceSerializer

    issuer = Organization.objects.create(name="الف", type="manufacturer", national_id="11111111111")
    buyer = Organization.objects.create(name="ب", type="pharmacy", national_id="22222222222")
    medicine = Medicine.objects.create(external_id="1", name="Drug")
    payload = {
        "issuer": issuer.pk,
        "buyer": buyer.pk,
        "number": "INV-1",
        "amount": "100.0000",
        "due_date": date.today().isoformat(),
        "lines": [
            {
                "medicine_id": medicine.pk,
                "quantity": "2",
                "unit_price": "50",
                "description": "item",
            }
        ],
    }
    serializer = InvoiceSerializer(data=payload)
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["lines"][0]["line_amount"] == Decimal("100.0000")
