# API Documentation

Base URL: `http://127.0.0.1:8000/api/`
All endpoints except register and login need the header `Authorization: Bearer <access_token>`.

## Authentication
| Method | Endpoint | Body | Result |
|---|---|---|---|
| POST | `/auth/register/` | `username`, `email`, `password` | `201` user |
| POST | `/auth/login/` | `username`, `password` | `200` `{access, refresh}` |
| POST | `/auth/refresh/` | `refresh` | `200` `{access}` |
| POST | `/auth/logout/` | `refresh` | `205` (token blacklisted) |
| GET / PATCH | `/auth/me/` | `username`, `email` | `200` user |

## Resources
Each supports `GET` (list), `POST` (create), and on `/{id}/`: `GET`, `PUT`, `PATCH`, `DELETE`.

| Endpoint | Fields |
|---|---|
| `/wallets/` | `name`, `starting_balance` (read-only: `current_balance`) |
| `/categories/` | `name`, `type` (`income` or `expense`). Default categories are read-only |
| `/transactions/` | `wallet`, `category`, `amount`, `type`, `description`, `transaction_date`. Filter: `?type=expense` |
| `/expenses/` | same as transactions, `type` is set to `expense` automatically |
| `/income/` | same as transactions, `type` is set to `income` automatically |
| `/budgets/` | `category` (expense), `amount`, `start_date`, `end_date` |
| `/savings/` | `name`, `target_amount`, `current_amount`, `deadline` |
| `/dashboard/` (GET only) | returns `total_income`, `total_expense`, `balance` |

## Example
`POST /api/expenses/`
```json
{ "wallet": 1, "category": 1, "amount": "150.00", "description": "Lunch", "transaction_date": "2026-10-08" }
```
Response `201`:
```json
{ "id": 1, "wallet": 1, "category": 1, "amount": "150.00", "type": "expense",
  "description": "Lunch", "transaction_date": "2026-10-08", "created_at": "2026-10-08T09:30:00Z" }
```

## Status codes
`200` OK, `201` created, `205` logged out, `400` invalid input, `401` not logged in or token expired, `403` not allowed, `404` not found.
