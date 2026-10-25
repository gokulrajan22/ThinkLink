"""Remove inactive rate-limit buckets; run daily as a scheduled maintenance task."""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import RateLimitBucket


class Command(BaseCommand):
    help = "Delete rate-limit counters that have been inactive for 30 days."

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=30)
        deleted, _ = RateLimitBucket.objects.filter(last_seen_at__lt=cutoff).delete()
        self.stdout.write(self.style.SUCCESS(f"Removed {deleted} expired rate-limit record(s)."))
