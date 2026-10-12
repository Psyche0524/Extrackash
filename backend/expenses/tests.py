from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from wallets.models import Wallet

from .models import Category


class ExpenseApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='juan', password='StrongPass#2026')
        self.wallet = Wallet.objects.create(user=self.user, name='Cash', starting_balance=1000)
        self.food = Category.objects.get(name='Food', user=None)
        self.salary = Category.objects.get(name='Salary', user=None)
        self.client.force_authenticate(user=self.user)

    def _expense(self, **extra):
        data = {'wallet': self.wallet.id, 'category': self.food.id,
                'amount': '150.00', 'transaction_date': '2026-10-08'}
        data.update(extra)
        return data

    def test_create_expense(self):
        response = self.client.post('/api/expenses/', self._expense())
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['type'], 'expense')

    def test_negative_amount_rejected(self):
        response = self.client.post('/api/expenses/', self._expense(amount='-5'))
        self.assertEqual(response.status_code, 400)

    def test_requires_login(self):
        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.get('/api/expenses/').status_code, 401)

    def test_wrong_category_type_rejected(self):
        response = self.client.post('/api/expenses/', self._expense(category=self.salary.id))
        self.assertEqual(response.status_code, 400)

    def test_cannot_use_someone_elses_wallet(self):
        other = User.objects.create_user(username='maria', password='StrongPass#2026')
        other_wallet = Wallet.objects.create(user=other, name='Bank')
        response = self.client.post('/api/expenses/', self._expense(wallet=other_wallet.id))
        self.assertEqual(response.status_code, 400)

    def test_users_only_see_their_own_data(self):
        self.client.post('/api/expenses/', self._expense())
        other = User.objects.create_user(username='maria', password='StrongPass#2026')
        self.client.force_authenticate(user=other)
        self.assertEqual(len(self.client.get('/api/expenses/').data), 0)

    def test_dashboard_and_wallet_balance(self):
        self.client.post('/api/expenses/', self._expense(amount='200.00'))
        self.client.post('/api/income/', {'wallet': self.wallet.id, 'category': self.salary.id,
                                          'amount': '500.00', 'transaction_date': '2026-10-08'})
        dash = self.client.get('/api/dashboard/').data
        self.assertEqual(float(dash['balance']), 300.0)
        wallet = self.client.get('/api/wallets/').data[0]
        self.assertEqual(float(wallet['current_balance']), 1300.0)

    def test_default_categories_are_read_only(self):
        response = self.client.delete(f'/api/categories/{self.food.id}/')
        self.assertEqual(response.status_code, 403)
