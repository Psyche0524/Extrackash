# Database Design

```text
USER
 |
 |---- WALLET
 |        |
 |        '---- TRANSACTION
 |                     |
 |                     '---- CATEGORY
 |
 |---- BUDGET (each for one CATEGORY)
 |
 '---- SAVINGS GOAL
```

| Table | Fields |
|---|---|
| User (Django built-in) | id, username, email, password (hashed), date_joined |
| Wallet | id, user, name, starting_balance, created_at |
| Category | id, user (empty = default), name, type (income/expense) |
| Transaction | id, user, wallet, category, amount, type, description, transaction_date, created_at |
| Budget | id, user, category, amount, start_date, end_date |
| SavingsGoal | id, user, name, target_amount, current_amount, deadline |

**Notes**
- A wallet's current balance is **calculated** (`starting_balance + income - expenses`), not stored, so edits and deletes never leave it wrong.
- Money uses `DecimalField` to avoid rounding errors.
- Deleting a wallet deletes its transactions. A category that has transactions cannot be deleted.
- Default categories are created by migration `expenses/0002_default_categories.py`.
