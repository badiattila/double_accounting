"""Accounting reporting helpers.

This module provides simple reporting functions built on the posted
`EntryLine` data: an income statement (profit & loss) over a date range and
a balance sheet snapshot at a point in time. Values are returned as plain
Python dictionaries suitable for JSON serialization by the API layer.

Notes:
- `amount_base` is the raw sum of (debit - credit) for an account.
- `display` applies the account's normal balance: asset/expense accounts
    are shown as positive when they have a debit balance, while liability/
    equity/income accounts are shown inverted so that the human-readable
    sign follows standard accounting presentation.
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Dict, Iterable, Tuple

from accounting.models import EntryLine, Account, AccountType

@dataclass
class LineSum:
    account_id: int
    account_code: str
    account_name: str
    type: str           # AccountType value
    normal_debit: bool
    amount_base: Decimal  # sum(debit - credit) in base currency (your EntryLine fields)
    display: Decimal      # amount as humans expect (normal balance logic)

def _iter_lines(*, start: date | None, end: date) -> Iterable[EntryLine]:
    qs = (EntryLine.objects
          .select_related("account", "transaction")
          .filter(transaction__posted=True, transaction__tx_date__lte=end))
    if start is not None:
        qs = qs.filter(transaction__tx_date__gte=start)
    return qs

def _accumulate(lines: Iterable[EntryLine]) -> Dict[int, LineSum]:
    sums: Dict[int, LineSum] = {}
    for l in lines:
        acc = l.account
        base = (l.debit or Decimal("0")) - (l.credit or Decimal("0"))
        cur = sums.get(acc.id)
        if cur is None:
            cur = LineSum(
                account_id=acc.id,
                account_code=acc.code,
                account_name=acc.name,
                type=acc.type,
                normal_debit=acc.normal_debit,
                amount_base=Decimal("0"),
                display=Decimal("0"),
            )
            sums[acc.id] = cur
        cur.amount_base += base
    # compute display using normal balance
    for s in sums.values():
        s.display = s.amount_base if s.normal_debit else -s.amount_base
    return sums

# ------------ Income Statement (P&L) ------------
def income_statement(*, start: date, end: date) -> dict:
    """
    Produce an income statement (profit & loss) for the inclusive date range
    `start`..`end`.

    Human-oriented description:
    - The income statement aggregates revenue and expense accounts that were
      posted during the period and reports totals and the resulting net income
      (or loss). It answers "how did we perform over this period?".
    - Returned dict contains:
      - `period`: input start/end as strings
      - `income`: list of income account rows (code, name, amount)
      - `expenses`: list of expense account rows
      - `totals`: totals for income, expense and net_income

    Important: only posted transactions are considered.
    """
   
    lines = _iter_lines(start=start, end=end)
    sums = _accumulate(lines)

    inc = [s for s in sums.values() if s.type == AccountType.INCOME]
    exp = [s for s in sums.values() if s.type == AccountType.EXPENSE]

    total_income = sum((s.display for s in inc), Decimal("0"))
    total_expense = sum((s.display for s in exp), Decimal("0"))
    net_income = total_income - total_expense

    return {
        "period": {"start": str(start), "end": str(end)},
        "income": [
            {"code": s.account_code, "name": s.account_name, "amount": str(+s.display)}
            for s in sorted(inc, key=lambda x: x.account_code)
        ],
        "expenses": [
            {"code": s.account_code, "name": s.account_name, "amount": str(+s.display)}
            for s in sorted(exp, key=lambda x: x.account_code)
        ],
        "totals": {
            "income": str(+total_income),
            "expense": str(+total_expense),
            "net_income": str(+net_income),
        },
    }


# ------------ Balance Sheet ------------
def balance_sheet(*, as_of: date) -> dict:
    """
    Produce a balance sheet snapshot as of the `as_of` date.

    Human-oriented description:
    - The balance sheet shows the company's assets, liabilities and equity
      at a single point in time. It combines cumulative posted activity up
      to `as_of` to compute current balances per account.
    - Retained earnings are computed by summing income minus expenses
      cumulatively and included in the equity section.
    - Returned dict contains:
      - `as_of`: the snapshot date
      - `assets`, `liabilities`, `equity`: lists of account rows (code, name, amount)
      - `totals`: aggregated totals and a `balanced` boolean that should be
        True when Assets == Liabilities + Equity.

    Important: only posted transactions are considered.
    """
    # Cumulative up to as_of for all accounts
    cumulative = _accumulate(_iter_lines(start=None, end=as_of))

    assets = [s for s in cumulative.values() if s.type == AccountType.ASSET]
    liabs = [s for s in cumulative.values() if s.type == AccountType.LIABILITY]
    equity = [s for s in cumulative.values() if s.type == AccountType.EQUITY]

    # Retained earnings = cumulative net income up to as_of
    inc = [s for s in cumulative.values() if s.type == AccountType.INCOME]
    exp = [s for s in cumulative.values() if s.type == AccountType.EXPENSE]
    retained = (
        sum((s.display for s in inc), Decimal("0"))
        - sum((s.display for s in exp), Decimal("0"))
    )

    total_assets = sum((s.display for s in assets), Decimal("0"))
    total_liabs = sum((s.display for s in liabs), Decimal("0"))
    total_equity = sum((s.display for s in equity), Decimal("0")) + retained

    # Balance check (A = L + E)
    balance_ok = (total_assets == (total_liabs + total_equity))

    return {
        "as_of": str(as_of),
        "assets": [
            {"code": s.account_code, "name": s.account_name, "amount": str(+s.display)}
            for s in sorted(assets, key=lambda x: x.account_code)
        ],
        "liabilities": [
            {"code": s.account_code, "name": s.account_name, "amount": str(+s.display)}
            for s in sorted(liabs, key=lambda x: x.account_code)
        ],
        "equity": [
            {"code": s.account_code, "name": s.account_name, "amount": str(+s.display)}
            for s in sorted(equity, key=lambda x: x.account_code)
        ]
        + [{"code": "RETAINED", "name": "Retained Earnings", "amount": str(+retained)}],
        "totals": {
            "assets": str(+total_assets),
            "liabilities_plus_equity": str(+(total_liabs + total_equity)),
            "balanced": balance_ok,
        },
    }
