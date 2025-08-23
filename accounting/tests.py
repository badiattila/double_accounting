from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Account, AccountType, Journal, Transaction, EntryLine
from .services import create_and_post_transaction


class AccountingModelTests(TestCase):
	def setUp(self):
		self.cash = Account.objects.create(code="1000", name="Cash", type=AccountType.ASSET, normal_debit=True)
		self.rev = Account.objects.create(code="4000", name="Revenue", type=AccountType.INCOME, normal_debit=False)
		self.journal = Journal.objects.create(name="GENERAL")

	def test_entryline_requires_debit_or_credit(self):
		tx = Transaction.objects.create(journal=self.journal, tx_date=timezone.now())
		line = EntryLine(transaction=tx, account=self.cash, debit=Decimal("0.00"), credit=Decimal("0.00"))
		with self.assertRaises(ValidationError):
			line.full_clean()

	def test_entryline_xor_constraint(self):
		tx = Transaction.objects.create(journal=self.journal, tx_date=timezone.now())
		# Both debit & credit > 0 should error via model clean() before DB constraint
		line = EntryLine(transaction=tx, account=self.cash, debit=Decimal("10.00"), credit=Decimal("5.00"))
		with self.assertRaises(ValidationError):
			line.full_clean()

	def test_transaction_needs_two_lines(self):
		tx = Transaction.objects.create(journal=self.journal, tx_date=timezone.now())
		EntryLine.objects.create(transaction=tx, account=self.cash, debit=Decimal("10.00"))
		with self.assertRaises(ValidationError):
			tx.full_clean()

	def test_transaction_balanced_validation(self):
		tx = Transaction.objects.create(journal=self.journal, tx_date=timezone.now())
		EntryLine.objects.create(transaction=tx, account=self.cash, debit=Decimal("10.00"))
		EntryLine.objects.create(transaction=tx, account=self.rev, credit=Decimal("9.99"))
		with self.assertRaises(ValidationError):
			tx.full_clean()

	def test_transaction_success_and_post_sets_flag(self):
		tx_date = timezone.now().date()
		tx = create_and_post_transaction(
			journal=self.journal,
			tx_date=tx_date,
			memo="Sale",
			lines=[
				{"account": self.cash, "debit": Decimal("125.00"), "credit": Decimal("0.00"), "description": "Cash sale"},
				{"account": self.rev, "debit": Decimal("0.00"), "credit": Decimal("125.00"), "description": "Revenue"},
			],
		)
		self.assertTrue(tx.posted)
		self.assertEqual(tx.lines.count(), 2)
		# Ensure base_amount set correctly
		cash_line = tx.lines.get(account=self.cash)
		self.assertEqual(cash_line.base_amount, Decimal("125.00"))
		rev_line = tx.lines.get(account=self.rev)
		self.assertEqual(rev_line.base_amount, Decimal("-125.00"))

	def test_service_rejects_unbalanced(self):
		with self.assertRaises(ValidationError):
			create_and_post_transaction(
				journal=self.journal,
				tx_date=timezone.now().date(),
				memo="Bad",
				lines=[
					{"account": self.cash, "debit": Decimal("10.00"), "credit": Decimal("0.00")},
					{"account": self.rev, "debit": Decimal("0.00"), "credit": Decimal("9.00")},
				],
			)

	def test_service_rejects_single_line(self):
		with self.assertRaises(ValidationError):
			create_and_post_transaction(
				journal=self.journal,
				tx_date=timezone.now().date(),
				memo="Single",
				lines=[
					{"account": self.cash, "debit": Decimal("10.00"), "credit": Decimal("0.00")},
				],
			)

	def test_multiple_transactions_isolated(self):
		t1 = create_and_post_transaction(
			journal=self.journal,
			tx_date=timezone.now().date(),
			memo="T1",
			lines=[
				{"account": self.cash, "debit": Decimal("50.00"), "credit": Decimal("0.00")},
				{"account": self.rev, "debit": Decimal("0.00"), "credit": Decimal("50.00")},
			],
		)
		t2 = create_and_post_transaction(
			journal=self.journal,
			tx_date=timezone.now().date(),
			memo="T2",
			lines=[
				{"account": self.cash, "debit": Decimal("30.00"), "credit": Decimal("0.00")},
				{"account": self.rev, "debit": Decimal("0.00"), "credit": Decimal("30.00")},
			],
		)
		self.assertNotEqual(t1.id, t2.id)
		self.assertTrue(t1.posted and t2.posted)
		self.assertEqual(t1.lines.count(), 2)
		self.assertEqual(t2.lines.count(), 2)

	def test_base_amount_sign_logic(self):
		tx = Transaction.objects.create(journal=self.journal, tx_date=timezone.now())
		debit_line = EntryLine.objects.create(transaction=tx, account=self.cash, debit=Decimal("20.00"))
		credit_line = EntryLine.objects.create(transaction=tx, account=self.rev, credit=Decimal("20.00"))
		# Trigger model clean to populate base_amount
		debit_line.full_clean()
		credit_line.full_clean()
		self.assertEqual(debit_line.base_amount, Decimal("20.00"))
		self.assertEqual(credit_line.base_amount, Decimal("-20.00"))

