import os
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.facilities.models import Facility
from apps.financing.models import FinancingRequest
from apps.financing.services import (
    approve_request,
    create_quote,
    disburse_request,
    submit_request,
)
from apps.identity.models import User
from apps.invoices.models import Invoice
from apps.organizations.models import BankAccount, Organization, UserMembership
from apps.organizations.services import DEFAULT_ROLE_SCOPES


class Command(BaseCommand):
    help = "Create an idempotent local dataset for the initial Darafin demo."

    def add_arguments(self, parser):
        parser.add_argument("--password", default=os.environ.get("DEMO_USER_PASSWORD"))

    @transaction.atomic
    def handle(self, *args, **options):
        password = options["password"]
        if not password:
            raise CommandError("--password or DEMO_USER_PASSWORD is required")

        maker = self._user("demo-maker", "maker@demo.darafin.local", password)
        distributor_user = self._user(
            "demo-distributor", "distributor@demo.darafin.local", password
        )
        pharmacy_user = self._user("demo-pharmacy", "pharmacy@demo.darafin.local", password)
        approver = self._user("demo-approver", "approver@demo.darafin.local", password)
        finance_user = self._user("demo-finance", "finance@demo.darafin.local", password)

        lender = self._organization(
            name="بانک توسعه دارافین",
            organization_type=Organization.Type.BANK,
            national_id="14050000001",
        )
        borrower = self._organization(
            name="داروسازی سپهر",
            organization_type=Organization.Type.MANUFACTURER,
            national_id="14050000002",
        )
        distributor = self._organization(
            name="پخش دارویی آریا",
            organization_type=Organization.Type.DISTRIBUTOR,
            national_id="14050000004",
        )
        buyer = self._organization(
            name="شبکه داروخانه سلامت",
            organization_type=Organization.Type.PHARMACY,
            national_id="14050000003",
        )
        insurers = [
            self._organization(
                name="سازمان تأمین اجتماعی",
                organization_type=Organization.Type.INSURANCE,
                national_id="14050000101",
                province="تهران",
                city="تهران",
                phone="021-64501",
                email="demo-tamin@darafin.local",
                risk_tier=1,
            ),
            self._organization(
                name="سازمان بیمه سلامت ایران",
                organization_type=Organization.Type.INSURANCE,
                national_id="14050000102",
                province="تهران",
                city="تهران",
                phone="021-1666",
                email="demo-salamat@darafin.local",
                risk_tier=1,
            ),
            self._organization(
                name="بیمه خدمات درمانی نیروهای مسلح",
                organization_type=Organization.Type.INSURANCE,
                national_id="14050000103",
                province="تهران",
                city="تهران",
                phone="021-81261",
                email="demo-sakhad@darafin.local",
                risk_tier=2,
            ),
            self._organization(
                name="بیمه دانا",
                organization_type=Organization.Type.INSURANCE,
                national_id="14050000104",
                province="تهران",
                city="تهران",
                phone="021-8304",
                email="demo-dana@darafin.local",
                risk_tier=2,
            ),
        ]

        self._membership(maker, borrower, UserMembership.Role.OWNER)
        self._membership(distributor_user, distributor, UserMembership.Role.OWNER)
        self._membership(pharmacy_user, buyer, UserMembership.Role.OWNER)
        self._membership(approver, lender, UserMembership.Role.APPROVER)
        self._membership(finance_user, lender, UserMembership.Role.BANK_FINANCE)

        bank_account, _ = BankAccount.objects.get_or_create(
            organization=borrower,
            iban="IR140000000000000000000001",
            defaults={"is_active": True},
        )
        distributor_account, _ = BankAccount.objects.get_or_create(
            organization=distributor,
            iban="IR140000000000000000000002",
            defaults={"is_active": True},
        )
        facility, _ = Facility.objects.get_or_create(
            lender=lender,
            borrower=borrower,
            defaults={
                "limit": Decimal("5000000000.0000"),
                "expiry": timezone.localdate() + timedelta(days=180),
            },
        )
        distributor_facility, _ = Facility.objects.get_or_create(
            lender=lender,
            borrower=distributor,
            defaults={
                "limit": Decimal("2500000000.0000"),
                "expiry": timezone.localdate() + timedelta(days=180),
            },
        )

        invoice_specs = [
            ("DF-DEMO-001", "1200000000.0000", FinancingRequest.Status.QUOTED),
            ("DF-DEMO-002", "900000000.0000", FinancingRequest.Status.REQUESTED),
            ("DF-DEMO-003", "1100000000.0000", FinancingRequest.Status.APPROVED),
            ("DF-DEMO-004", "800000000.0000", FinancingRequest.Status.DISBURSED),
        ]
        for index, (number, amount, target) in enumerate(invoice_specs, start=1):
            invoice, _ = Invoice.objects.get_or_create(
                issuer=borrower,
                number=number,
                defaults={
                    "buyer": buyer,
                    "amount": Decimal(amount),
                    "due_date": timezone.localdate() + timedelta(days=30 + index * 15),
                    "status": Invoice.Status.VERIFIED,
                    "created_by": maker,
                },
            )
            if target != FinancingRequest.Status.QUOTED:
                self._seed_request(
                    invoice=invoice,
                    target=target,
                    facility=facility,
                    bank_account=bank_account,
                    maker=maker,
                    approver=approver,
                    finance_user=finance_user,
                )

        distributor_invoice, _ = Invoice.objects.get_or_create(
            issuer=distributor,
            number="DF-DEMO-DIST-001",
            defaults={
                "buyer": buyer,
                "amount": Decimal("650000000.0000"),
                "due_date": timezone.localdate() + timedelta(days=45),
                "status": Invoice.Status.VERIFIED,
                "created_by": distributor_user,
            },
        )
        self._seed_request(
            invoice=distributor_invoice,
            target=FinancingRequest.Status.REQUESTED,
            facility=distributor_facility,
            bank_account=distributor_account,
            maker=distributor_user,
            approver=approver,
            finance_user=finance_user,
        )

        display_invoice_specs = [
            (
                borrower,
                insurers[0],
                maker,
                "DF-DEMO-101",
                "185000000.0000",
                12,
                Invoice.Status.DRAFT,
            ),
            (
                borrower,
                insurers[1],
                maker,
                "DF-DEMO-102",
                "420000000.0000",
                20,
                Invoice.Status.SUBMITTED,
            ),
            (
                borrower,
                insurers[2],
                maker,
                "DF-DEMO-103",
                "730000000.0000",
                35,
                Invoice.Status.VERIFIED,
            ),
            (
                borrower,
                insurers[3],
                maker,
                "DF-DEMO-104",
                "265000000.0000",
                48,
                Invoice.Status.DISPUTED,
            ),
            (
                borrower,
                buyer,
                maker,
                "DF-DEMO-105",
                "980000000.0000",
                60,
                Invoice.Status.FINANCED,
            ),
            (
                distributor,
                buyer,
                distributor_user,
                "DF-DEMO-DIST-102",
                "315000000.0000",
                25,
                Invoice.Status.SUBMITTED,
            ),
            (
                distributor,
                insurers[0],
                distributor_user,
                "DF-DEMO-DIST-103",
                "540000000.0000",
                40,
                Invoice.Status.VERIFIED,
            ),
            (
                distributor,
                insurers[1],
                distributor_user,
                "DF-DEMO-DIST-104",
                "225000000.0000",
                55,
                Invoice.Status.DISPUTED,
            ),
        ]
        for (
            issuer,
            invoice_buyer,
            creator,
            number,
            amount,
            due_in_days,
            invoice_status,
        ) in display_invoice_specs:
            Invoice.objects.get_or_create(
                issuer=issuer,
                number=number,
                defaults={
                    "buyer": invoice_buyer,
                    "amount": Decimal(amount),
                    "due_date": timezone.localdate() + timedelta(days=due_in_days),
                    "status": invoice_status,
                    "created_by": creator,
                },
            )

        self.stdout.write(self.style.SUCCESS("Darafin demo data is ready."))
        self.stdout.write(
            "Users: demo-maker, demo-distributor, demo-pharmacy, demo-approver, demo-finance"
        )

    def _user(self, username, email, password):
        user, _ = User.objects.get_or_create(username=username, defaults={"email": email})
        user.email = email
        user.set_password(password)
        user.save(update_fields=("email", "password"))
        return user

    def _organization(self, *, name, organization_type, national_id, **profile):
        organization, _ = Organization.objects.update_or_create(
            national_id=national_id,
            defaults={"name": name, "type": organization_type, **profile},
        )
        return organization

    def _membership(self, user, organization, role):
        UserMembership.objects.update_or_create(
            user=user,
            organization=organization,
            role=role,
            defaults={"scopes": DEFAULT_ROLE_SCOPES[role].copy(), "is_active": True},
        )

    def _seed_request(
        self, *, invoice, target, facility, bank_account, maker, approver, finance_user
    ):
        if invoice.financing_requests.exists():
            return
        quote = create_quote(
            actor=maker,
            invoice_ids=[invoice.pk],
            amount=invoice.amount,
            term_days=60,
            correlation_id="demo-seed",
        )
        request = submit_request(
            request=quote.request,
            facility_id=facility.pk,
            key=f"demo-submit-{invoice.pk}",
            actor=maker,
            correlation_id="demo-seed",
        )
        if target in {FinancingRequest.Status.APPROVED, FinancingRequest.Status.DISBURSED}:
            request = approve_request(
                request=request,
                key=f"demo-approve-{invoice.pk}",
                actor=approver,
                correlation_id="demo-seed",
            )
        if target == FinancingRequest.Status.DISBURSED:
            disburse_request(
                request=request,
                bank_account_id=bank_account.pk,
                key=f"demo-disburse-{invoice.pk}",
                actor=finance_user,
                correlation_id="demo-seed",
            )
