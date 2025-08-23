from django.core.management.base import BaseCommand
from accounting.models import EntryLine
from aiassist.local_model import train_from_ledger

class Command(BaseCommand):
    help = "Train or update the local account categorizer model from posted ledger entries"

    def handle(self, *args, **options):
        # Grab only posted entry lines
        qs = EntryLine.objects.filter(transaction__posted=True).select_related("account", "transaction")

        if not qs.exists():
            self.stdout.write(self.style.WARNING("No posted transactions found. Nothing to train on."))
            return

        train_from_ledger(qs)
        self.stdout.write(self.style.SUCCESS(f"Training complete on {qs.count()} entry lines."))
