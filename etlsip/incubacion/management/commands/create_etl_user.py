from django.contrib.auth.models import Group, Permission, User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create initial ETL executor user and group with permissions"

    def add_arguments(self, parser) -> None:
        parser.add_argument("username", type=str, help="Username for the ETL executor")
        parser.add_argument("--password", type=str, help="Password (will prompt if not provided)")

    def handle(self, *args, **options) -> None:
        username = options["username"]
        password = options.get("password")

        if not password:
            password = input(f"Enter password for '{username}': ")

        # Create or get group
        group, group_created = Group.objects.get_or_create(name="etl_executor")
        if group_created:
            self.stdout.write(self.style.SUCCESS("✓ Group 'etl_executor' created"))

            # Assign permissions
            permissions = Permission.objects.filter(
                codename__in=[
                    "view_etlrunaudit",
                    "add_etlrunaudit",
                    "change_etlrunaudit",
                ]
            )
            group.permissions.set(permissions)
            self.stdout.write(self.style.SUCCESS(f"✓ Assigned {permissions.count()} permissions to group"))
        else:
            self.stdout.write(self.style.WARNING("ℹ Group 'etl_executor' already exists"))

        # Create or update user
        user, user_created = User.objects.get_or_create(
            username=username,
            defaults={"email": f"{username}@example.com"},
        )
        user.set_password(password)
        user.save()

        if user_created:
            self.stdout.write(self.style.SUCCESS(f"✓ User '{username}' created"))
        else:
            self.stdout.write(self.style.WARNING(f"ℹ User '{username}' already exists (password updated)"))

        # Add user to group
        user.groups.add(group)
        user.save()
        self.stdout.write(self.style.SUCCESS(f"✓ User '{username}' added to group 'etl_executor'"))

        self.stdout.write(self.style.SUCCESS("\n✅ Setup complete! Ready to login."))
        self.stdout.write(f"   Username: {username}\n")
