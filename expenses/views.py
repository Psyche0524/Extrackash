import csv
import re
from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from . import forms
from .models import (Account, Budget, Contribution, Debt, Goal, Household, Investment, PlannedPayment, Transaction,
                     Trip, _add_months, category_label)


# ---------- helpers ----------

def _sum(qs):
    return qs.aggregate(t=Sum('amount'))['t'] or Decimal(0)


def _month_start(day=None):
    return (day or timezone.localdate()).replace(day=1)


def _prev_month(day):
    return (day - timedelta(days=1)).replace(day=1)


def _available(user):
    """Net worth: every account's balance added up (credit cards count as negative)."""
    return sum((a.balance for a in user.accounts.all()), Decimal(0))


def _budget_rows(user):
    today = timezone.localdate()
    rows = []
    for b in user.budgets.all():
        start, end = b.window(today)
        spent = _sum(user.transactions.filter(kind='expense', category=b.category, date__gte=start, date__lt=end))
        rows.append({'budget': b, 'spent': spent, 'left': b.limit - spent, 'pct': int(spent / b.limit * 100),
                     'start': start, 'end': end})
    return rows


def _daily_bars(values):
    """[(label, value)] -> rows with a 0-100 height for simple CSS bar charts."""
    peak = max((abs(v) for _, v in values), default=0) or 1
    return [{'label': label, 'value': v, 'pct': int(abs(v) / peak * 100)} for label, v in values]


def _insight(user):
    """One friendly sentence about this month, like the mascot tip in the recording."""
    month = user.transactions.filter(date__gte=_month_start())
    income, spent = _sum(month.filter(kind='income')), _sum(month.filter(kind='expense'))
    if not month.exists():
        return 'Log your first expense or income today to start seeing your patterns.'
    if spent > income:
        return "You've spent more than the income you've logged this month. Check your balances and any income you haven't logged."
    over = [r for r in _budget_rows(user) if r['left'] < 0]
    if over:
        return f"You're over your {over[0]['budget'].get_category_display()} budget. A slower few days will even it out."
    return f"You've kept {income - spent:,.0f} pesos of this month's income. That's money with room to grow."


def _form_page(request, form_class, title, done, instance=None, subtitle='', initial=None, on_save=None):
    """One page for every add/edit form. `on_save(obj)` fills fields the form doesn't show."""
    form = form_class(request.user, request.POST or None, request.FILES or None, instance=instance, initial=initial)
    if form.is_valid():
        obj = form.save(commit=False)
        if on_save:
            on_save(obj)
        obj.save()
        form.save_m2m()
        messages.success(request, 'Saved.')
        return redirect(done(obj) if callable(done) else done)
    return render(request, 'expenses/form.html', {'form': form, 'title': title, 'subtitle': subtitle, 'back': request.GET.get('back', '')})


def _delete(request, obj, done, label):
    obj.delete()
    messages.success(request, f'{label} removed.')
    return redirect(done)


def _set_user(request):
    return lambda obj: setattr(obj, 'user', request.user)


# ---------- welcome, sign up, set up ----------

def welcome(request):
    if request.user.is_authenticated:
        return redirect('home')
    return render(request, 'expenses/welcome.html')


def signup(request):
    form = forms.SignUpForm(request.POST or None)
    if form.is_valid():
        login(request, form.save())
        return redirect('setup')
    return render(request, 'expenses/signup.html', {'form': form})


@login_required
def setup(request):
    form = forms.AccountForm(request.user, request.POST or None)
    if form.is_valid():
        account = form.save(commit=False)
        account.user = request.user
        account.save()
        return redirect('ready')
    return render(request, 'expenses/setup.html', {'form': form})


@login_required
def ready(request):
    return render(request, 'expenses/ready.html')


# ---------- home & activity ----------

def _streak(user):
    """Days in a row (ending today or yesterday) with at least one logged transaction."""
    days = set(user.transactions.values_list('date', flat=True))
    day, count = timezone.localdate(), 0
    if day not in days:
        day -= timedelta(days=1)
    while day in days:
        count, day = count + 1, day - timedelta(days=1)
    return count


