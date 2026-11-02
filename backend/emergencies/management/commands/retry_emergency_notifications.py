from django.core.management.base import BaseCommand

from emergencies.notifications import (
    retry_failed_emergency_notifications,
)


class Command(BaseCommand):
    help = (
        "Retry failed LifeLine emergency email "
        "notifications."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=25,
            help=(
                "Maximum number of failed emergency "
                "notifications to retry."
            ),
        )

    def handle(self, *args, **options):
        limit = options["limit"]

        if limit <= 0:
            self.stderr.write(
                self.style.ERROR(
                    "The retry limit must be greater than 0."
                )
            )
            return

        self.stdout.write(
            "Checking for failed emergency notifications..."
        )

        try:
            result = (
                retry_failed_emergency_notifications(
                    limit=limit
                )
            )

        except Exception as exc:
            self.stderr.write(
                self.style.ERROR(
                    "Emergency notification retry failed: "
                    f"{exc}"
                )
            )
            raise

        self.stdout.write(
            self.style.SUCCESS(
                "Emergency notification retry completed."
            )
        )

        self.stdout.write(
            f"Found: {result['found']}"
        )

        self.stdout.write(
            f"Sent: {result['sent']}"
        )

        self.stdout.write(
            f"Failed: {result['failed']}"
        )

        self.stdout.write(
            f"Skipped: {result['skipped']}"
        )