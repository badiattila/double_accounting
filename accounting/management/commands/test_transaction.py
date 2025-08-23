from django.core.management.base import BaseCommand
from datetime import date
from decimal import Decimal
from accounting.models import Account, Journal
from accounting.services import create_and_post_transaction

class Command(BaseCommand):
    help = "Create and post a sample transaction"

    def handle(self, *args, **opts):
        j, _ = Journal.objects.get_or_create(name="General")
        cash = Account.objects.get(code="1000")
        sales = Account.objects.get(code="4000")
        tx = create_and_post_transaction(
            journal=j, tx_date=date.today(), memo="Test sale",
            lines=[
                {"account": cash, "debit": Decimal("100.00"), "credit": Decimal("0.00")},
                {"account": sales, "debit": Decimal("0.00"), "credit": Decimal("100.00")},
            ],
        )
        self.stdout.write(self.style.SUCCESS(f"Posted: {tx.pk}"))