def _greeting(hour):
    if hour < 12:
        return 'morning'
    return 'afternoon' if hour < 18 else 'evening'


def _forecast(user, months):
    """Expected bills and income per month from planned payments."""
    start = _month_start()
    planned = list(user.planned.filter(active=True))
    rows, m = [], start
    for _ in range(months):
        nxt = (m + timedelta(days=32)).replace(day=1)
        bills = income = Decimal(0)
        for p in planned:
            hits = [d for d in p.dates_until(nxt - timedelta(days=1)) if d >= m]
            if p.kind == 'income':
                income += p.amount * len(hits)
            else:
                bills += p.amount * len(hits)
        rows.append({'month': m, 'bills': bills, 'income': income, 'net': income - bills})
        m = nxt
    return rows


@login_required
def home(request):
    user = request.user
    today = timezone.localdate()
    span = request.GET.get('span', 'day')
    since = {'week': today - timedelta(days=today.weekday()), 'month': _month_start()}.get(span, today)
    period = user.transactions.filter(date__gte=since)
    week = [(d.strftime('%a')[0], _sum(user.transactions.filter(kind='expense', date=d)))
            for d in (today - timedelta(days=i) for i in range(6, -1, -1))]
    due = [p for p in user.planned.filter(active=True, kind='expense').select_related('account')
           if p.next_date <= today + timedelta(days=31)]
    for p in due:
        p.days_left = (p.next_date - today).days
    years = {'3y': 3, '5y': 5}.get(request.GET.get('forecast'), 1)
    return render(request, 'expenses/home.html', {
        'today': today, 'streak': _streak(user), 'insight': _insight(user),
        'greeting': _greeting(timezone.localtime().hour),
        'span': span, 'span_in': _sum(period.filter(kind='income')), 'span_out': _sum(period.filter(kind='expense')),
        'week': _daily_bars(week), 'due': due, 'due_total': sum(p.amount for p in due),
        'forecast': _forecast(user, 12 * years), 'years': years,
        'recent': user.transactions.select_related('account')[:5],
        'tab': 'home',
    })


@login_required
def activity(request):
    """History: filter by text, date, type, account or tag; grouped by day with totals."""
    f = request.GET
    txs = request.user.transactions.select_related('account', 'to_account')
    if f.get('q'):
        q = f['q'].strip()
        txs = txs.filter(Q(description__icontains=q) | Q(note__icontains=q) | Q(amount__icontains=q) | Q(category__icontains=q))
    if f.get('date'):
        txs = txs.filter(date=f['date'])
    if f.get('kind') in ('expense', 'income', 'transfer'):
        txs = txs.filter(kind=f['kind'])
    if f.get('account', '').isdigit():
        txs = txs.filter(Q(account_id=f['account']) | Q(to_account_id=f['account']))
    if f.get('tag'):
        txs = txs.filter(tags__icontains=f['tag'])
    days = {}
    for t in txs:
        day = days.setdefault(t.date, {'date': t.date, 'items': [], 'out': Decimal(0), 'in': Decimal(0)})
        day['items'].append(t)
        if t.kind == 'expense':
            day['out'] += t.amount
        elif t.kind == 'income':
            day['in'] += t.amount
    return render(request, 'expenses/activity.html', {
        'days': days.values(), 'f': f, 'accounts': request.user.accounts.all(), 'filtered': any(f.values()),
        'today': timezone.localdate(),
        'tab': 'activity',
    })


