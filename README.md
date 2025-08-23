
# Double Accounting Django Project

## Data Model (ORM)

### AccountType
Enum for account types:
- ASSET, LIABILITY, EQUITY, INCOME, EXPENSE, CONTRA_ASSET, CONTRA_LIAB

### Account
| Field         | Type           | Description                                 |
|-------------- |--------------- |---------------------------------------------|
| code          | CharField(20)  | Unique account code                         |
| name          | CharField(120) | Account name                                |
| type          | CharField(12)  | Account type (choices from AccountType)      |
| is_active     | BooleanField   | Is account active                           |
| normal_debit  | BooleanField   | True if normal balance is debit              |

### Journal
| Field       | Type           | Description                |
|------------ |--------------- |---------------------------|
| name        | CharField(60)  | Unique journal name        |
| description | CharField(200) | Optional description       |

### Transaction
| Field      | Type              | Description                        |
|----------- |------------------ |------------------------------------|
| journal    | ForeignKey(Journal)| Journal for transaction            |
| tx_date    | DateField         | Transaction date                   |
| memo       | CharField(255)    | Optional memo                      |
| created_at | DateTimeField     | Created timestamp                  |
| posted     | BooleanField      | Is transaction posted              |

Validation: Must have at least two lines, debits must equal credits.

### EntryLine
| Field        | Type                  | Description                                 |
|------------- |---------------------- |---------------------------------------------|
| transaction  | ForeignKey(Transaction)| Transaction this line belongs to            |
| account      | ForeignKey(Account)   | Account for entry                           |
| debit        | DecimalField(18,2)    | Debit amount (>=0)                          |
| credit       | DecimalField(18,2)    | Credit amount (>=0)                         |
| description  | CharField(255)        | Optional description                        |
| currency     | CharField(3)          | Currency code (default EUR)                 |
| base_amount  | DecimalField(18,2)    | Signed amount (debit-credit)                |

Constraints: Debit XOR Credit, non-negative amounts, must have debit or credit > 0.

### Balance (optional)
| Field        | Type                  | Description                                 |
|------------- |---------------------- |---------------------------------------------|
| account      | ForeignKey(Account)   | Account                                     |
| period       | DateField             | First day of month                          |
| debit_total  | DecimalField(18,2)    | Total debits for period                     |
| credit_total | DecimalField(18,2)    | Total credits for period                    |

Unique together: (account, period)
