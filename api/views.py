from rest_framework import mixins, serializers, viewsets, status
from rest_framework.response import Response
from accounting.models import Account, Transaction, EntryLine, Journal
from accounting.services import create_and_post_transaction
from aiassist.services import predict_account_code
from .serializers import AccountSerializer

class AccountViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = Account.objects.all().order_by("code")
    serializer_class = AccountSerializer

class EntryLineIn(serializers.Serializer):
    account_code = serializers.CharField()
    debit = serializers.DecimalField(max_digits=18, decimal_places=2)
    credit = serializers.DecimalField(max_digits=18, decimal_places=2)
    description = serializers.CharField(allow_blank=True, required=False)

class TransactionIn(serializers.Serializer):
    journal = serializers.CharField()
    tx_date = serializers.DateField()
    memo = serializers.CharField(allow_blank=True, required=False)
    lines = EntryLineIn(many=True)

    def create(self, validated):
        j = Journal.objects.get(name=validated["journal"])
        lines = []
        for l in validated["lines"]:
            acc = Account.objects.get(code=l["account_code"])
            lines.append({"account": acc, "debit": l["debit"], "credit": l["credit"], "description": l.get("description","")})
        return create_and_post_transaction(journal=j, tx_date=validated["tx_date"], memo=validated.get("memo",""), lines=lines)

class TransactionView(viewsets.ViewSet):
    """
    POST /api/transactions/  -> create & post a transaction
    """
    def create(self, request):
        s = TransactionIn(data=request.data)
        s.is_valid(raise_exception=True)
        tx = s.save()  # calls your create()
        # minimal response
        return Response({"id": tx.id, "posted": tx.posted, "memo": tx.memo}, status=status.HTTP_200_OK)

class PredictIn(serializers.Serializer):
    payee = serializers.CharField()
    narrative = serializers.CharField(required=False, allow_blank=True)
    amount = serializers.DecimalField(max_digits=18, decimal_places=2)

class PredictView(viewsets.ViewSet):
    def create(self, request):
        s = PredictIn(data=request.data); s.is_valid(raise_exception=True)
        code, prob = predict_account_code(**s.validated_data)
        return Response({"account_code": code, "confidence": prob})