@login_required
def add_transaction(request):
    user = request.user
    if not user.accounts.exists():
        messages.info(request, 'Add an account first.')
        return redirect('account_new')
    form = forms.TransactionForm(user, request.POST or None, request.FILES or None, initial={
        'kind': request.GET.get('kind', Transaction.EXPENSE),
        'account': user.accounts.first(),
    })
    if form.is_valid():
        tx = form.save(commit=False)
        tx.user = user
        tx.save()
        data = form.cleaned_data
        if data.get('recurring'):
            user.planned.create(kind=tx.kind, name=tx.description, amount=tx.amount, category=tx.category,
                                account=tx.account, next_date=_add_months(tx.date, 1), repeat='monthly')
        if data.get('owed_amount'):
            user.debts.create(kind='receivable', name=data['owed_by'], total=data['owed_amount'],
                              monthly=data['owed_amount'], account=tx.account, note=f'For {tx.description}')
        messages.success(request, 'Income saved.' if tx.kind == 'income' else 'Expense saved.')
        return redirect('activity')
    return render(request, 'expenses/add.html', {'form': form, 'tab': 'activity', 'scan': 'scan' in request.GET})


@login_required
def transaction_photo(request, pk):
    tx = get_object_or_404(Transaction, pk=pk, user=request.user)
    if not tx.photo:
        raise Http404
    return FileResponse(tx.photo.open('rb'))


@login_required
def transaction_detail(request, pk):
    tx = get_object_or_404(Transaction, pk=pk, user=request.user)
    return render(request, 'expenses/transaction.html', {'t': tx, 'tab': 'activity'})


@login_required
def transaction_edit(request, pk):
    tx = get_object_or_404(Transaction, pk=pk, user=request.user)
    is_transfer = tx.kind == 'transfer'
    form_class = forms.TransferForm if is_transfer else forms.TransactionForm
    form = form_class(request.user, request.POST or None, request.FILES or None, instance=tx)
    if form.is_valid():
        form.save()
        messages.success(request, 'Saved.')
        return redirect('transaction', pk=tx.pk)
    return render(request, 'expenses/transfer.html' if is_transfer else 'expenses/add.html', {'form': form, 'tab': 'activity'})


@login_required
@require_POST
def transaction_delete(request, pk):
    return _delete(request, get_object_or_404(Transaction, pk=pk, user=request.user), 'activity', 'Transaction')


@login_required
def transfer(request):
    user = request.user
    accounts = list(user.accounts.all())
    first, second = (accounts + [None, None])[:2]
    form = forms.TransferForm(user, request.POST or None, request.FILES or None, initial={
        'account': first, 'to_account': request.GET.get('to') or second,
    })
    if form.is_valid():
        tx = form.save(commit=False)
        tx.user, tx.kind, tx.category = user, 'transfer', 'other'
        tx.description = f'{tx.account or "Outside"} → {tx.to_account or "Outside"}'
        tx.save()
        if form.cleaned_data.get('fee'):
            Transaction.objects.create(user=user, kind='expense', category='fees', amount=form.cleaned_data['fee'],
                                       description='Transfer fee', account=tx.account, date=tx.date, time=tx.time)
        messages.success(request, 'Transfer recorded.')
        return redirect('accounts')
    return render(request, 'expenses/transfer.html', {'form': form, 'tab': 'wallet'})


# ---------- plan: hub, budgets, goals, cashflow, planned payments, travel, tags ----------

@login_required
def plan(request):
    user = request.user
    debts = user.debts.all()
    return render(request, 'expenses/plan_hub.html', {
        'budgets': user.budgets.count(), 'goals': user.goals.count(),
        'loans': debts.filter(kind='loan').count(), 'installments': debts.filter(kind='installment').count(),
        'receivables': debts.filter(kind='receivable').count(),
        'recurring': user.planned.filter(active=True).exclude(repeat='once').count(),
        'one_time': user.planned.filter(active=True, repeat='once').count(),
        'investments': user.investments.count(), 'trips': user.trips.count(),
        'tab': 'plan',
    })


@login_required
def budgets(request):
    rows = _budget_rows(request.user)
    total = sum(r['budget'].limit for r in rows)
    spent = sum(r['spent'] for r in rows)
    return render(request, 'expenses/plan.html', {
        'rows': rows, 'total': total, 'spent': spent, 'left': total - spent,
        'pct': int(spent / total * 100) if total else 0, 'month': timezone.localdate(), 'tab': 'plan', 'sub': 'budgets',
    })


