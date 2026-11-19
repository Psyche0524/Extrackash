from datetime import date, timedelta

from django.conf import settings
from django.db import models
from django.db.models import Sum
from django.utils import timezone

USER = settings.AUTH_USER_MODEL
MONEY = {'max_digits': 12, 'decimal_places': 2}


def _now_time():
    return timezone.localtime().time().replace(second=0, microsecond=0)

EXPENSE_CATEGORIES = [
    ('dining', 'Food'),
    ('groceries', 'Groceries'),
    ('transport', 'Transport'),
    ('phone', 'Phone'),
    ('bills', 'Bills'),
    ('subscriptions', 'Subscriptions'),
    ('shopping', 'Shopping'),
    ('fun', 'Fun'),
    ('health', 'Health'),
    ('fees', 'Fees'),
    ('other', 'Other'),
]
INCOME_CATEGORIES = [
    ('salary', 'Salary'), ('bonus', 'Bonus'), ('freelance', 'Freelance'), ('commission', 'Commission'),
    ('business', 'Business'), ('side_hustle', 'Side hustle'), ('allowance', 'Allowance'), ('gift', 'Gift'),
    ('refund', 'Refund'), ('cashback', 'Cashback'), ('interest', 'Interest'), ('dividend', 'Dividend'),
    ('rental', 'Rental'), ('other', 'Other'),
]
CATEGORIES = EXPENSE_CATEGORIES + INCOME_CATEGORIES[:-1]
LABELS = dict(CATEGORIES)


def category_label(value):
    """Built-in categories have a nice label; custom ones are shown as typed."""
    return LABELS.get(value, value)


def _sum(qs):
    return qs.aggregate(t=Sum('amount'))['t'] or 0


