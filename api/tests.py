from decimal import Decimal
from datetime import date
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.utils import timezone

from accounting.models import Account, AccountType, Journal, Transaction
from accounting.services import create_and_post_transaction
from aiassist.local_model import MODEL_PATH


class APITests(TestCase):
	"""API-level tests for prediction and transaction creation."""

	def setUp(self):
		self.client = APIClient()
		# Accounts & journal
		self.cash = Account.objects.create(code="1000", name="Cash", type=AccountType.ASSET, normal_debit=True)
		self.rev = Account.objects.create(code="4000", name="Revenue", type=AccountType.INCOME, normal_debit=False)
		self.journal = Journal.objects.create(name="GENERAL")

		# Ensure deterministic fallback behaviour for AI predictor
		if MODEL_PATH.exists():
			MODEL_PATH.unlink()

	def test_predict_endpoint_fallback(self):
		url = reverse("predict-list")
		resp = self.client.post(url, {"payee": "AMAZON EU", "narrative": "cables", "amount": "12.99"}, format="json")
		self.assertEqual(resp.status_code, status.HTTP_200_OK)
		self.assertIn("account_code", resp.data)
		self.assertIn("confidence", resp.data)
		self.assertEqual(resp.data["account_code"], "5000")  # default fallback

	def test_transaction_serializer_creates_and_posts(self):
		from api.views import TransactionIn

		payload = {
			"journal": "GENERAL",
			"tx_date": timezone.now().date(),
			"memo": "Sale",
			"lines": [
				{"account_code": "1000", "debit": "25.00", "credit": "0.00", "description": "Cash in"},
				{"account_code": "4000", "debit": "0.00", "credit": "25.00", "description": "Revenue"},
			],
		}

		ser = TransactionIn(data=payload)
		self.assertTrue(ser.is_valid(), ser.errors)
		tx = ser.save()
		self.assertTrue(tx.posted)
		self.assertEqual(tx.lines.count(), 2)
		self.assertEqual(Transaction.objects.count(), 1)

	def test_transaction_serializer_rejects_unbalanced(self):
		from api.views import TransactionIn

		bad_payload = {
			"journal": "GENERAL",
			"tx_date": timezone.now().date(),
			"lines": [
				{"account_code": "1000", "debit": "10.00", "credit": "0.00"},
				{"account_code": "4000", "debit": "0.00", "credit": "9.00"},
			],
		}

		ser = TransactionIn(data=bad_payload)
		self.assertTrue(ser.is_valid(), ser.errors)
		with self.assertRaises(Exception):
			ser.save()


class ReportTests(TestCase):
	"""Simple integration tests for reporting endpoints."""

	def setUp(self):
		self.client = APIClient()
		self.journal, _ = Journal.objects.get_or_create(name="GENERAL")
		self.bank = Account.objects.create(code="1100", name="Bank", type=AccountType.ASSET, normal_debit=True)
		self.sales = Account.objects.create(code="4000", name="Sales", type=AccountType.INCOME, normal_debit=False)
		self.food = Account.objects.create(code="5200", name="Food", type=AccountType.EXPENSE, normal_debit=True)

		# Create a sale (bank debit, sales credit)
		create_and_post_transaction(
			journal=self.journal,
			tx_date=date(2025, 8, 10),
			memo="Sale",
			lines=[
				{"account": self.bank, "debit": Decimal("100.00"), "credit": Decimal("0.00")},
				{"account": self.sales, "debit": Decimal("0.00"), "credit": Decimal("100.00")},
			],
		)

		# Create an expense (food debit, bank credit)
		create_and_post_transaction(
			journal=self.journal,
			tx_date=date(2025, 8, 11),
			memo="Bagel",
			lines=[
				{"account": self.food, "debit": Decimal("30.00"), "credit": Decimal("0.00")},
				{"account": self.bank, "debit": Decimal("0.00"), "credit": Decimal("30.00")},
			],
		)

	def test_income_statement(self):
		url = reverse("report-income-statement") + "?from=2025-08-01&to=2025-08-31"
		r = self.client.get(url)
		self.assertEqual(r.status_code, status.HTTP_200_OK)
		self.assertEqual(Decimal(r.data["totals"]["income"]), Decimal("100.00"))
		self.assertEqual(Decimal(r.data["totals"]["expense"]), Decimal("30.00"))
		self.assertEqual(Decimal(r.data["totals"]["net_income"]), Decimal("70.00"))

	def test_balance_sheet(self):
		url = reverse("report-balance-sheet") + "?as_of=2025-08-31"
		r = self.client.get(url)
		self.assertEqual(r.status_code, status.HTTP_200_OK)
		totals = r.data["totals"]
		self.assertTrue(totals.get("balanced", False))
