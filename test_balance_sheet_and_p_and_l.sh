#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

# Simple helper to fetch Income Statement and Balance Sheet from local API
# Usage: ./test_balance_sheet_and_p_and_l.sh [--host HOST] [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--as-of YYYY-MM-DD]

HOST="${HOST:-http://localhost:5005}"
FROM_DATE="${1:-2025-08-01}"
TO_DATE="${2:-2025-08-31}"
AS_OF_DATE="${3:-2025-08-31}"

retry_curl() {
	local url="$1"
	local tries=0
	local max=3
	until curl -sS --fail "$url"; do
		tries=$((tries+1))
		if [ "$tries" -ge "$max" ]; then
			echo "[ERROR] Failed to fetch $url after $max attempts" >&2
			return 1
		fi
		echo "[WARN] Request failed, retrying ($tries/$max)..." >&2
		sleep 1
	done
}

echo "== Income Statement: ${FROM_DATE} → ${TO_DATE} =="
URL_IS="${HOST%/}/api/reports/income-statement/?from=${FROM_DATE}&to=${TO_DATE}"
retry_curl "$URL_IS" || exit 1

echo
echo "== Balance Sheet as of ${AS_OF_DATE} =="
URL_BS="${HOST%/}/api/reports/balance-sheet/?as_of=${AS_OF_DATE}"
retry_curl "$URL_BS" || exit 1

echo
echo "Done. Above are the two reports fetched from ${HOST}."

