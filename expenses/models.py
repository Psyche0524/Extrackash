from django.db import models
from django.utils import timezone


class Transaction(models.Model):
    EXPENSE = 'expense'
    INCOME = 'income'
    KINDS = [(EXPENSE, 'Expense'), (INCOME, 'Income')]

    CATEGORIES = [
        ('dining', 'Dining'),
        ('groceries', 'Groceries'),
        ('transport', 'Transport'),
        ('bills', 'Bills'),
        ('subscriptions', 'Subscriptions'),
        ('shopping', 'Shopping'),
        ('salary', 'Salary'),
        ('other', 'Other'),
    ]

    kind = models.CharField(max_length=10, choices=KINDS, default=EXPENSE)
    description = models.CharField('Merchant or description', max_length=100)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    category = models.CharField(max_length=20, choices=CATEGORIES, default='other')
    date = models.DateField(default=timezone.localdate)
    note = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ['-date', '-id']

    def __str__(self):
        return f'{self.description} ({self.amount})'
