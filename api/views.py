# api/views.py
from rest_framework import mixins, serializers, viewsets, status
from rest_framework.response import Response
from accounting.models import Account, Transaction, EntryLine, Journal
from accounting.services import create_and_post_transaction
from aiassist.services import predict_account_code
from .serializers import AccountSerializer, JournalSerializer

# --- drf-spectacular imports ---
from drf_spectacular.utils import (
    extend_schema, extend_schema_view,
    OpenApiTypes, OpenApiExample
)

# ======================
# Accounts (read-only)
# ======================
@extend_schema_view(
    list=extend_schema(
        summary="List accounts",
        description="Return the chart of accounts.",
        responses={200: AccountSerializer(many=True)},
        tags=["Accounts"],
        operation_id="accounts_list",
        examples=[
            OpenApiExample(
                "Sample response",
                value=[{"id": 1, "code": "1000", "name": "Cash", "type": "ASSET", "is_active": True, "normal_debit": True}],
            )
        ],
    ),
)
class AccountViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = Account.objects.all().order_by("code")
    serializer_class = AccountSerializer

# ======================
# Journals (create)
# ======================
@extend_schema_view(
    list=extend_schema(
        summary="List journals",
        tags=["Journals"],
        responses={200: JournalSerializer(many=True)},
        examples=[OpenApiExample("Sample", value=[{"id":1,"name":"GENERAL","description":""}])]
    ),
    create=extend_schema(
        summary="Create journal",
        tags=["Journals"],
        request=JournalSerializer,
        responses={201: JournalSerializer},
        examples=[OpenApiExample("Create", request_only=True, value={"name":"BANK","description":"Bank movements"})]
    ),
)
class JournalViewSet(mixins.ListModelMixin,
                     mixins.CreateModelMixin,
                     viewsets.GenericViewSet):
    queryset = Journal.objects.all().order_by("name")
    serializer_class = JournalSerializer

# ======================
# Transactions (create)
# ======================
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
            lines.append({
                "account": acc,
                "debit": l["debit"],
                "credit": l["credit"],
                "description": l.get("description", "")
            })
        return create_and_post_transaction(
            journal=j,
            tx_date=validated["tx_date"],
            memo=validated.get("memo", ""),
            lines=lines
        )

class TransactionMinimalOut(serializers.Serializer):
    id = serializers.IntegerField()
    posted = serializers.BooleanField()
    memo = serializers.CharField()

class TransactionView(viewsets.ViewSet):
    """
    POST /api/transactions/  -> create & post a transaction
    """
    @extend_schema(
        summary="Create & post a transaction",
        description="Creates a balanced journal entry (≥2 lines) and posts it atomically.",
        request=TransactionIn,
        responses={200: TransactionMinimalOut},
        tags=["Transactions"],
        operation_id="transactions_create",
        examples=[
            OpenApiExample(
                "Cash sale 25.00",
                request_only=True,
                value={
                    "journal": "GENERAL",
                    "tx_date": "2025-08-23",
                    "memo": "Sale",
                    "lines": [
                        {"account_code": "1000", "debit": "25.00", "credit": "0.00", "description": "Cash in"},
                        {"account_code": "4000", "debit": "0.00", "credit": "25.00", "description": "Revenue"}
                    ]
                },
            ),
            OpenApiExample(
                "Success response",
                response_only=True,
                value={"id": 123, "posted": True, "memo": "Sale"},
            ),
        ],
    )
    def create(self, request):
        s = TransactionIn(data=request.data)
        s.is_valid(raise_exception=True)
        tx = s.save()
        return Response(TransactionMinimalOut(tx.__dict__).data, status=status.HTTP_200_OK)


# ======================
# Predict (create)
# ======================
class PredictIn(serializers.Serializer):
    payee = serializers.CharField()
    narrative = serializers.CharField(required=False, allow_blank=True)
    amount = serializers.DecimalField(max_digits=18, decimal_places=2)

class PredictOut(serializers.Serializer):
    account_code = serializers.CharField()
    confidence = serializers.FloatField()

@extend_schema_view(
    create=extend_schema(
        summary="Predict account code",
        description="Suggest an account code for a bank/expense line using rules/ML.",
        request=PredictIn,
        responses={200: PredictOut},
        tags=["AI"],
        operation_id="predict_create",
        examples=[
            OpenApiExample(
                "Staples pens",
                request_only=True,
                value={"payee": "STAPLES DUBLIN", "narrative": "pens", "amount": "23.45"},
            ),
            OpenApiExample(
                "Predicted office supplies",
                response_only=True,
                value={"account_code": "5000", "confidence": 0.83},
            ),
        ],
    )
)
class PredictView(viewsets.ViewSet):
    def create(self, request):
        s = PredictIn(data=request.data)
        s.is_valid(raise_exception=True)
        code, prob = predict_account_code(**s.validated_data)
        return Response({"account_code": code, "confidence": prob})
