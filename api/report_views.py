"""API report views for accounting reports.

This module exposes simple GET endpoints to retrieve common accounting
reports: income statement, balance sheet and trial balance. Views accept
ISO date query parameters and return the raw data structures produced by
the accounting.reporting helpers.
"""

from datetime import date
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework import status

from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from accounting.reporting import (
    balance_sheet,
    income_statement,
    trial_balance_as_of,
    trial_balance_period,
)


def _parse_date(s: str) -> date:
    return date.fromisoformat(s)


@extend_schema(
    summary="Income Statement (Profit & Loss)",
    parameters=[
        OpenApiParameter(
            name="from",
            type=OpenApiTypes.DATE,
            location=OpenApiParameter.QUERY,
            required=True,
            description="Start date inclusive (YYYY-MM-DD)",
        ),
        OpenApiParameter(
            name="to",
            type=OpenApiTypes.DATE,
            location=OpenApiParameter.QUERY,
            required=True,
            description="End date inclusive (YYYY-MM-DD)",
        ),
    ],
    responses={200: None},
)
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
        return Response(
            {"detail": "Query params 'from' and 'to' (YYYY-MM-DD) are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    data = income_statement(start=_parse_date(start), end=_parse_date(end))
    return Response(data)


@extend_schema(
    summary="Balance Sheet",
    parameters=[
        OpenApiParameter(
            name="as_of",
            type=OpenApiTypes.DATE,
            location=OpenApiParameter.QUERY,
            required=True,
            description="Point-in-time date (YYYY-MM-DD)",
        ),
    ],
    responses={200: None},
)
@api_view(["GET"])
@permission_classes([IsAuthenticatedOrReadOnly])
def balance_sheet_view(request):
    """Return a balance sheet as of the requested date.

    The balance sheet reports assets, liabilities and equity at a specific
    point in time and verifies the accounting equation: Assets = Liabilities + Equity.
    """
    as_of = request.query_params.get("as_of")
    if not as_of:
        return Response(
            {"detail": "Query param 'as_of' (YYYY-MM-DD) is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    data = balance_sheet(as_of=_parse_date(as_of))
    return Response(data)


@extend_schema(
    summary="Trial Balance",
    description="Provide either `as_of` OR both `from` and `to`.",
    parameters=[
        OpenApiParameter(
            name="as_of",
            type=OpenApiTypes.DATE,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Point-in-time date (YYYY-MM-DD)",
        ),
        OpenApiParameter(
            name="from",
            type=OpenApiTypes.DATE,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Start date inclusive (YYYY-MM-DD)",
        ),
        OpenApiParameter(
            name="to",
            type=OpenApiTypes.DATE,
            location=OpenApiParameter.QUERY,
            required=False,
            description="End date inclusive (YYYY-MM-DD)",
        ),
    ],
    responses={200: None},
)
@api_view(["GET"])
@permission_classes([IsAuthenticatedOrReadOnly])
def trial_balance_view(request):
    """Return a trial balance for either a point in time or a period.

    Use either the `as_of` query parameter (single date) or the pair
    `from` and `to` to request a period. Providing both is an error.
    """
    as_of = request.query_params.get("as_of")
    start = request.query_params.get("from")
    end = request.query_params.get("to")

    if as_of and (start or end):
        return Response(
            {"detail": "Provide either 'as_of' or 'from'+'to', not both."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if as_of:
        data = trial_balance_as_of(as_of=_parse_date(as_of))
        return Response(data)

    if start and end:
        data = trial_balance_period(start=_parse_date(start), end=_parse_date(end))
        return Response(data)

    return Response(
        {"detail": "Required: 'as_of' OR 'from' and 'to' (YYYY-MM-DD)."},
        status=status.HTTP_400_BAD_REQUEST,
    )