@login_required
def budget_detail(request, pk):
    budget = get_object_or_404(Budget, pk=pk, user=request.user)
    row = next(r for r in _budget_rows(request.user) if r['budget'] == budget)
    days_left = (row['end'] - timezone.localdate()).days
    recent = request.user.transactions.filter(kind='expense', category=budget.category,
                                              date__gte=row['start'], date__lt=row['end']).select_related('account')
    return render(request, 'expenses/budget.html', {
        **row, 'recent': recent, 'days_left': days_left, 'next_month': row['end'],
        'per_day': max(row['left'], 0) / days_left, 'tab': 'plan',
    })


@login_required
def planned(request):
    items = list(request.user.planned.filter(active=True).select_related('account'))
    return render(request, 'expenses/planned.html', {
        'items': items, 'month_total': sum(p.amount for p in items if p.kind == 'expense' and p.next_date < _add_month_start()),
        'tab': 'plan',
    })


def _add_month_start():
    return (_month_start() + timedelta(days=32)).replace(day=1)


@login_required
def planned_new(request):
    return _form_page(request, forms.PlannedPaymentForm, 'Plan a payment', 'planned', on_save=_set_user(request),
                      initial={'kind': request.GET.get('kind', 'expense')})


@login_required
def planned_edit(request, pk):
    item = get_object_or_404(PlannedPayment, pk=pk, user=request.user)
    return _form_page(request, forms.PlannedPaymentForm, 'Edit planned payment', 'planned', instance=item)


@login_required
@require_POST
def planned_done(request, pk):
    """Record this occurrence as a real transaction and move to the next due date."""
    item = get_object_or_404(PlannedPayment, pk=pk, user=request.user, active=True)
    Transaction.objects.create(user=request.user, kind=item.kind, amount=item.amount, category=item.category,
                               description=item.name, account=item.account)
    item.advance()
    item.save()
    messages.success(request, 'Payment recorded.')
    return redirect(request.POST.get('next') or 'planned')


@login_required
@require_POST
def planned_delete(request, pk):
    return _delete(request, get_object_or_404(PlannedPayment, pk=pk, user=request.user), 'planned', 'Planned payment')


@login_required
def trips(request):
    trip_list = list(request.user.trips.all())
    for t in trip_list:
        t.total = t.spent
        t.pct = int(t.total / t.budget * 100) if t.budget else 0
    return render(request, 'expenses/trips.html', {'trips': trip_list, 'tab': 'plan'})


@login_required
def trip_new(request):
    return _form_page(request, forms.TripForm, 'Plan a trip', 'trips', on_save=_set_user(request),
                      subtitle='Spending between the start and end dates counts toward the trip.')


@login_required
def trip_edit(request, pk):
    trip = get_object_or_404(Trip, pk=pk, user=request.user)
    return _form_page(request, forms.TripForm, 'Edit trip', 'trips', instance=trip)


@login_required
@require_POST
def trip_delete(request, pk):
    return _delete(request, get_object_or_404(Trip, pk=pk, user=request.user), 'trips', 'Trip')


@login_required
def tags(request):
    totals = {}
    for t in request.user.transactions.exclude(tags='').filter(kind='expense'):
        for tag in t.tag_list:
            row = totals.setdefault(tag, {'tag': tag, 'total': Decimal(0), 'count': 0})
            row['total'] += t.amount
            row['count'] += 1
    return render(request, 'expenses/tags.html', {
        'tags': sorted(totals.values(), key=lambda r: -r['total']), 'tab': 'plan',
    })


@login_required
def budget_new(request):
    return _form_page(request, forms.BudgetForm, 'Create budget', 'plan', on_save=_set_user(request),
                      initial={'category': request.GET.get('category')})


