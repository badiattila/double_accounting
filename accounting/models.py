from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import models, transaction as dbtx
from django.utils import timezone

class AccountType(models.TextChoices):
    ASSET="ASSET","Asset"
    LIABILITY="LIAB","Liability"
    EQUITY="EQTY","Equity"
    INCOME="INC","Income"
    EXPENSE="EXP","Expense"
    CONTRA_ASSET="C_ASSET","Contra Asset"
    CONTRA_LIAB="C_LIAB","Contra Liability"

class Account(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=120)
    type = models.CharField(max_length=12, choices=AccountType.choices)
    is_active = models.BooleanField(default=True)
    # Normal balance direction helps reporting
    normal_debit = models.BooleanField()  # True=debit-normal (Assets/Expenses), False=credit-normal

    class Meta:
        ordering = ["code"]

    def __str__(self): return f"{self.code} · {self.name}"

class Journal(models.Model):
    name = models.CharField(max_length=60, unique=True)
    description = models.CharField(max_length=200, blank=True, default="")

    def __str__(self): return self.name

class Transaction(models.Model):
    journal = models.ForeignKey(Journal, on_delete=models.PROTECT)
    tx_date = models.DateField(default=timezone.now)
    memo = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    posted = models.BooleanField(default=False)

    def clean(self):
        lines = list(self.lines.all())
        if len(lines) < 2:
            raise ValidationError("A transaction must have at least two lines.")
        deb = sum((l.debit for l in lines), Decimal("0.00"))
        cred = sum((l.credit for l in lines), Decimal("0.00"))
        if deb != cred:
            raise ValidationError(f"Unbalanced transaction: debits {deb} != credits {cred}")

    def post(self):
        from django.db.models import F
        with dbtx.atomic():
            self.full_clean()
            self.posted = True
            self.save(update_fields=["posted"])
            # Optionally update running balances table here (see Balance model below)

class EntryLine(models.Model):
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name="lines")
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="entries")
    # Use positive decimals; enforce debit XOR credit
    debit = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0.00"))
    credit = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0.00"))
    description = models.CharField(max_length=255, blank=True)
    currency = models.CharField(max_length=3, default="EUR")
    base_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0.00"))  # +/- signed

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=~(models.Q(debit__gt=0) & models.Q(credit__gt=0)),
                name="debit_xor_credit"
            ),
            models.CheckConstraint(
                check=models.Q(debit__gte=0) & models.Q(credit__gte=0),
                name="non_negative_amounts"
            ),
        ]

    def clean(self):
        if (self.debit == 0) and (self.credit == 0):
            raise ValidationError("Line must have either debit or credit > 0.")
        # Base amount signed for quick aggregation (debits positive, credits negative)
        self.base_amount = self.debit - self.credit

    def save(self, *args, **kwargs):
        # Ensure base_amount always consistent even if full_clean not called upstream
        self.base_amount = (self.debit or Decimal("0.00")) - (self.credit or Decimal("0.00"))
        super().save(*args, **kwargs)

# (Optional) Denormalized balances for fast reports
class Balance(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    period = models.DateField()  # first day of month
    debit_total = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0.00"))
    credit_total = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        unique_together = [("account", "period")]
