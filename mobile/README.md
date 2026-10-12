# Extrackash Mobile (React Native + Expo)

This folder holds the mobile app. The API helper is already written in `services/api.js`.

## First-time setup (Mobile Developer, once)

Run this from the **repo root** into a temporary folder, then copy the generated files into `mobile/`
(keep our `services/`, `components/`, `.env.example`):

```bash
npx create-expo-app@latest mobile-tmp
```

Copy everything from `mobile-tmp/` into `mobile/` (do not overwrite `services/`), delete `mobile-tmp/`, then:

```bash
cd mobile
npx expo install expo-secure-store
copy .env.example .env
npx expo start
```

Scan the QR code with the **Expo Go** app (same Wi-Fi as your computer).

## Connect to Django
1. In `backend/`, run: `python manage.py runserver 0.0.0.0:8000`
2. Put your computer's IP in `backend/.env` -> `ALLOWED_HOSTS`
3. Put `http://YOUR-IP:8000` in `mobile/.env` -> `EXPO_PUBLIC_API_URL`

## Using the API helper
```javascript
import { login, getDashboard, addExpense } from './services/api';

await login('juan', 'StrongPass#2026');
const summary = await getDashboard();
await addExpense({ wallet: 1, category: 1, amount: '150.00', description: 'Lunch', transaction_date: '2026-10-08' });
```
