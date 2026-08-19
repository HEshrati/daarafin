import factory

from apps.identity.models import User


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user{n}")
    password = factory.PostGenerationMethodCall("set_password", "correct-password")

    @classmethod
    def _after_postgeneration(cls, instance, create, results=None):
        if create:
            instance.save()
