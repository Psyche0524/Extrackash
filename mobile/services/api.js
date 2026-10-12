import * as SecureStore from 'expo-secure-store';

const API_URL = process.env.EXPO_PUBLIC_API_URL;

async function getToken(name) {
  return SecureStore.getItemAsync(name);
}

async function saveTokens({ access, refresh }) {
  await SecureStore.setItemAsync('access', access);
  if (refresh) await SecureStore.setItemAsync('refresh', refresh);
}

export async function clearTokens() {
  await SecureStore.deleteItemAsync('access');
  await SecureStore.deleteItemAsync('refresh');
}

async function refreshAccessToken() {
  const refresh = await getToken('refresh');
  if (!refresh) return false;
  const res = await fetch(`${API_URL}/api/auth/refresh/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh }),
  });
  if (!res.ok) return false;
  await saveTokens(await res.json());
  return true;
}

// Generic request helper: adds the token and retries once if it expired.
export async function request(path, { method = 'GET', body, auth = true } = {}, retry = true) {
  const headers = { 'Content-Type': 'application/json' };
  if (auth) headers.Authorization = `Bearer ${await getToken('access')}`;

  const res = await fetch(`${API_URL}/api${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (res.status === 401 && auth && retry && (await refreshAccessToken())) {
    return request(path, { method, body, auth }, false);
  }
  if (res.status === 204 || res.status === 205) return null;

  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const message = data?.detail || (data && JSON.stringify(data)) || 'Request failed';
    throw new Error(message);
  }
  return data;
}

// ---- Auth ----
export const register = (username, email, password) =>
  request('/auth/register/', { method: 'POST', body: { username, email, password }, auth: false });

export async function login(username, password) {
  const tokens = await request('/auth/login/', { method: 'POST', body: { username, password }, auth: false });
  await saveTokens(tokens);
  return tokens;
}

export async function logout() {
  const refresh = await getToken('refresh');
  try {
    await request('/auth/logout/', { method: 'POST', body: { refresh } });
  } finally {
    await clearTokens();
  }
}

// ---- Data ----
export const getDashboard = () => request('/dashboard/');
export const getWallets = () => request('/wallets/');
export const getCategories = () => request('/categories/');
export const getTransactions = (type) => request(`/transactions/${type ? `?type=${type}` : ''}`);
export const getExpenses = () => request('/expenses/');
export const addExpense = (expense) => request('/expenses/', { method: 'POST', body: expense });
export const addIncome = (income) => request('/income/', { method: 'POST', body: income });
export const getBudgets = () => request('/budgets/');
export const getSavings = () => request('/savings/');
