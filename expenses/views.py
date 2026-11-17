from django.db.models import Q, Sum
from django.shortcuts import redirect, render

from .forms import TransactionForm
from .models import Transaction


def _total(qs, kind):
    return qs.filter(kind=kind).aggregate(t=Sum('amount'))['t'] or 0


def home(request):
    all_tx = Transaction.objects.all()
    income = _total(all_tx, Transaction.INCOME)
    expenses = _total(all_tx, Transaction.EXPENSE)
    return render(request, 'expenses/home.html', {
        'available': income - expenses,
        'income': income,
        'expenses': expenses,
        'recent': all_tx[:5],
        'tab': 'home',
    })


def activity(request):
    q = request.GET.get('q', '').strip()
    txs = Transaction.objects.all()
    if q:
        txs = txs.filter(Q(description__icontains=q) | Q(note__icontains=q) | Q(amount__icontains=q))
    return render(request, 'expenses/activity.html', {
        'transactions': txs,
        'spent': _total(txs, Transaction.EXPENSE),
        'q': q,
        'tab': 'activity',
    })


def add_transaction(request):
    form = TransactionForm(request.POST or None, initial={'kind': request.GET.get('kind', Transaction.EXPENSE)})
    if form.is_valid():
        form.save()
        return redirect('activity')
    return render(request, 'expenses/add.html', {'form': form, 'tab': 'activity'})