@login_required
def budget_edit(request, pk):
    budget = get_object_or_404(Budget, pk=pk, user=request.user)
    return _form_page(request, forms.BudgetForm, 'Edit budget', lambda b: f'/plan/budgets/{b.pk}/', instance=budget)


@login_required
@require_POST
def budget_delete(request, pk):
    return _delete(request, get_object_or_404(Budget, pk=pk, user=request.user), 'plan', 'Budget')


@login_required
def goals(request):
    goal_list = list(request.user.goals.all())
    return render(request, 'expenses/goals.html', {
        'goals': goal_list, 'total': sum(g.saved for g in goal_list), 'tab': 'plan', 'sub': 'goals',
    })


@login_required
def goal_detail(request, pk):
    goal = get_object_or_404(Goal, pk=pk, user=request.user)
    saved = goal.saved
    return render(request, 'expenses/goal.html', {
        'goal': goal, 'saved': saved, 'left': max(goal.target - saved, 0),
        'pct': min(int(saved / goal.target * 100), 100), 'tab': 'plan',
    })


@login_required
def goal_new(request):
    return _form_page(request, forms.GoalForm, 'Create goal', 'goals', on_save=_set_user(request))


@login_required
def goal_edit(request, pk):
    goal = get_object_or_404(Goal, pk=pk, user=request.user)
    return _form_page(request, forms.GoalForm, 'Edit goal', lambda g: f'/plan/goals/{g.pk}/', instance=goal)


@login_required
def goal_add_money(request, pk):
    goal = get_object_or_404(Goal, pk=pk, user=request.user)
    return _form_page(request, forms.ContributionForm, f'Add to {goal.name}', f'/plan/goals/{goal.pk}/',
                      on_save=lambda c: setattr(c, 'goal', goal))


@login_required
@require_POST
def goal_delete(request, pk):
    return _delete(request, get_object_or_404(Goal, pk=pk, user=request.user), 'goals', 'Goal')


@login_required
def cashflow(request):
    user = request.user
    today = timezone.localdate()
    last_30 = user.transactions.filter(date__gt=today - timedelta(days=30))
    # shortcut: projects the last 30 days forward; add recurring transactions if users need exact forecasts.
    income = _sum(last_30.filter(kind='income'))
    spending = _sum(last_30.filter(kind='expense'))
    debts = [d for d in user.debts.all() if d.remaining > 0]
    commitments = sum(min(d.monthly, d.remaining) for d in debts)
    available = _available(user)
    return render(request, 'expenses/cashflow.html', {
        'available': available, 'income': income, 'spending': spending, 'commitments': commitments,
        'debt_count': len(debts), 'projected': available + income - spending - commitments,
        'until': today + timedelta(days=30), 'tab': 'plan', 'sub': 'cashflow',
    })


# ---------- accounts, cards, installments, debts ----------

def _net_change(t):
    """How much one transaction changes net worth (moves between your own accounts change nothing)."""
    if t.kind == 'income':
        return t.amount
    if t.kind == 'expense':
        return -t.amount
    return (t.amount if t.to_account_id else 0) - (t.amount if t.account_id else 0)


@login_required
def accounts(request):
    user = request.user
    show = request.GET.get('show', 'all')
    group = request.GET.get('group', '')
    account_list = list(user.accounts.all())
    for a in account_list:
        a.bal = a.balance
    assets = sum((a.bal for a in account_list if not a.is_liability), Decimal(0))
    liabilities = -sum((a.bal for a in account_list if a.is_liability), Decimal(0))
    net = assets - liabilities

    # Net worth at the end of each of the last 7 days = today's net worth minus what changed since.
    today = timezone.localdate()
    recent = list(user.transactions.filter(date__gt=today - timedelta(days=7)))
    daily = [(d.strftime('%a')[0], net - sum((_net_change(t) for t in recent if t.date > d), Decimal(0)))
             for d in (today - timedelta(days=i) for i in range(6, -1, -1))]

    shown = [a for a in account_list if show == 'all' or (show == 'liabilities') == a.is_liability]
    if group:
        shown = [a for a in shown if (a.group or 'Ungrouped') == group]
    groups = {}
    for a in shown:
        g = groups.setdefault(a.group or 'Accounts', {'name': a.group or 'Accounts', 'items': [], 'total': Decimal(0)})
        g['items'].append(a)
        g['total'] += a.bal
    return render(request, 'expenses/accounts.html', {
        'net': net, 'assets': assets, 'liabilities': liabilities, 'show': show, 'group': group,
        'group_names': sorted({a.group for a in account_list if a.group}), 'groups': groups.values(),
        'view': request.GET.get('view', 'grid'), 'daily': _daily_bars(daily), 'insight': _insight(user),
        'recent_income': user.transactions.filter(kind='income').select_related('account')[:5],
        'tab': 'wallet',
    })


