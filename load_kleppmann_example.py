#!/usr/bin/env python3
"""
Load the transactions described in:
  Martin Kleppmann, "Accounting for Computer Scientists" (2011-03-07)
  https://martin.kleppmann.com/2011/03/07/accounting-for-computer-scientists.html

This script calls the DRF endpoint: POST {API}/api/transactions/
and creates the example transactions in the specified journal.

Usage:
  python load_kleppmann_example.py --api http://localhost:8008 --user alice --password secret [--journal General]

Prereqs:
  - Your API is running and reachable.
  - Accounts with the codes below exist (or adjust to yours).
"""

import argparse
import sys
import requests
from datetime import date

# ---- Adjust these if your codes differ ----
ACCOUNTS = {
    "BANK": "1100",          # Asset
    "CREDIT_CARD": "2100",   # Liability
    "DEBTORS": "1200",       # Asset (Accounts Receivable)
    "FURNITURE": "1500",     # Asset
    "CAPITAL": "3000",       # Equity (Owner's Equity/Capital)
    "SALES": "4000",         # Income (Revenue)
    "PAYROLL": "5100",       # Expense
    "FOOD": "5200",          # Expense
    "DEPRECIATION": "5300",  # Expense
}

def must_have_accounts(api, auth):
    """Fetch /api/accounts/ and ensure all required codes exist."""
    url = f"{api.rstrip('/')}/api/accounts/?page_size=10000"
    r = requests.get(url, auth=auth, timeout=30)
    r.raise_for_status()
    try:
        data = r.json()
    except ValueError:
        raise RuntimeError("Accounts endpoint did not return valid JSON")

    # Support DRF paginated responses (dict with 'results') and plain list responses
    if isinstance(data, dict):
        entries = data.get("results") if "results" in data else data.get("data", None)
        # If still None, the dict might itself be a single account or unexpected shape
        if entries is None:
            # try interpreting the dict as a mapping of code->... or fail fast
            # collect any nested dicts that look like account entries
            possible = []
            for v in data.values():
                if isinstance(v, list):
                    possible.extend(v)
            if possible:
                entries = possible
            else:
                raise RuntimeError("Unexpected JSON shape from accounts endpoint")
    elif isinstance(data, list):
        entries = data
    else:
        raise RuntimeError("Unexpected JSON type from accounts endpoint")

    got = set()
    for a in entries:
        if isinstance(a, dict) and "code" in a:
            got.add(a["code"])

    missing = [code for code in ACCOUNTS.values() if code not in got]
    return missing

