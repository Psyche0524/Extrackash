# Requirements

## Functional
| ID | Requirement |
|---|---|
| FR-01 | Users can register, log in, and log out |
| FR-02 | Users can create and manage multiple wallets |
| FR-03 | Users can record income and expenses with a category |
| FR-04 | Users can view and filter transaction history |
| FR-05 | Users can set budgets per expense category and date range |
| FR-06 | Users can create savings goals and track progress |
| FR-07 | The dashboard shows total income, total expense, and balance |
| FR-08 | Users receive notifications (planned) |

## Non-functional
- Passwords are hashed by Django, never stored as plain text
- Each user can only see their own data
- All input is validated by the API
- JWT access tokens expire after 30 minutes
- The mobile app works on Android through Expo