@login_required
def account_new(request):
    return _form_page(request, forms.AccountForm, 'Add wallet', 'accounts', on_save=_set_user(request),
                      initial={'kind': request.GET.get('kind', 'bank')})


@login_required
def account_edit(request, pk):
    account = get_object_or_404(Account, pk=pk, user=request.user)
    return _form_page(request, forms.AccountForm, 'Edit account', 'accounts', instance=account)


@login_required
@require_POST
def account_delete(request, pk):
    return _delete(request, get_object_or_404(Account, pk=pk, user=request.user), 'accounts', 'Account')


@login_required
def cards(request):
    cards = []
    for a in request.user.accounts.filter(kind='credit'):
        owed = max(-a.balance, 0)
        limit = a.credit_limit or 0
        cards.append({'card': a, 'owed': owed, 'available': limit - owed, 'pct': int(owed / limit * 100) if limit else 0})
    return render(request, 'expenses/cards.html', {
        'cards': cards, 'installments': request.user.debts.filter(kind='installment').count(), 'tab': 'plan',
    })


@login_required
def debts(request, kind):
    debt_list = list(request.user.debts.filter(kind=kind).select_related('account'))
    for d in debt_list:
        d.pct = min(int(d.paid / d.total * 100), 100)
    active = [d for d in debt_list if d.remaining > 0]
    return render(request, 'expenses/debts.html', {
        'debts': debt_list, 'kind': kind, 'monthly': sum(min(d.monthly, d.remaining) for d in active),
        'remaining': sum(d.remaining for d in active), 'tab': 'plan',
    })


DEBT_TITLES = {'installment': 'Track installment', 'loan': 'Add loan', 'receivable': 'Someone owes me'}


@login_required
def debt_new(request):
    kind = request.GET.get('kind', 'installment')
    return _form_page(request, forms.DebtForm, DEBT_TITLES.get(kind, 'Add'),
                      lambda d: f'/explore/{d.kind}s/', on_save=_set_user(request), initial={'kind': kind})


@login_required
def debt_edit(request, pk):
    debt = get_object_or_404(Debt, pk=pk, user=request.user)
    return _form_page(request, forms.DebtForm, 'Adjust plan', lambda d: f'/explore/{d.kind}s/', instance=debt)


@login_required
@require_POST
def debt_pay(request, pk):
    """Pay one instalment, or for money owed to you, record that they paid you back."""
    debt = get_object_or_404(Debt, pk=pk, user=request.user)
    amount = min(debt.monthly, debt.remaining)
    if amount > 0:
        debt.paid += amount
        debt.save()
        if debt.kind == 'receivable':
            Transaction.objects.create(user=request.user, kind='income', amount=amount, category='other',
                                       description=f'Paid back: {debt.name}', account=debt.account)
            messages.success(request, 'Settlement recorded.')
        else:
            Transaction.objects.create(user=request.user, kind='expense', amount=amount, category='bills',
                                       description=f'Payment: {debt.name}', account=debt.account)
            messages.success(request, 'Payment recorded.')
    return redirect(f'/explore/{debt.kind}s/')


@login_required
@require_POST
def debt_delete(request, pk):
    debt = get_object_or_404(Debt, pk=pk, user=request.user)
    return _delete(request, debt, f'/explore/{debt.kind}s/', 'Plan')


