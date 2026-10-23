"""Create a portal administrator from environment-supplied credentials."""
import os
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    """Create one staff account without embedding credentials in source."""
    help = 'Create an administrator from ADMIN_LOGIN and ADMIN_PASSWORD'

    def handle(self, *args, **options):
        """Validate environment and create an idempotent staff account."""
        username = os.getenv('ADMIN_LOGIN', '')
        password = os.getenv('ADMIN_PASSWORD', '')
        if len(username) < 6 or len(password) < 12:
            raise CommandError('Set ADMIN_LOGIN (6+ chars) and ADMIN_PASSWORD (12+ chars)')
        if User.objects.filter(username=username).exists():
            raise CommandError('Admin login already exists')
        User.objects.create_user(username=username, password=password, is_staff=True)
        self.stdout.write(self.style.SUCCESS('Administrator created'))
