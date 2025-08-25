from django.core.management.base import BaseCommand
from accounting.models import Account, AccountType

BASICS = [
    ("1000", "Cash", AccountType.ASSET, True),
    ("1100", "Bank", AccountType.ASSET, True),
    ("1200", "Debtors", AccountType.ASSET, True),
    ("1500", "Furniture", AccountType.ASSET, True),
    ("2000", "Accounts Payable", AccountType.LIABILITY, False),
    ("2100", "Credit Card", AccountType.LIABILITY, False),
    ("3000", "Capital", AccountType.EQUITY, False),
    ("4000", "Sales", AccountType.INCOME, False),
    ("5000", "Office Supplies", AccountType.EXPENSE, True),
    ("5100", "Payroll", AccountType.EXPENSE, True),
    ("5200", "Food", AccountType.EXPENSE, True),
    ("5300", "Depreciation", AccountType.EXPENSE, True),
]


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        for code, name, typ, nd in BASICS:
            Account.objects.get_or_create(
                code=code, defaults={"name": name, "type": typ, "normal_debit": nd}
            )
        self.stdout.write(self.style.SUCCESS("Seeded Chart of Accounts."))
