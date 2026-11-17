from django.conf import settings
from django.db import models
from django.db.models import Sum
from django.utils import timezone

USER = settings.AUTH_USER_MODEL
MONEY = {'max_digits': 12, 'decimal_places': 2}

CATEGORIES = [
    ('dining', 'Food & dining'),
    ('groceries', 'Groceries'),
    ('transport', 'Transport'),
    ('bills', 'Bills & essentials'),
    ('subscriptions', 'Subscriptions'),
    ('shopping', 'Shopping'),
    ('salary', 'Salary'),
    ('other', 'Other'),
]


def _sum(qs):
    return qs.aggregate(t=Sum('amount'))['t'] or 0


class Account(models.Model):
    KINDS = [('bank', 'Bank'), ('wallet', 'E-wallet'), ('cash', 'Cash'), ('credit', 'Credit card')]

    user = models.ForeignKey(USER, on_delete=models.CASCADE, related_name='accounts')
    name = models.CharField(max_length=60)
    kind = models.CharField(max_length=10, choices=KINDS, default='bank')
    opening_balance = models.DecimalField('Current balance', default=0, help_text='For a credit card, enter what you owe as a negative number.', **MONEY)
    credit_limit = models.DecimalField(null=True, blank=True, help_text='Credit cards only.', **MONEY)
    due_day = models.PositiveSmallIntegerField(null=True, blank=True, help_text='Credit cards only: day of the month the bill is due.')

    class Meta:
        ordering = ['id']

    def __str__(self):
        return self.name

    @property
    def balance(self):
        # shortcut: 4 queries per account, fine for a handful of accounts; annotate if lists get long.
        tx = Transaction.objects
        return (self.opening_balance
                + _sum(tx.filter(account=self, kind='income'))
                - _sum(tx.filter(account=self, kind='expense'))
                - _sum(tx.filter(account=self, kind='transfer'))
                + _sum(tx.filter(to_account=self, kind='transfer')))


class Transaction(models.Model):
    EXPENSE = 'expense'
    INCOME = 'income'
    TRANSFER = 'transfer'
    KINDS = [(EXPENSE, 'Expense'), (INCOME, 'Income'), (TRANSFER, 'Transfer')]
    CATEGORIES = CATEGORIES

    user = models.ForeignKey(USER, on_delete=models.CASCADE, related_name='transactions')
    kind = models.CharField(max_length=10, choices=KINDS, default=EXPENSE)
    description = models.CharField('Merchant or description', max_length=100)
    amount = models.DecimalField(**MONEY)
    category = models.CharField(max_length=20, choices=CATEGORIES, default='other')
    date = models.DateField(default=timezone.localdate)
    note = models.CharField(max_length=200, blank=True)
    account = models.ForeignKey(Account, null=True, on_delete=models.SET_NULL, related_name='+')
    to_account = models.ForeignKey(Account, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    shared = models.BooleanField('Shared with my household', default=False)

    class Meta:
        ordering = ['-date', '-id']

    def __str__(self):
        return f'{self.description} ({self.amount})'


class Budget(models.Model):
    user = models.ForeignKey(USER, on_delete=models.CASCADE, related_name='budgets')
    category = models.CharField(max_length=20, choices=CATEGORIES)
    limit = models.DecimalField('Monthly limit', **MONEY)

    class Meta:
        ordering = ['category']
        constraints = [models.UniqueConstraint(fields=['user', 'category'], name='one_budget_per_category')]


class Goal(models.Model):
    user = models.ForeignKey(USER, on_delete=models.CASCADE, related_name='goals')
    name = models.CharField(max_length=60)
    note = models.CharField(max_length=100, blank=True)
    target = models.DecimalField(**MONEY)
    target_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['id']

    @property
    def saved(self):
        return _sum(self.contributions.all())


class Contribution(models.Model):
    goal = models.ForeignKey(Goal, on_delete=models.CASCADE, related_name='contributions')
    description = models.CharField(max_length=60, default='Contribution')
    amount = models.DecimalField(**MONEY)
    date = models.DateField(default=timezone.localdate)

    class Meta:
        ordering = ['-date', '-id']


class Debt(models.Model):
    """Installments and loans: both are 'pay X a month until Y is paid'."""
    KINDS = [('installment', 'Installment'), ('loan', 'Loan')]

    user = models.ForeignKey(USER, on_delete=models.CASCADE, related_name='debts')
    kind = models.CharField(max_length=12, choices=KINDS, default='installment')
    name = models.CharField(max_length=60)
    total = models.DecimalField('Total amount', **MONEY)
    monthly = models.DecimalField('Monthly payment', **MONEY)
    paid = models.DecimalField('Already paid', default=0, **MONEY)
    account = models.ForeignKey(Account, null=True, blank=True, on_delete=models.SET_NULL, help_text='Where payments come from.')
    due_day = models.PositiveSmallIntegerField(null=True, blank=True)
    note = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['id']

    @property
    def remaining(self):
        return max(self.total - self.paid, 0)

    @property
    def payments_left(self):
        return -(-self.remaining // self.monthly) if self.monthly else 0


class Investment(models.Model):
    user = models.ForeignKey(USER, on_delete=models.CASCADE, related_name='investments')
    name = models.CharField(max_length=60)
    label = models.CharField('Type', max_length=40, blank=True, help_text='e.g. Long-term, Fixed income')
    invested = models.DecimalField('Amount put in', **MONEY)
    value = models.DecimalField('Current value', **MONEY)
    updated = models.DateField(auto_now=True)

    class Meta:
        ordering = ['-value']


class Household(models.Model):
    name = models.CharField(max_length=60)
    members = models.ManyToManyField(USER, related_name='households')
    shared_budget = models.DecimalField('Monthly shared budget', default=0, **MONEY)
