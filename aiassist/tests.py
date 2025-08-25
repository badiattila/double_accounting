import os
from decimal import Decimal
from pathlib import Path
from django.test import TestCase, override_settings
from django.core.management import call_command
from django.utils import timezone

from accounting.models import Account, AccountType, Journal, Transaction, EntryLine
from .local_model import MODEL_PATH, train_from_ledger, LocalCategorizer
from .services import predict_account_code


class AIAssistTests(TestCase):
    def setUp(self):
        # Minimal chart for tests
        self.acc_supplies = Account.objects.create(
            code="5000",
            name="Office Supplies",
            type=AccountType.EXPENSE,
            normal_debit=True,
        )
        self.acc_travel = Account.objects.create(
            code="5200", name="Travel", type=AccountType.EXPENSE, normal_debit=True
        )
        self.acc_misc = Account.objects.create(
            code="5999", name="Misc", type=AccountType.EXPENSE, normal_debit=True
        )
        self.journal = Journal.objects.create(name="GENERAL")

    def _make_line(self, account, description: str, amount: Decimal):
        tx = Transaction.objects.create(journal=self.journal, tx_date=timezone.now())
        EntryLine.objects.create(transaction=tx, account=account, debit=amount)
        EntryLine.objects.create(transaction=tx, account=self.acc_misc, credit=amount)
        return tx

    def tearDown(self):
        # Clean up model file if created
        if MODEL_PATH.exists():
            try:
                MODEL_PATH.unlink()
            except OSError:
                pass

    def test_fallback_returns_default_when_no_model(self):
        # Ensure model file absent
        if MODEL_PATH.exists():
            MODEL_PATH.unlink()
        code, conf = predict_account_code(
            payee="AMAZON EU", narrative="cables", amount=Decimal("12.99")
        )
        self.assertEqual(code, "5000")  # defined fallback
        self.assertGreaterEqual(conf, 0)

    def test_training_creates_model_file_and_predicts(self):
        # Generate some training data
        self._make_line(self.acc_supplies, "printer paper", Decimal("30.00"))
        self._make_line(self.acc_supplies, "pens and notebooks", Decimal("15.00"))
        self._make_line(self.acc_travel, "flight ticket", Decimal("300.00"))
        self._make_line(self.acc_travel, "hotel booking", Decimal("450.00"))

        qs = EntryLine.objects.filter(
            account__code__in=["5000", "5200"]
        )  # only the debit lines interest
        train_from_ledger(qs)
        self.assertTrue(MODEL_PATH.exists(), "Model file not created")

        # New predictor should load model
        cat = LocalCategorizer()
        code, conf = cat.predict(
            payee="AMAZON", narrative="notebook bulk", amount=25.00
        )
        self.assertIn(code, ["5000", "5200"])  # should be one of trained classes
        self.assertGreater(conf, 0.0)

    def test_predict_service_with_model(self):
        # Need at least two classes for logistic regression
        self._make_line(self.acc_supplies, "paper", Decimal("10.00"))
        self._make_line(self.acc_travel, "flight", Decimal("120.00"))
        qs = EntryLine.objects.filter(account__code__in=["5000", "5200"])
        train_from_ledger(qs)
        code, conf = predict_account_code(
            payee="paper shop", narrative="office pads", amount=12.0
        )
        self.assertIn(code, ["5000", "5200"])
        self.assertGreater(conf, 0.0)
