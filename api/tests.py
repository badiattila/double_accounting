from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.utils import timezone

from accounting.models import Account, AccountType, Journal, Transaction, EntryLine
from aiassist.local_model import MODEL_PATH


class APITests(TestCase):
	def setUp(self):
		self.client = APIClient()
		# Accounts & journal
		self.cash = Account.objects.create(code="1000", name="Cash", type=AccountType.ASSET, normal_debit=True)
		self.rev = Account.objects.create(code="4000", name="Revenue", type=AccountType.INCOME, normal_debit=False)
		self.journal = Journal.objects.create(name="GENERAL")
		# Ensure any prior model file removed for deterministic fallback
		if MODEL_PATH.exists():
			MODEL_PATH.unlink()

	def test_predict_endpoint_fallback(self):
		url = reverse("predict-list")  # viewset list/create naming
		resp = self.client.post(url, {"payee": "AMAZON EU", "narrative": "cables", "amount": "12.99"}, format="json")
		self.assertEqual(resp.status_code, status.HTTP_200_OK)
		self.assertIn("account_code", resp.data)
		self.assertIn("confidence", resp.data)
		self.assertEqual(resp.data["account_code"], "5000")  # default fallback

	def test_transaction_serializer_creates_and_posts(self):
		from api.views import TransactionIn  # import inside to avoid polluting global test load
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
		tx = ser.save()  # calls create
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
		self.assertTrue(ser.is_valid(), ser.errors)  # structure valid
		with self.assertRaises(Exception):  # underlying ValidationError bubbles up
			ser.save()
