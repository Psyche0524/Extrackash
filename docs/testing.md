# Testing

## Automatic tests
```bash
cd backend
python manage.py test
```
Covers registration, login, logout, weak/duplicate passwords, data isolation between users, validation (negative amounts, wrong wallet/category), the dashboard, and wallet balances.

## Manual test cases (QA fills this in)
| ID | Feature | Steps | Expected | Actual | Pass/Fail | Date |
|---|---|---|---|---|---|---|
| TC-001 | Register | POST `/auth/register/` with valid data | 201 | | | |
| TC-002 | Login | POST `/auth/login/` with wrong password | 401 | | | |
| TC-003 | Add expense | POST `/expenses/` with negative amount | 400 | | | |
| TC-004 | Privacy | User B opens `/expenses/` | Sees none of user A's data | | | |

## Bug list
| ID | Description | Found by | Status |
|---|---|---|---|