def post_tx(api, auth, journal, tx_date, memo, lines):
    """POST one transaction."""
    url = f"{api.rstrip('/')}/api/transactions/"
    payload = {
        "journal": journal,
        "tx_date": tx_date.isoformat(),
        "memo": memo,
        "lines": lines,
    }
    r = requests.post(url, json=payload, auth=auth, timeout=30)
    if r.status_code >= 400:
        raise RuntimeError(f"POST failed {r.status_code}: {r.text}")
    return r.json()

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--api", required=True, help="Base URL, e.g. http://localhost:8008")
    p.add_argument("--user", required=True)
    p.add_argument("--password", required=True)
    p.add_argument("--journal", default="General")
    p.add_argument("--date", default=date.today().isoformat(), help="Posting date (YYYY-MM-DD) used for all entries")
    args = p.parse_args()

    auth = (args.user, args.password)
    # 1) Preflight: ensure accounts exist
    missing = must_have_accounts(args.api, auth)
    if missing:
        print("ERROR: The following required account codes are missing in your CoA:")
        print("  " + ", ".join(missing))
        print("Create them in Admin (or change the mapping in this script), then re-run.")
        sys.exit(2)

    D = lambda code, amt, desc="": {"account_code": code, "debit": f"{amt:.2f}", "credit": "0.00", "description": desc}
    C = lambda code, amt, desc="": {"account_code": code, "debit": "0.00", "credit": f"{amt:.2f}", "description": desc}
    day = date.fromisoformat(args.date)

    created = []

    # --- Transactions per the article ---

    # 1) Buy bagel $5 on company credit card (expense via card) [FOOD, CREDIT_CARD]
    created.append(post_tx(
        args.api, auth, args.journal, day,
        "Bagel on company credit card ($5)",
        [D(ACCOUNTS["FOOD"], 5.00, "bagel"), C(ACCOUNTS["CREDIT_CARD"], 5.00, "bagel")]
    ))

    # 2) Buy chair $500 by cheque from the company bank account (asset purchase) [FURNITURE, BANK]
    created.append(post_tx(
        args.api, auth, args.journal, day,
        "Aeron chair paid from bank ($500)",
        [D(ACCOUNTS["FURNITURE"], 500.00, "chair"), C(ACCOUNTS["BANK"], 500.00, "chair")]
    ))

    # 3) Pay the $5 credit card bill from the bank [CREDIT_CARD, BANK]
    created.append(post_tx(
        args.api, auth, args.journal, day,
        "Pay credit card bill ($5)",
        [D(ACCOUNTS["CREDIT_CARD"], 5.00, "card bill"), C(ACCOUNTS["BANK"], 5.00, "card bill")]
    ))

    # 4) Founder puts $5,000 to start the company (capital) [BANK, CAPITAL]
    created.append(post_tx(
        args.api, auth, args.journal, day,
        "Founder capital $5,000",
        [D(ACCOUNTS["BANK"], 5000.00, "founder capital"), C(ACCOUNTS["CAPITAL"], 5000.00, "founder capital")]
    ))

    # 5) Customer 1 sale $5,000, paid immediately [BANK, SALES]
    created.append(post_tx(
        args.api, auth, args.journal, day,
        "Customer 1 sale, paid immediately ($5,000)",
        [D(ACCOUNTS["BANK"], 5000.00, "sale C1"), C(ACCOUNTS["SALES"], 5000.00, "sale C1")]
    ))

    # 6) Customer 2: sell $5,000 on credit (A/R), then take $2,500 upfront
    # 6a) Recognize the sale on credit [DEBTORS, SALES]
    created.append(post_tx(
        args.api, auth, args.journal, day,
        "Customer 2 sale on credit ($5,000)",
        [D(ACCOUNTS["DEBTORS"], 5000.00, "sale C2"), C(ACCOUNTS["SALES"], 5000.00, "sale C2")]
    ))
    # 6b) Receive partial payment $2,500 [BANK, DEBTORS]
    created.append(post_tx(
        args.api, auth, args.journal, day,
        "Customer 2 partial payment ($2,500)",
        [D(ACCOUNTS["BANK"], 2500.00, "C2 upfront"), C(ACCOUNTS["DEBTORS"], 2500.00, "C2 upfront")]
    ))

    # 7) YC investment $20,000 (equity) [BANK, CAPITAL]
    created.append(post_tx(
        args.api, auth, args.journal, day,
        "YC investment $20,000",
        [D(ACCOUNTS["BANK"], 20000.00, "YC"), C(ACCOUNTS["CAPITAL"], 20000.00, "YC")]
    ))

    # 8) Payroll (salary) $8,000 paid out of bank [PAYROLL, BANK]
    created.append(post_tx(
        args.api, auth, args.journal, day,
        "Payroll $8,000",
        [D(ACCOUNTS["PAYROLL"], 8000.00, "salary"), C(ACCOUNTS["BANK"], 8000.00, "salary")]
    ))

    # 9) Depreciation: one year on $500 chair -> $125 [DEPRECIATION, FURNITURE]
    created.append(post_tx(
        args.api, auth, args.journal, day,
        "Depreciation of chair (1 year) $125",
        [D(ACCOUNTS["DEPRECIATION"], 125.00, "depr chair"), C(ACCOUNTS["FURNITURE"], 125.00, "depr chair")]
    ))

    print(f"Created {len(created)} transactions successfully.")
    for t in created:
        print(f"- Tx {t['id']}: {t['memo']} (posted={t['posted']})")

if __name__ == "__main__":
    main()