# ---------- investments ----------

@login_required
def investments(request):
    items = list(request.user.investments.all())
    value = sum(i.value for i in items)
    invested = sum(i.invested for i in items)
    for i in items:
        i.share = int(i.value / value * 100) if value else 0
    return render(request, 'expenses/investments.html', {
        'items': items, 'value': value, 'gain': value - invested,
        'gain_pct': round((value - invested) / invested * 100, 2) if invested else 0, 'tab': 'plan',
    })


@login_required
def investment_new(request):
    return _form_page(request, forms.InvestmentForm, 'Add holding', 'investments', on_save=_set_user(request))


@login_required
def investment_edit(request, pk):
    item = get_object_or_404(Investment, pk=pk, user=request.user)
    return _form_page(request, forms.InvestmentForm, 'Update investment', 'investments', instance=item)


@login_required
@require_POST
def investment_delete(request, pk):
    return _delete(request, get_object_or_404(Investment, pk=pk, user=request.user), 'investments', 'Holding')


# ---------- reports ----------

@login_required
def reports(request):
    period = request.GET.get('period', 'month')
    today = timezone.localdate()
    if period == 'week':
        start = today - timedelta(days=today.weekday())
        prev_start = start - timedelta(days=7)
    elif period == 'year':
        start = today.replace(month=1, day=1)
        prev_start = start.replace(year=start.year - 1)
    else:
        period = 'month'
        start = _month_start()
        prev_start = _prev_month(start)
    expenses = request.user.transactions.filter(kind='expense')
    spent = _sum(expenses.filter(date__gte=start))
    prev = _sum(expenses.filter(date__gte=prev_start, date__lte=prev_start + (today - start)))

    by_cat = expenses.filter(date__gte=start).values('category').annotate(total=Sum('amount')).order_by('-total')
    top = by_cat[0]['total'] if by_cat else 1
    cats = [{'label': category_label(c['category']), 'total': c['total'], 'pct': int(c['total'] / top * 100)} for c in by_cat]

    months, m = [], _month_start()
    for _ in range(6):
        nxt = (m.replace(day=28) + timedelta(days=4)).replace(day=1)
        months.append({'month': m, 'total': _sum(expenses.filter(date__gte=m, date__lt=nxt))})
        m = _prev_month(m)
    months.reverse()
    peak = max(x['total'] for x in months) or 1
    for x in months:
        x['pct'] = int(x['total'] / peak * 100)

    return render(request, 'expenses/reports.html', {
        'period': period, 'start': start, 'spent': spent, 'diff': prev - spent, 'cats': cats, 'months': months, 'tab': 'plan',
    })


@login_required
def export_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="extrackash-transactions.csv"'
    writer = csv.writer(response)
    writer.writerow(['Date', 'Type', 'Description', 'Category', 'Account', 'To account', 'Amount', 'Note'])
    for t in request.user.transactions.select_related('account', 'to_account').order_by('date', 'id'):
        writer.writerow([t.date, t.kind, t.description, t.get_category_display(), t.account or '', t.to_account or '', t.amount, t.note])
    return response


# ---------- shared finances ----------

@login_required
def shared(request):
    home = request.user.households.prefetch_related('members').first()
    if not home:
        return render(request, 'expenses/shared.html', {'tab': 'plan'})
    members = list(home.members.all())
    shared_tx = Transaction.objects.filter(user__in=members, shared=True, kind='expense', date__gte=_month_start())
    total = _sum(shared_tx)
    share = total / len(members)
    people = [{'user': m, 'paid': _sum(shared_tx.filter(user=m))} for m in members]
    for p in people:
        p['balance'] = p['paid'] - share  # + means others owe them
    return render(request, 'expenses/shared.html', {
        'home': home, 'members': members, 'people': people, 'total': total, 'share': share,
        'left': home.shared_budget - total, 'pct': int(total / home.shared_budget * 100) if home.shared_budget else 0,
        'tab': 'plan',
    })


