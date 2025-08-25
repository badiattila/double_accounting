# Double Entry Accounting System

A Django-based double-entry bookkeeping system with AI-powered transaction categorization and bank reconciliation capabilities.

## Prerequisites

- Python 3.8+
- PostgreSQL
- Django 4.x
- scikit-learn (for AI categorization)

## Setup

1. **Environment Configuration**
   ```bash
   cp .env.example .env
   # Update .env with your PostgreSQL database connection details
   ```

2. **Database Setup**
   ```bash
   python manage.py migrate
   python manage.py seed_coa                  # Creates the required chart of accounts
   python manage.py createsuperuser           # Create admin user for API access
   ```

3. **Development Server**
   ```bash
   python manage.py runserver localhost:5005
   ```

4. **Load Sample Data**
   ```bash
   python load_kleppmann_example.py --api http://localhost:5005 --user <django_username> --password <django_password> --journal GENERAL
   ```

5. **AI Model Training**
   ```bash
   python manage.py train_categorizer         # Train the transaction categorization model
   python manage.py check_prediction_health   # Validate the trained model
   ```

## Data Model

### AccountType
Enumeration defining account categories:
- ASSET, LIABILITY, EQUITY, INCOME, EXPENSE, CONTRA_ASSET, CONTRA_LIABILITY

### Account
| Field        | Type           | Description                                |
|--------------|----------------|--------------------------------------------|
| code         | CharField(20)  | Unique account code                        |
| name         | CharField(120) | Account name                               |
| type         | CharField(12)  | Account type (from AccountType enum)       |
| is_active    | BooleanField   | Whether account is currently active        |
| normal_debit | BooleanField   | True if account has normal debit balance   |

### Journal
| Field       | Type           | Description               |
|-------------|----------------|---------------------------|
| name        | CharField(60)  | Unique journal identifier |
| description | CharField(200) | Optional description      |

### Transaction
| Field      | Type               | Description                       |
|------------|--------------------|-----------------------------------|
| journal    | ForeignKey(Journal)| Associated journal                |
| tx_date    | DateField          | Transaction date                  |
| memo       | CharField(255)     | Optional transaction memo         |
| created_at | DateTimeField      | Creation timestamp                |
| posted     | BooleanField       | Transaction posting status        |

**Business Rules:** Each transaction must contain at least two entry lines, and total debits must equal total credits.

### EntryLine
| Field       | Type                   | Description                                |
|-------------|------------------------|--------------------------------------------|
| transaction | ForeignKey(Transaction)| Parent transaction                         |
| account     | ForeignKey(Account)    | Associated account                         |
| debit       | DecimalField(18,2)     | Debit amount (non-negative)                |
| credit      | DecimalField(18,2)     | Credit amount (non-negative)               |
| description | CharField(255)         | Optional line description                  |
| currency    | CharField(3)           | Currency code (default: EUR)               |
| base_amount | DecimalField(18,2)     | Signed amount calculation (debit - credit) |

**Constraints:** Each line must have either a debit or credit amount (but not both), and amounts must be non-negative.

### Balance
| Field        | Type                 | Description                                |
|--------------|----------------------|--------------------------------------------|
| account      | ForeignKey(Account)  | Associated account                         |
| period       | DateField            | Period start date (first day of month)    |
| debit_total  | DecimalField(18,2)   | Total debits for the period                |
| credit_total | DecimalField(18,2)   | Total credits for the period               |

**Constraints:** Unique combination of account and period.

## Application Architecture

### accounting
The core double-entry ledger implementation containing the fundamental business logic.

**Responsibilities:**
- Define core models: Account, Journal, Transaction, EntryLine, Balance
- Enforce accounting invariants: balanced entries, minimum line requirements, posted transaction immutability
- Provide business services: transaction posting pipeline, chart of accounts seeding, financial reporting
- Generate reports: Trial Balance, Profit & Loss Statement, Balance Sheet

This application serves as the system's foundation, with all other components either feeding data into or consuming data from the accounting ledger.

### aiassist
Machine learning and artificial intelligence functionality for automated bookkeeping assistance.

**Responsibilities:**
- Implement ML providers: local scikit-learn classifier, optional LLM integration
- Provide categorization services: automatic account suggestion for bank transactions
- Support natural language processing: convert text descriptions to structured transactions
- Manage model lifecycle: training commands, model validation, performance monitoring

The AI functionality remains decoupled from core accounting rules, enabling independent development and testing of machine learning features.

### api
REST API layer providing external access to the accounting system.

**Responsibilities:**
- Expose Django REST Framework endpoints for accounts, transactions, and AI predictions
- Handle request validation and serialization
- Maintain clean separation between external interfaces and internal business logic
- Support multiple client types: web frontends, mobile applications, CLI tools, external integrations

The API design ensures that user interfaces and external systems can interact with the ledger without direct coupling to Django internals.

### banking
Bank statement processing and reconciliation functionality.

**Responsibilities:**
- Model bank transactions and statement imports
- Support multiple import formats: CSV, OFX, MT940
- Provide reconciliation logic: match statement entries with ledger transactions
- Integration with AI services for automated transaction matching and categorization

This application bridges the gap between real-world banking data and the formal double-entry accounting system.

### core
Shared utilities and foundational components used across the application.

**Responsibilities:**
- Provide common model mixins: timestamping, soft deletion, audit trails
- Define reusable validators and utility functions
- Manage project-wide configurations and shared templates
- Handle cross-cutting concerns: logging, signals, external service integrations

The core application serves as a dependency-free foundation that other applications can safely import without creating circular dependencies.

## API Documentation

When the development server is running, interactive API documentation is available at:
- Swagger UI: `http://localhost:5005/api/schema/swagger-ui/`
