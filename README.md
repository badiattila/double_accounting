# Double Accounting Django Project

## Data Model (ORM)

### AccountType
Enum for account types:
- ASSET, LIABILITY, EQUITY, INCOME, EXPENSE, CONTRA_ASSET, CONTRA_LIAB

### Account
| Field        | Type           | Description                                |
|--------------|----------------|--------------------------------------------|
| code         | CharField(20)  | Unique account code                        |
| name         | CharField(120) | Account name                               |
| type         | CharField(12)  | Account type (choices from AccountType)    |
| is_active    | BooleanField   | Is account active                          |
| normal_debit | BooleanField   | True if normal balance is debit            |

### Journal
| Field       | Type           | Description               |
|-------------|----------------|---------------------------|
| name        | CharField(60)  | Unique journal name       |
| description | CharField(200) | Optional description      |

### Transaction
| Field      | Type               | Description                       |
|------------|--------------------|-----------------------------------|
| journal    | ForeignKey(Journal)| Journal for transaction           |
| tx_date    | DateField          | Transaction date                  |
| memo       | CharField(255)     | Optional memo                     |
| created_at | DateTimeField      | Created timestamp                 |
| posted     | BooleanField       | Is transaction posted             |

Validation: Must have at least two lines, debits must equal credits.

### EntryLine
| Field       | Type                   | Description                                |
|-------------|------------------------|--------------------------------------------|
| transaction | ForeignKey(Transaction)| Transaction this line belongs to           |
| account     | ForeignKey(Account)    | Account for entry                          |
| debit       | DecimalField(18,2)     | Debit amount (>=0)                         |
| credit      | DecimalField(18,2)     | Credit amount (>=0)                        |
| description | CharField(255)         | Optional description                       |
| currency    | CharField(3)           | Currency code (default EUR)                |
| base_amount | DecimalField(18,2)     | Signed amount (debit-credit)               |

Constraints: Debit XOR Credit, non-negative amounts, must have debit or credit > 0.

### Balance (optional)
| Field        | Type                 | Description                                |
|--------------|----------------------|--------------------------------------------|
| account      | ForeignKey(Account)  | Account                                    |
| period       | DateField            | First day of month                         |
| debit_total  | DecimalField(18,2)   | Total debits for period                    |
| credit_total | DecimalField(18,2)   | Total credits for period                   |

Unique together: (account, period)


## App Architecture Overview


### 1. `accounting`
**Intent:**
Implements the core **double-entry ledger** logic.

- Models: `Account`, `Journal`, `Transaction`, `EntryLine`, `Balance`
- Enforces invariants: debits = credits, ≥2 lines, no editing posted entries
- Services: posting pipeline, seeding chart of accounts, reporting (Trial Balance, P&L, Balance Sheet)
- This app is the **heart** of the system — everything else feeds into or consumes from it


### 2. `aiassist`
**Intent:**
Houses all **AI/ML functionality** that augments the bookkeeping process.

- Providers: local ML classifier (scikit-learn), optional LLM fallback
- Services: categorize bank transactions into accounts, natural-language → structured transaction, suggesting accounts during manual entry
- Training commands: build/update models based on past posted transactions
- Keeps AI logic **decoupled** from business rules in `accounting`


### 3. `api`
**Intent:**
Exposes a **clean REST API** for external clients and frontends.

- Uses Django REST Framework
- Endpoints:
  - `/api/accounts/`
  - `/api/transactions/`
  - `/api/ai/predict-account/`
- Serializers: validate incoming JSON and pass to services
- Separation of concerns: ensures UI (React, mobile app, CLI) or integrations (bank feeds, external systems) can talk to the ledger without touching Django internals


### 4. `banking`
**Intent:**
Handles **bank statements and reconciliation**.

- Models: `BankTransaction` (raw imports), links to `EntryLine` or `Transaction`
- CSV importers, OFX/MT940 parsers (later)
- Logic: reconciliation of statement lines with posted ledger entries, match suggestions (using `aiassist`)
- Provides the “real-world money” input that eventually becomes double-entry transactions in `accounting`


### 5. `core`
**Intent:**
A **utility app** for shared logic, settings, and extensions that don’t belong in one domain.

- Common mixins (`TimeStampedModel`, `SoftDeleteModel`), reusable validators
- Shared templates, utilities, custom user model (if needed)
- A place for project-wide signals, logging, or integration with other services (email, audit logs)
- Think of it as the **foundation layer** the other apps can import without circularity
