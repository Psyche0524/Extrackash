# Installation Guide

Follow the **Installation** section of the root `README.md`. Quick checklist:

- [ ] Python 3.12+, Git, Node.js LTS, PostgreSQL, VS Code installed
- [ ] Repository cloned and opened in VS Code
- [ ] Database `extrackash_db` created
- [ ] `venv` created and activated, `pip install -r requirements.txt` done
- [ ] `backend/.env` created from `.env.example`
- [ ] `python manage.py migrate` ran without errors
- [ ] `python manage.py test` shows `OK`
- [ ] `python manage.py runserver` works and `/admin` opens
- [ ] Mobile app started with `npx expo start` (see `mobile/README.md`)
