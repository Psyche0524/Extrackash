# System Architecture

```text
             EXTRACKASH MOBILE APP
          (React Native + Expo)
                     |
                     | HTTP / REST API (JSON)
                     v
          +----------------------+
          |   DJANGO BACKEND     |
          | Django REST Framework|
          +----------+-----------+
                     | Django ORM
                     v
               POSTGRESQL DATABASE
```

- **Mobile app:** screens and user actions. Calls the API using `mobile/services/api.js`.
- **Django REST API:** checks login (JWT), validates data, returns JSON.
- **Database:** stores users, wallets, categories, transactions, budgets, savings goals.

## Django apps
| App | Responsibility |
|---|---|
| `accounts` | Register, login, logout, profile |
| `wallets` | Wallets and their balances |
| `expenses` | Categories, transactions (income and expenses), dashboard |
| `budgets` | Budgets per category and period |
| `savings` | Savings goals |
| `notifications` | Reminders and alerts (placeholder for now) |
