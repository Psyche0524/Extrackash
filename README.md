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
  templates/expenses/       HTML pages (Home, Activity, Add transaction)
  static/expenses/          CSS, JavaScript, images (logo)
  tests.py                  Tests
```

Brand: **Poppins** font and the green palette from the Brand Identity Board
(see the `:root` colors in `expenses/static/expenses/style.css`).

## Screens built so far

| Figma screen | URL |
|---|---|
| 03 Home | `/` |
| 04 Activity | `/activity/` |
| 05 Add transaction / 25 Add income | `/add/` |

Not built yet: Welcome, Set up, Budgets, Accounts, Transfer, Goals, Cards, Reports, Settings and the rest.
Pick one, make a `feature/<screen>` branch, and open a PR.

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

macOS/Linux: use `source .venv/bin/activate` instead of `.venv\Scripts\activate`.

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
