# Extrackash

Expense tracker web app built with **Django** (Python), **HTML**, **CSS** and **JavaScript**.
Design: [Figma](https://www.figma.com/design/E1OFOlFfNvk1xL3djQGqXV/Untitled?node-id=0-1)

## Project layout

```text
config/                     Django settings and URLs
expenses/                   The expenses app
  models.py                 Database tables
  views.py                  Page logic
  forms.py                  Forms + validation
  templates/expenses/       HTML pages (form.html is shared by every add/edit screen)
  templatetags/money.py     {{ value|peso }} money formatting
  static/expenses/          CSS, JavaScript, images (logo, mascot)
  management/commands/      seed_demo (sample data)
  tests.py                  Tests
```

Brand: **Poppins** font and the green palette from the Brand Identity Board
(see the `:root` colors in `expenses/static/expenses/style.css`).
Figma exports live in a local `Figma Design/` folder, which git ignores.

## Screens

| Figma screen | URL |
|---|---|
| 01 Welcome | `/welcome/` |
| 02 Set up (sign up, then first account) | `/signup/`, `/setup/`, `/ready/` |
| Log in | `/login/` |
| 03 Home | `/` |
| 04 Activity | `/activity/` |
| 05 Add transaction / 25 Add income | `/add/` |
| 07 Transaction detail | `/activity/<id>/` |
| 08 Budgets / 09 Budget detail | `/plan/`, `/plan/budgets/<id>/` |
| 10 Accounts / 11 Transfer | `/explore/accounts/`, `/transfer/` |
| 12 Extrackash Chat | `/explore/chat/` |
| 13 Goals / 14 Goal detail | `/plan/goals/`, `/plan/goals/<id>/` |
| 15 Cards / 16 Installments | `/explore/cards/`, `/explore/installments/` |
| 17 Cashflow / 18 Debt plan | `/plan/cashflow/`, `/explore/loans/` |
| 19 Investments | `/explore/investments/` |
| 20, 27, 28 Reports (month/week/year) | `/explore/reports/` |
| 21 Shared finances | `/explore/shared/` |
| 22 Explore | `/explore/` |
| 23 Settings | `/settings/` |

Not built (needs a native app or an outside service): app lock / biometrics, cloud sync and offline mode,
appearance themes, PDF export, AI chat (Chat answers from your own numbers with simple rules for now).

## First-time setup (Windows)

```bash
git clone https://github.com/Psyche0524/Extrackash.git
cd Extrackash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000 for the app and http://127.0.0.1:8000/admin for the admin panel.

Want sample data to click around? Run `python manage.py seed_demo` and log in with the demo account it prints
(local development only; running it again resets the demo).

macOS/Linux: use `source .venv/bin/activate` instead of `.venv\Scripts\activate`.

## View it as a mobile app

**On your PC:** open the app in Chrome/Edge, press `F12`, then `Ctrl+Shift+M`, and pick a phone (e.g. iPhone 14 Pro, 393 px like the Figma frames).

**On your real phone** (phone and PC on the same Wi-Fi):

```bash
python manage.py runserver 0.0.0.0:8000
```

1. Find your PC's IP: run `ipconfig` and look for **IPv4 Address** (e.g. `192.168.1.5`).
2. On your phone, open `http://192.168.1.5:8000`.
3. If it doesn't load, allow Python through Windows Firewall (Private networks) when Windows asks.

## Every day

```bash
git switch develop
git pull
.venv\Scripts\activate
python manage.py migrate
```

## Team workflow (3 members)

1. Never push straight to `main` or `develop`.
2. Make a branch from `develop` for each task: `feature/<name>`, `fix/<name>`.
3. Run `python manage.py test` before you push.
4. Open a Pull Request into `develop`. One teammate reviews, then merge.
5. When `develop` is stable, merge `develop` into `main`.
6. Changed `models.py`? Run `python manage.py makemigrations` and commit the migration file.
7. Never commit `.venv/`, `db.sqlite3` or `.env` (already in `.gitignore`).

## Team

| Name | Role |
|---|---|
| Member 1 | Backend (Django models, views) |
| Member 2 | Frontend (HTML, CSS, JavaScript) |
| Member 3 | UI/UX (Figma) + testing + docs |
