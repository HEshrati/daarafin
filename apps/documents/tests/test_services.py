import hashlib
from unittest.mock import Mock, patch

import pytest

from apps.documents.models import Document
from apps.documents.services import complete_upload
from apps.identity.tests.factories import UserFactory
from apps.onboarding.models import OnboardingCase
from apps.organizations.models import Organization
from common.errors import DomainError

pytestmark = pytest.mark.django_db


class FakeBody:
    def __init__(self, content: bytes):
        self.content = content
        self.closed = False

    def iter_chunks(self, chunk_size):
        yield from (
            self.content[index : index + chunk_size]
            for index in range(0, len(self.content), chunk_size)
        )

    def close(self):
        self.closed = True


def make_document():
    user = UserFactory()
    organization = Organization.objects.create(
        name="شرکت سند", type="manufacturer", national_id="50505050505"
    )
    case = OnboardingCase.objects.create(organization=organization, requested_by=user)
    return Document.objects.create(
        onboarding_case=case,
        document_type="registration",
        storage_key="documents/test.pdf",
        uploaded_by=user,
    )


def test_complete_upload_verifies_object_checksum():
    document = make_document()
    content = b"verified document"
    body = FakeBody(content)
    client = Mock()
    client.get_object.return_value = {"Body": body}

    with patch("apps.documents.services.s3_client", return_value=client):
        completed = complete_upload(document=document, checksum=hashlib.sha256(content).hexdigest())

    assert completed.checksum_sha256 == hashlib.sha256(content).hexdigest()
    assert body.closed


def test_complete_upload_rejects_checksum_mismatch():
    document = make_document()
    client = Mock()
    client.get_object.return_value = {"Body": FakeBody(b"actual")}

    with (
        patch("apps.documents.services.s3_client", return_value=client),
        pytest.raises(DomainError),
    ):
        complete_upload(document=document, checksum=hashlib.sha256(b"other").hexdigest())
