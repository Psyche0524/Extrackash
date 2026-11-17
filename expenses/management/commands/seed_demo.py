from datetime import date, timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from expenses.models import Account, Budget, Contribution, Debt, Goal, Investment, Transaction

EMAIL = 'demo@example.test'
PASSWORD = 'local-dev-squirrel-77'  # local development only


class Command(BaseCommand):
    help = f'Create (or reset) a demo account with sample data. Log in as {EMAIL} / {PASSWORD}.'

    def handle(self, *args, **options):
        User.objects.filter(username=EMAIL).delete()
        u = User.objects.create_user(EMAIL, EMAIL, PASSWORD, first_name='Alex')
        bpi = Account.objects.create(user=u, name='BPI Everyday', kind='bank', opening_balance=40000)
        gcash = Account.objects.create(user=u, name='GCash', kind='wallet', opening_balance=22000)
        Account.objects.create(user=u, name='Cash', kind='cash', opening_balance=8000)
        visa = Account.objects.create(user=u, name='BPI Visa', kind='credit', credit_limit=50000, due_day=25)

        today = date.today()
        for kind, amount, desc, cat, acct, days_ago, note in [
            ('income', 62000, 'Monthly salary', 'salary', bpi, (today - today.replace(day=1)).days, ''),
            ('expense', 650, 'Wildflour', 'dining', bpi, 0, 'Lunch with Maya'),
            ('expense', 180, 'Grab', 'transport', gcash, 0, ''),
            ('expense', 2100, 'The Marketplace', 'groceries', bpi, 1, ''),
            ('expense', 549, 'Netflix', 'subscriptions', visa, 1, ''),
            ('expense', 4200, 'Uniqlo', 'shopping', visa, 3, ''),
        ]:
            Transaction.objects.create(user=u, kind=kind, amount=amount, description=desc, category=cat,
                                       account=acct, date=today - timedelta(days=days_ago), note=note)

        for cat, limit in [('dining', 8000), ('shopping', 5000), ('transport', 3000)]:
            Budget.objects.create(user=u, category=cat, limit=limit)
        fund = Goal.objects.create(user=u, name='Emergency fund', note='Your future safety net', target=60000)
        Contribution.objects.create(goal=fund, amount=24000, description='Monthly contribution')
        Goal.objects.create(user=u, name='Japan, slowly', note='A little adventure', target=40000, target_date=date(today.year + 1, 4, 1))
        Debt.objects.create(user=u, kind='installment', name='MacBook Air', total=30000, monthly=2500, paid=10000, account=visa, due_day=25)
        Debt.objects.create(user=u, kind='loan', name='Personal loan', total=36000, monthly=3000, paid=18000, account=bpi, note='0% family loan')
        Investment.objects.create(user=u, name='Global index fund', label='Long-term', invested=90000, value=96000)
        Investment.objects.create(user=u, name='Government bonds', label='Fixed income', invested=30000, value=30500)
        self.stdout.write(self.style.SUCCESS(f'Demo ready. Log in as {EMAIL} / {PASSWORD}'))