@login_required
def household_new(request):
    form = forms.HouseholdForm(request.user, request.POST or None)
    if form.is_valid():
        home = form.save()
        home.members.add(request.user)
        messages.success(request, 'Household created.')
        return redirect('shared')
    return render(request, 'expenses/form.html', {'form': form, 'title': 'Create household', 'subtitle': 'Share spending with people you live with.'})


@login_required
def household_invite(request):
    home = get_object_or_404(Household, members=request.user)
    form = forms.InviteForm(request.POST or None)
    if form.is_valid():
        home.members.add(form.cleaned_data['email'])
        messages.success(request, 'Member added.')
        return redirect('shared')
    return render(request, 'expenses/form.html', {'form': form, 'title': 'Invite member', 'subtitle': 'Shared spaces show your name and shared expenses only.'})


@login_required
@require_POST
def household_leave(request):
    home = get_object_or_404(Household, members=request.user)
    home.members.remove(request.user)
    if not home.members.exists():
        home.delete()
    messages.success(request, 'You left the household.')
    return redirect('shared')


# ---------- chat ----------

@login_required
def chat(request):
    # shortcut: rule-based answers from the user's own numbers, no AI service; swap in an LLM API later if wanted.
    question = request.GET.get('q', '').strip()
    answer = None
    if question:
        user = request.user
        rows = _budget_rows(user)
        left = sum(r['left'] for r in rows) if rows else _available(user)
        today = timezone.localdate()
        days_left = ((today.replace(day=28) + timedelta(days=4)).replace(day=1) - today).days
        amount = re.search(r'(\d[\d,]*(?:\.\d+)?)', question)
        if amount:
            want = Decimal(amount.group(1).replace(',', ''))
            after = left - want
            answer = {
                'title': 'Yes, with a small adjustment.' if after >= 0 else 'Not comfortably this month.',
                'body': f'You have ₱{left:,.2f} left {"in your plan" if rows else "available"}. '
                        f'Setting aside ₱{want:,.2f} would leave ₱{after:,.2f} for the next {days_left} days.',
                'step': f'Aim for about ₱{max(after, 0) / days_left:,.0f} a day in remaining spending.' if after >= 0
                        else 'Try a smaller amount, or move part of it to next month.',
            }
        else:
            start = _month_start()
            this = _sum(user.transactions.filter(kind='expense', date__gte=start))
            prev_start = _prev_month(start)
            prev = _sum(user.transactions.filter(kind='expense', date__gte=prev_start, date__lte=prev_start + (today - start)))
            answer = {
                'title': 'Spending is down.' if this <= prev else 'Spending is up.',
                'body': f'This month you spent ₱{this:,.2f}. At this point last month it was ₱{prev:,.2f}.',
                'step': 'Ask "Can I save 5000 this month?" to check a savings amount.',
            }
    return render(request, 'expenses/chat.html', {'question': question, 'answer': answer, 'today': timezone.localdate(), 'tab': 'plan'})


# ---------- explore & settings ----------

def explore(request):
    return redirect('plan')  # Explore was merged into the Plan hub; keep old links working.


@login_required
def settings_page(request):
    return render(request, 'expenses/settings.html', {'tab': 'plan'})


@login_required
def profile_edit(request):
    form = forms.ProfileForm(request.POST or None, instance=request.user)
    if form.is_valid():
        form.save()
        messages.success(request, 'Your preferences are saved.')
        return redirect('settings')
    return render(request, 'expenses/form.html', {'form': form, 'title': 'Edit profile', 'subtitle': 'Your email is also how you log in.'})


@login_required
def delete_account(request):
    if request.method == 'POST' and request.POST.get('confirm') == 'DELETE':
        user = request.user
        logout(request)
        user.delete()
        messages.success(request, 'Your account and data were deleted.')
        return redirect('welcome')
    return render(request, 'expenses/delete_account.html', {'tab': 'plan'})
