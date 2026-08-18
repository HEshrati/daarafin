from django.core.management.base import BaseCommand

from apps.organizations.services import DEFAULT_ROLE_SCOPES


class Command(BaseCommand):
    help = "Validate and print the six canonical role/scope seeds."

    def handle(self, *args, **options):
        for role, scopes in DEFAULT_ROLE_SCOPES.items():
            self.stdout.write(f"{role}: {','.join(scopes)}")
