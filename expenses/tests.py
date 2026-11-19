from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Account, Budget, Debt, Goal, Household, Investment, Transaction
from .templatetags.money import peso


def make_user(email='alex@example.com', name='Alex'):
    return User.objects.create_user(email, email, 'squirrel-cash-26', first_name=name)


class AuthTests(TestCase):
    def test_pages_need_login(self):
        for url in ['/', '/activity/', '/add/', '/plan/', '/explore/', '/settings/']:
            self.assertRedirects(self.client.get(url), f'/welcome/?next={url}')

    def test_signup_then_setup_first_account(self):
        response = self.client.post('/signup/', {
            'first_name': 'Alex', 'email': 'Alex@Example.com',
            'password1': 'squirrel-cash-26', 'password2': 'squirrel-cash-26',
        })
        self.assertRedirects(response, '/setup/')
        response = self.client.post('/setup/', {'name': 'BPI Everyday', 'kind': 'bank', 'opening_balance': '54250'})
        self.assertRedirects(response, '/ready/')
        home = self.client.get('/')
        self.assertContains(home, 'Hello, Alex!')
        self.assertContains(home, '₱54,250.00')
        self.assertEqual(User.objects.get().username, 'alex@example.com')

    def test_duplicate_email_rejected(self):
        make_user()
        response = self.client.post('/signup/', {
            'first_name': 'A', 'email': 'ALEX@example.com',
            'password1': 'squirrel-cash-26', 'password2': 'squirrel-cash-26',
        })
        self.assertContains(response, 'already exists')

    def test_login_with_email_any_case_and_logout(self):
        make_user()
        response = self.client.post('/login/', {'username': 'ALEX@example.com', 'password': 'squirrel-cash-26'})
        self.assertRedirects(response, '/')
        self.assertRedirects(self.client.post('/logout/'), '/welcome/')

    def test_wrong_password_shows_error(self):
        make_user()
        response = self.client.post('/login/', {'username': 'alex@example.com', 'password': 'nope'})
        self.assertContains(response, 'Email or password is incorrect.')

    def test_delete_account_needs_typed_confirmation(self):
        user = make_user()
        self.client.force_login(user)
        self.client.post('/settings/delete/', {'confirm': 'yes'})
        self.assertTrue(User.objects.exists())
        self.assertRedirects(self.client.post('/settings/delete/', {'confirm': 'DELETE'}), '/welcome/')
        self.assertFalse(User.objects.exists())


class MoneyTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)
        self.bank = Account.objects.create(user=self.user, name='BPI', kind='bank', opening_balance=1000)
        self.gcash = Account.objects.create(user=self.user, name='GCash', kind='wallet', opening_balance=0)

    def add(self, **data):
        base = {'kind': 'expense', 'amount': '100', 'description': 'X', 'category': 'other',
                'account': self.bank.pk, 'date': '2026-11-17', 'note': ''}
        return self.client.post('/add/', {**base, **data})

    def test_peso_filter(self):
        self.assertEqual(peso(Decimal('1234.5')), '₱1,234.50')
        self.assertEqual(peso(-20), '−₱20.00')

    def test_income_expense_and_transfer_balances(self):
        self.add(kind='income', amount='500', category='salary')
        self.add(amount='200')
        self.client.post('/transfer/', {'account': self.bank.pk, 'to_account': self.gcash.pk, 'amount': '300', 'date': '2026-11-17'})
        self.bank.refresh_from_db()
        self.assertEqual(self.bank.balance, 1000)   # 1000 + 500 - 200 - 300
        self.assertEqual(self.gcash.balance, 300)
        self.assertEqual(self.client.get('/').context['available'], 1300)  # transfers don't change the total

    def test_transfer_needs_two_different_accounts(self):
        response = self.client.post('/transfer/', {'account': self.bank.pk, 'to_account': self.bank.pk, 'amount': '1', 'date': '2026-11-17'})
        self.assertContains(response, 'Pick two different accounts.')

    def test_rejects_zero_amount(self):
        response = self.add(amount='0')
        self.assertEqual(Transaction.objects.count(), 0)
        self.assertContains(response, 'Amount must be more than 0.')

    def test_activity_search(self):
        self.add(description='Grab')
        self.add(description='Netflix')
        response = self.client.get('/activity/?q=grab')
        self.assertContains(response, 'Grab')
        self.assertNotContains(response, 'Netflix')

    def test_edit_and_delete_transaction(self):
        self.add(description='Lunch')
        tx = Transaction.objects.get()
        self.client.post(f'/activity/{tx.pk}/edit/', {'kind': 'expense', 'amount': '150', 'description': 'Lunch',
                                                     'category': 'dining', 'account': self.bank.pk, 'date': '2026-11-17'})
        tx.refresh_from_db()
        self.assertEqual(tx.amount, 150)
        self.client.post(f'/activity/{tx.pk}/delete/')
        self.assertFalse(Transaction.objects.exists())

    def test_budget_tracks_this_months_spending(self):
        from django.utils import timezone
        budget = Budget.objects.create(user=self.user, category='dining', limit=1000)
        self.add(amount='250', category='dining', date=timezone.localdate().isoformat())
        response = self.client.get(f'/plan/budgets/{budget.pk}/')
        self.assertEqual(response.context['spent'], 250)
        self.assertEqual(response.context['left'], 750)
        self.assertContains(self.client.post('/plan/budgets/new/', {'category': 'dining', 'limit': '5'}), 'already have a budget')

    def test_goal_contributions_add_up(self):
        goal = Goal.objects.create(user=self.user, name='Emergency fund', target=1000)
        self.client.post(f'/plan/goals/{goal.pk}/add/', {'amount': '400', 'description': 'Monthly', 'date': '2026-11-01'})
        self.assertEqual(self.client.get(f'/plan/goals/{goal.pk}/').context['pct'], 40)

    def test_debt_payment_moves_plan_and_adds_expense(self):
        debt = Debt.objects.create(user=self.user, kind='installment', name='MacBook', total=1000, monthly=400, account=self.bank)
        for _ in range(4):  # last payment is capped at what's left
            self.client.post(f'/explore/debts/{debt.pk}/pay/')
        debt.refresh_from_db()
        self.assertEqual(debt.paid, 1000)
        self.assertEqual(sum(t.amount for t in Transaction.objects.all()), 1000)

    def test_credit_card_owed_and_payment(self):
        card = Account.objects.create(user=self.user, name='Visa', kind='credit', credit_limit=5000)
        self.add(amount='600', account=card.pk)
        self.assertEqual(self.client.get('/explore/cards/').context['cards'][0]['owed'], 600)
        self.client.post('/transfer/', {'account': self.bank.pk, 'to_account': card.pk, 'amount': '600', 'date': '2026-11-17'})
        self.assertEqual(self.client.get('/explore/cards/').context['cards'][0]['owed'], 0)

    def test_shared_household_equal_split(self):
        maya = make_user('maya@example.com', 'Maya')
        maya_bank = Account.objects.create(user=maya, name='BDO')
        self.client.post('/explore/shared/new/', {'name': 'Santos home', 'shared_budget': '20000'})
        self.client.post('/explore/shared/invite/', {'email': 'MAYA@example.com'})
        self.add(amount='700', shared='on')
        Transaction.objects.create(user=maya, account=maya_bank, amount=300, description='Rent', shared=True)
        people = {p['user'].first_name: p['balance'] for p in self.client.get('/explore/shared/').context['people']}
        self.assertEqual(people, {'Alex': 200, 'Maya': -200})

    def test_users_cannot_see_or_touch_each_others_data(self):
        self.add(description='Alex lunch')
        tx = Transaction.objects.get()
        other = make_user('maya@example.com', 'Maya')
        self.client.force_login(other)
        self.assertNotContains(self.client.get('/activity/'), 'Alex lunch')
        self.assertEqual(self.client.get(f'/activity/{tx.pk}/').status_code, 404)
        self.assertEqual(self.client.post(f'/activity/{tx.pk}/delete/').status_code, 404)
        self.assertEqual(self.client.get(f'/explore/accounts/{self.bank.pk}/edit/').status_code, 404)
        # can't log a transaction into someone else's account
        Account.objects.create(user=other, name='Mine')
        response = self.client.post('/add/', {'kind': 'expense', 'amount': '1', 'description': 'x', 'category': 'other',
                                              'account': self.bank.pk, 'date': '2026-11-17'})
        self.assertContains(response, 'Select a valid choice')

    def test_csv_export_only_has_my_rows(self):
        self.add(description='Mine')
        Transaction.objects.create(user=make_user('maya@example.com'), amount=5, description='Not mine')
        body = self.client.get('/explore/reports/export.csv').content.decode()
        self.assertIn('Mine', body)
        self.assertNotIn('Not mine', body)

    def test_chat_save_question(self):
        Budget.objects.create(user=self.user, category='dining', limit=10000)
        answer = self.client.get('/explore/chat/?q=Can I save 5,000 this month?').context['answer']
        self.assertIn('₱5,000.00', answer['body'])

    def test_every_page_loads(self):
        goal = Goal.objects.create(user=self.user, name='G', target=100)
        budget = Budget.objects.create(user=self.user, category='dining', limit=100)
        debt = Debt.objects.create(user=self.user, name='Loan', kind='loan', total=100, monthly=10)
        item = Investment.objects.create(user=self.user, name='Fund', invested=100, value=120)
        self.add(description='Lunch')
        tx = Transaction.objects.get()
        names = ['home', 'activity', 'add', 'transfer', 'plan', 'budget_new', 'goals', 'goal_new', 'cashflow',
                 'explore', 'accounts', 'account_new', 'cards', 'installments', 'loans', 'debt_new', 'investments',
                 'investment_new', 'reports', 'shared', 'household_new', 'chat', 'settings', 'profile_edit', 'delete_account']
        urls = [reverse(n) for n in names] + [
            reverse('transaction', args=[tx.pk]), reverse('transaction_edit', args=[tx.pk]),
            reverse('budget', args=[budget.pk]), reverse('goal', args=[goal.pk]), reverse('goal_add', args=[goal.pk]),
            reverse('debt_edit', args=[debt.pk]), reverse('investment_edit', args=[item.pk]),
            '/explore/reports/?period=week', '/explore/reports/?period=year', '/explore/chat/?q=how am I doing',
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
        Household.objects.create(name='H').members.add(self.user)
        self.assertEqual(self.client.get('/explore/shared/').status_code, 200)
