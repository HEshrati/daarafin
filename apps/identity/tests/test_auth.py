import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.identity.models import User

from .factories import UserFactory

pytestmark = pytest.mark.django_db


def test_user_can_be_created():
    user: User = UserFactory(email="user@example.com")  # type: ignore[assignment]
    assert user.check_password("correct-password")


def test_valid_credentials_return_token():
    user = UserFactory()
    response = APIClient().post(
        reverse("token"), {"username": user.username, "password": "correct-password"}
    )
    assert response.status_code == 200 and "access" in response.data


def test_refresh_token_returns_new_access_token():
    user = UserFactory()
    client = APIClient()
    tokens = client.post(
        reverse("token"), {"username": user.username, "password": "correct-password"}
    ).data
    response = client.post(reverse("token-refresh"), {"refresh": tokens["refresh"]})
    assert response.status_code == 200 and "access" in response.data


def test_invalid_password_is_rejected():
    user = UserFactory()
    assert (
        APIClient()
        .post(reverse("token"), {"username": user.username, "password": "wrong"})
        .status_code
        == 401
    )


def test_me_requires_authentication():
    assert APIClient().get(reverse("me")).status_code == 401