class Account(models.Model):
    KINDS = [('bank', 'Bank'), ('wallet', 'E-wallet'), ('cash', 'Cash'), ('credit', 'Credit card')]
    # (value, label, card colour). Colours approximate each brand; logos are initials, not brand artwork.
    PROVIDERS = [
        ('gcash', 'GCash', '#1d4ed8'),
        ('maya', 'Maya', '#047857'),
        ('maribank', 'Maribank', '#ea580c'),
        ('gotyme', 'GoTyme', '#0e7490'),
        ('shopeepay', 'ShopeePay', '#dc2626'),
        ('coins', 'Coins.ph', '#2563eb'),
        ('bpi', 'BPI', '#b91c1c'),
        ('bdo', 'BDO', '#1e3a8a'),
        ('metrobank', 'Metrobank', '#1e40af'),
        ('unionbank', 'UnionBank', '#c2410c'),
        ('landbank', 'Landbank', '#15803d'),
        ('seabank', 'SeaBank', '#c2410c'),
        ('cash', 'Cash / Wallet', '#a16207'),
        ('other', 'Other', '#1e5f43'),
    ]
    COLORS = {value: color for value, _, color in PROVIDERS}

    user = models.ForeignKey(USER, on_delete=models.CASCADE, related_name='accounts')
    provider = models.CharField('Wallet or bank', max_length=12, choices=[(v, label) for v, label, _ in PROVIDERS], default='other')
    name = models.CharField(max_length=60)
    kind = models.CharField(max_length=10, choices=KINDS, default='bank')
    opening_balance = models.DecimalField('Current balance', default=0, help_text='For a credit card, enter what you owe as a negative number.', **MONEY)
    credit_limit = models.DecimalField(null=True, blank=True, help_text='Credit cards only.', **MONEY)
    due_day = models.PositiveSmallIntegerField(null=True, blank=True, help_text='Credit cards only: day of the month the bill is due.')
    group = models.CharField(max_length=40, blank=True, help_text='Optional folder, e.g. "Savings" or "GO TRADE".')
    interest_rate = models.DecimalField('Interest rate (% a year)', max_digits=5, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return self.name

    @property
    def is_liability(self):
        return self.kind == 'credit'

    @property
    def color(self):
        return self.COLORS.get(self.provider, '#1e5f43')

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
    category = models.CharField(max_length=30, default='other')
    date = models.DateField(default=timezone.localdate)
    time = models.TimeField(default=_now_time)
    note = models.CharField(max_length=200, blank=True)
    tags = models.CharField(max_length=100, blank=True, help_text='Comma separated, e.g. japan, birthday')
    photo = models.FileField('Photo or receipt', upload_to='receipts/%Y/%m/', blank=True)
    # account is null for money coming in from outside; to_account is null for money going outside.
    account = models.ForeignKey(Account, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    to_account = models.ForeignKey(Account, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    shared = models.BooleanField('Shared with my household', default=False)

    class Meta:
        ordering = ['-date', '-time', '-id']

    def __str__(self):
        return f'{self.description} ({self.amount})'

    def get_category_display(self):
        return category_label(self.category)

    @property
    def tag_list(self):
        return [t.strip().lower() for t in self.tags.split(',') if t.strip()]


class Budget(models.Model):
    PERIODS = [('daily', 'Daily'), ('weekly', 'Weekly'), ('biweekly', 'Every 2 weeks'), ('monthly', 'Monthly'), ('yearly', 'Yearly')]

    user = models.ForeignKey(USER, on_delete=models.CASCADE, related_name='budgets')
    category = models.CharField(max_length=30)
    period = models.CharField(max_length=10, choices=PERIODS, default='monthly')
    limit = models.DecimalField(**MONEY)

    class Meta:
        ordering = ['category']
        constraints = [models.UniqueConstraint(fields=['user', 'category'], name='one_budget_per_category')]

    def get_category_display(self):
        return category_label(self.category)

    def window(self, today):
        """(start, next_start) of the budget period that contains today."""
        if self.period == 'daily':
            return today, today + timedelta(days=1)
        if self.period in ('weekly', 'biweekly'):
            days = 7 if self.period == 'weekly' else 14
            # bi-weekly periods count from a fixed Monday so they don't drift
            start = today - timedelta(days=(today - date(2024, 1, 1)).days % days)
            return start, start + timedelta(days=days)
        if self.period == 'yearly':
            return today.replace(month=1, day=1), today.replace(year=today.year + 1, month=1, day=1)
        start = today.replace(day=1)
        return start, (start + timedelta(days=32)).replace(day=1)


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
    """Installments, loans and money owed to you: all are 'X a month until Y is paid'."""
    KINDS = [('installment', 'Installment'), ('loan', 'Loan'), ('receivable', 'Money owed to me')]

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


class PlannedPayment(models.Model):
    """A bill or income you expect: once, or repeating."""
    REPEATS = [('once', 'One time'), ('weekly', 'Every week'), ('monthly', 'Every month'), ('yearly', 'Every year')]

    user = models.ForeignKey(USER, on_delete=models.CASCADE, related_name='planned')
    kind = models.CharField(max_length=10, choices=Transaction.KINDS[:2], default='expense')
    name = models.CharField(max_length=60)
    amount = models.DecimalField(**MONEY)
    category = models.CharField(max_length=30, default='bills')
    account = models.ForeignKey(Account, null=True, blank=True, on_delete=models.SET_NULL)
    next_date = models.DateField('Next due', default=timezone.localdate)
    repeat = models.CharField(max_length=10, choices=REPEATS, default='monthly')
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['next_date']

    def advance(self):
        """Move to the next due date, or switch off a one-time payment."""
        d = self.next_date
        if self.repeat == 'once':
            self.active = False
        elif self.repeat == 'weekly':
            self.next_date = d + timedelta(days=7)
        elif self.repeat == 'yearly':
            self.next_date = _add_months(d, 12)
        else:
            self.next_date = _add_months(d, 1)

    def dates_until(self, end):
        """Every due date from next_date up to end (for forecasts)."""
        out, probe = [], PlannedPayment(next_date=self.next_date, repeat=self.repeat)
        while self.active and probe.next_date <= end:
            out.append(probe.next_date)
            if probe.repeat == 'once':
                break
            probe.advance()
        return out


def _add_months(d, n):
    month = d.month - 1 + n
    year, month = d.year + month // 12, month % 12 + 1
    # clamp e.g. Jan 31 + 1 month to Feb 28/29
    for day in (d.day, 30, 29, 28):
        try:
            return d.replace(year=year, month=month, day=day)
        except ValueError:
            continue


class Trip(models.Model):
    user = models.ForeignKey(USER, on_delete=models.CASCADE, related_name='trips')
    name = models.CharField(max_length=60)
    start = models.DateField()
    end = models.DateField()
    budget = models.DecimalField(default=0, **MONEY)

    class Meta:
        ordering = ['-start']

    @property
    def spent(self):
        return _sum(self.user.transactions.filter(kind='expense', date__range=(self.start, self.end)))
