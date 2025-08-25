from decimal import Decimal
from django.db import transaction as dbtx
from django.core.exceptions import ValidationError
from .models import Transaction, EntryLine


def create_and_post_transaction(*, journal, tx_date, memo, lines):
    """
    lines = [{"account": acc_obj, "debit": Decimal("10.00"), "credit": Decimal("0.00"), "description": "..."}, ...]
    """
    with dbtx.atomic():
        tx = Transaction.objects.create(journal=journal, tx_date=tx_date, memo=memo)
        for l in lines:
            EntryLine.objects.create(transaction=tx, **l)
        tx.full_clean()  # enforces Σ(debit)==Σ(credit) and ≥2 lines
        tx.post()
        return tx
