from django.test import TestCase

from .models import Transaction


def add(client, **data):
    base = {'kind': 'expense', 'amount': '100', 'description': 'X', 'category': 'other', 'date': '2026-11-17', 'note': ''}
    return client.post('/add/', {**base, **data})


class TransactionTests(TestCase):
    def test_home_totals(self):
        add(self.client, kind='income', amount='62000', description='Monthly salary', category='salary')
        add(self.client, amount='650.50', description='Wildflour', category='dining')
        response = self.client.get('/')
        self.assertEqual(response.context['available'], 62000 - 650.5)
        self.assertContains(response, 'Wildflour')
        self.assertContains(response, '+₱62,000.00')

    def test_activity_search(self):
        add(self.client, description='Grab')
        add(self.client, description='Netflix')
        response = self.client.get('/activity/?q=grab')
        self.assertContains(response, 'Grab')
        self.assertNotContains(response, 'Netflix')

    def test_rejects_zero_amount(self):
        response = add(self.client, amount='0')
        self.assertEqual(Transaction.objects.count(), 0)
        self.assertContains(response, 'Amount must be more than 0.')
