from datetime import date
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework import status

from accounting.reporting import income_statement, balance_sheet

def _parse_date(s: str) -> date:
    return date.fromisoformat(s)

@api_view(["GET"])
@permission_classes([IsAuthenticatedOrReadOnly])
def income_statement_view(request):
    """Return an income statement (profit & loss) for the requested period.

    The income statement summarizes revenues and expenses over a time range
    and shows the resulting net profit or loss for that period.
    """
    start = request.query_params.get("from")
    end = request.query_params.get("to")
    if not start or not end:
        return Response({"detail": "Query params 'from' and 'to' (YYYY-MM-DD) are required."},
                        status=status.HTTP_400_BAD_REQUEST)
    data = income_statement(start=_parse_date(start), end=_parse_date(end))
    return Response(data)

@api_view(["GET"])
@permission_classes([IsAuthenticatedOrReadOnly])
def balance_sheet_view(request):
    """Return a balance sheet as of the requested date.

    The balance sheet reports assets, liabilities and equity at a specific
    point in time and verifies the accounting equation: Assets = Liabilities + Equity.
    """
    as_of = request.query_params.get("as_of")
    if not as_of:
        return Response({"detail": "Query param 'as_of' (YYYY-MM-DD) is required."},
                        status=status.HTTP_400_BAD_REQUEST)
    data = balance_sheet(as_of=_parse_date(as_of))
    return Response(data)
