# Extrackash

A mobile expense tracker that helps you record income and expenses, manage budgets, and reach your savings goals. Built as a BSIT mini-capstone project.

## Features
- Register, login, logout (JWT)
- Multiple wallets (Cash, Bank, E-wallet)
- Add income and expenses with categories
- Transaction history
- Budgets and savings goals
- Dashboard summary
- Notifications (planned)

## Technologies
| Part | Tech |
|---|---|
| Backend | Python 3.12+, Django, Django REST Framework |
| Mobile | React Native, Expo |
| Database | PostgreSQL |
| Auth | JWT (SimpleJWT) |
| Tools | VS Code, Git, GitHub, Thunder Client |

## System Architecture
```text
Mobile App (React Native)  -->  Django REST API  -->  PostgreSQL
```

## Installation
### 1. Database
Install PostgreSQL, open **SQL Shell (psql)**, then run:
```sql
CREATE DATABASE extrackash_db;
```

### 2. Backend
```bash
git clone https://github.com/YOUR-USERNAME/Extrackash.git
cd Extrackash/backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```
Open `.env` and fill in your own `SECRET_KEY` and `DB_PASSWORD`, then:
```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```
Open http://127.0.0.1:8000/admin to check that it works.

### 3. Mobile
See [`mobile/README.md`](mobile/README.md).

## Development Setup
- Always activate `venv` before running Django commands.
- Run `python manage.py migrate` after every `git pull`.
- Run `python manage.py test` before opening a Pull Request.

## Git Workflow
- Never commit directly to `main` or `develop`.
- Create a branch: `feature/<name>`, `bugfix/<name>`, or `docs/<name>`.
- Open a Pull Request into `develop`; a teammate must review it.
- Use clear commit messages (e.g. `Add wallet API`).

## API Information
Base URL: `http://YOUR-IP:8000/api/`

| Endpoint | Purpose |
|---|---|
| `/auth/register/`, `/auth/login/`, `/auth/refresh/`, `/auth/logout/`, `/auth/me/` | Authentication |
| `/wallets/` | Wallets |
| `/categories/` | Categories (defaults + your own) |
| `/transactions/`, `/expenses/`, `/income/` | Transactions |
| `/budgets/` | Budgets |
| `/savings/` | Savings goals |
| `/dashboard/` | Totals for the home screen |

Full details: [`docs/api-documentation.md`](docs/api-documentation.md).

## Team Members
| Name | Role |
|---|---|
| Name 1 | Project Manager |
| Name 2 | Backend Developer |
| Name 3 | Mobile/Frontend Developer |
| Name 4 | Database Developer |
| Name 5 | UI/UX Designer |
| Name 6 | QA/Tester and Documentation |

## Future Improvements
- Notifications and reminders
- Charts and reports
- Export to PDF/Excel
- Recurring transactions
- Receipt photo upload
- Multi-currency support
- Dark mode
