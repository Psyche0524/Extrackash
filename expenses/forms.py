from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from .models import (EXPENSE_CATEGORIES, INCOME_CATEGORIES, LABELS, Account, Budget, Contribution, Debt, Goal,
                     Household, Investment, PlannedPayment, Transaction, Trip, _now_time, category_label)

DATE = forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d')
MONEY = forms.NumberInput(attrs={'step': '0.01', 'inputmode': 'decimal', 'placeholder': '0.00'})


class UserForm(forms.ModelForm):
    """ModelForm that only offers the current user's accounts in account dropdowns."""

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ('account', 'to_account'):
            if name in self.fields:
                self.fields[name].queryset = user.accounts.all()


def positive(form, name):
    value = form.cleaned_data[name]
    if value is not None and value <= 0:
        raise forms.ValidationError('Must be more than 0.')
    return value


TIME = forms.TimeInput(attrs={'type': 'time'}, format='%H:%M')
PHOTO = forms.ClearableFileInput(attrs={'accept': 'image/*'})
MAX_PHOTO = 5 * 1024 * 1024


def check_photo(form):
    photo = form.cleaned_data.get('photo')
    if photo and hasattr(photo, 'content_type'):  # a new upload, not the saved file
        if not photo.content_type.startswith('image/'):
            raise forms.ValidationError('Please choose an image.')
        if photo.size > MAX_PHOTO:
            raise forms.ValidationError('Photo is too big (5 MB max).')
    return photo


def custom_categories(user, kind):
    """Categories this user typed in before, so they show up as chips next time."""
    built_in = {v for v, _ in (EXPENSE_CATEGORIES if kind == 'expense' else INCOME_CATEGORIES)}
    used = user.transactions.filter(kind=kind).values_list('category', flat=True).distinct()
    return [(c, c) for c in used if c not in built_in and c not in LABELS]


class TransactionForm(UserForm):
    new_category = forms.CharField(label='New category', max_length=30, required=False,
                                   widget=forms.TextInput(attrs={'placeholder': '+ Add your own category'}))
    recurring = forms.BooleanField(label='Repeat every month', required=False)
    owed_by = forms.CharField(label='Someone owes me part of this', max_length=60, required=False,
                              widget=forms.TextInput(attrs={'placeholder': 'Their name'}))
    owed_amount = forms.DecimalField(label='How much they owe', required=False, widget=MONEY)

    class Meta:
        model = Transaction
        fields = ['kind', 'amount', 'category', 'description', 'account', 'date', 'time', 'note', 'tags', 'photo', 'shared']
        labels = {'description': 'Name (optional)'}
        widgets = {'kind': forms.RadioSelect, 'date': DATE, 'time': TIME, 'photo': PHOTO,
                   'amount': forms.TextInput(attrs={'inputmode': 'decimal', 'placeholder': '0', 'autocomplete': 'off'}),
                   'note': forms.TextInput(attrs={'placeholder': 'Add a note…'})}

    def __init__(self, user, *args, **kwargs):
        super().__init__(user, *args, **kwargs)
        self.fields['kind'].choices = Transaction.KINDS[:2]  # transfers have their own form
        self.fields['account'].required = True
        self.fields['description'].required = False
        self.fields['category'].required = False
        self.fields['time'].required = False
        self.expense_categories = EXPENSE_CATEGORIES + custom_categories(user, 'expense')
        self.income_categories = INCOME_CATEGORIES + custom_categories(user, 'income')
        if not user.households.exists():
            del self.fields['shared']
        if self.instance.pk:  # editing: these only make sense when adding
            for name in ('recurring', 'owed_by', 'owed_amount'):
                del self.fields[name]

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if amount <= 0:
            raise forms.ValidationError('Amount must be more than 0.')
        return amount

    def clean_photo(self):
        return check_photo(self)

    def clean(self):
        data = super().clean()
        data['time'] = data.get('time') or _now_time()
        data['category'] = (data.get('new_category') or '').strip() or data.get('category') or 'other'
        if not data.get('description'):
            data['description'] = category_label(data['category'])
        owed = data.get('owed_amount')
        if owed is not None and (owed <= 0 or (data.get('amount') and owed > data['amount'])):
            self.add_error('owed_amount', 'Must be more than 0 and not more than the amount.')
        if owed and not data.get('owed_by'):
            self.add_error('owed_by', 'Who owes you?')
        return data


class TransferForm(UserForm):
    MODES = [('mine', 'My accounts'), ('external', 'Outside')]
    source = forms.ChoiceField(choices=MODES, initial='mine', required=False, widget=forms.RadioSelect)
    destination = forms.ChoiceField(choices=MODES, initial='mine', required=False, widget=forms.RadioSelect)
    fee = forms.DecimalField(label='Transfer fee (optional)', required=False, widget=MONEY)

    class Meta:
        model = Transaction
        fields = ['account', 'to_account', 'amount', 'date', 'time', 'note', 'photo']
        labels = {'account': 'From account', 'to_account': 'To account', 'note': 'Note (optional)'}
        widgets = {'date': DATE, 'time': TIME, 'amount': MONEY, 'photo': PHOTO}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['time'].required = False
        if self.instance.pk:
            self.initial.setdefault('source', 'mine' if self.instance.account_id else 'external')
            self.initial.setdefault('destination', 'mine' if self.instance.to_account_id else 'external')

    def clean_amount(self):
        return positive(self, 'amount')

    def clean_photo(self):
        return check_photo(self)

    def clean(self):
        data = super().clean()
        data['time'] = data.get('time') or _now_time()
        data['source'] = data.get('source') or 'mine'
        data['destination'] = data.get('destination') or 'mine'
        if data.get('source') == 'external':
            data['account'] = None
        elif not data.get('account'):
            self.add_error('account', 'Pick the account the money leaves.')
        if data.get('destination') == 'external':
            data['to_account'] = None
        elif not data.get('to_account'):
            self.add_error('to_account', 'Pick the account the money goes to.')
        if data.get('source') == data.get('destination') == 'external':
            raise forms.ValidationError('At least one side must be one of your accounts.')
        if data.get('account') and data.get('account') == data.get('to_account'):
            raise forms.ValidationError('Pick two different accounts.')
        fee = data.get('fee')
        if fee is not None and fee < 0:
            self.add_error('fee', 'Fee cannot be negative.')
        if fee and not data.get('account'):
            self.add_error('fee', 'Fees come out of one of your accounts.')
        return data


class AccountForm(UserForm):
    class Meta:
        model = Account
        fields = ['provider', 'name', 'kind', 'group', 'opening_balance', 'interest_rate', 'credit_limit', 'due_day']
        widgets = {'opening_balance': MONEY, 'credit_limit': MONEY}
        help_texts = {'name': 'Leave blank to use the wallet or bank name.'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].required = False

    def clean(self):
        data = super().clean()
        if not data.get('name') and data.get('provider'):
            data['name'] = dict(self.fields['provider'].choices)[data['provider']]
        return data


class BudgetForm(UserForm):
    class Meta:
        model = Budget
        fields = ['category', 'period', 'limit']
        widgets = {'limit': MONEY}

    def __init__(self, user, *args, **kwargs):
        super().__init__(user, *args, **kwargs)
        self.user = user
        self.fields['category'].widget = forms.Select(choices=EXPENSE_CATEGORIES + custom_categories(user, 'expense'))

    def clean_limit(self):
        return positive(self, 'limit')

    def clean_category(self):
        category = self.cleaned_data['category']
        taken = self.user.budgets.filter(category=category).exclude(pk=self.instance.pk)
        if taken.exists():
            raise forms.ValidationError('You already have a budget for this category.')
        return category


class GoalForm(UserForm):
    class Meta:
        model = Goal
        fields = ['name', 'note', 'target', 'target_date']
        widgets = {'target': MONEY, 'target_date': DATE}

    def clean_target(self):
        return positive(self, 'target')


class ContributionForm(UserForm):
    class Meta:
        model = Contribution
        fields = ['amount', 'description', 'date']
        widgets = {'amount': MONEY, 'date': DATE}

    def clean_amount(self):
        return positive(self, 'amount')


class DebtForm(UserForm):
    class Meta:
        model = Debt
        fields = ['kind', 'name', 'total', 'monthly', 'paid', 'account', 'due_day', 'note']
        widgets = {'total': MONEY, 'monthly': MONEY, 'paid': MONEY}

    def clean_total(self):
        return positive(self, 'total')

    def clean_monthly(self):
        return positive(self, 'monthly')


class PlannedPaymentForm(UserForm):
    class Meta:
        model = PlannedPayment
        fields = ['kind', 'name', 'amount', 'category', 'account', 'next_date', 'repeat']
        widgets = {'amount': MONEY, 'next_date': DATE}

    def __init__(self, user, *args, **kwargs):
        super().__init__(user, *args, **kwargs)
        self.fields['category'].widget = forms.Select(choices=EXPENSE_CATEGORIES + INCOME_CATEGORIES[:-1])

    def clean_amount(self):
        return positive(self, 'amount')


class TripForm(UserForm):
    class Meta:
        model = Trip
        fields = ['name', 'start', 'end', 'budget']
        widgets = {'start': DATE, 'end': DATE, 'budget': MONEY}

    def clean(self):
        data = super().clean()
        if data.get('start') and data.get('end') and data['end'] < data['start']:
            self.add_error('end', 'End date must be after the start date.')
        return data


class InvestmentForm(UserForm):
    class Meta:
        model = Investment
        fields = ['name', 'label', 'invested', 'value']
        widgets = {'invested': MONEY, 'value': MONEY}


class HouseholdForm(UserForm):
    class Meta:
        model = Household
        fields = ['name', 'shared_budget']
        widgets = {'shared_budget': MONEY}


class InviteForm(forms.Form):
    email = forms.EmailField(help_text='They need an Extrackash account first.')

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        try:
            return User.objects.get(username=email)
        except User.DoesNotExist:
            raise forms.ValidationError('No Extrackash account uses this email yet.')


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'email']
        labels = {'first_name': 'Your name'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].required = True

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(username=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def save(self, commit=True):
        self.instance.username = self.cleaned_data['email']  # email is the login
        return super().save(commit)


class SignUpForm(UserCreationForm):
    """Sign up with name + email; the email is stored as the username."""

    first_name = forms.CharField(label='Your name', max_length=150, widget=forms.TextInput(attrs={'autocomplete': 'given-name'}))
    email = forms.EmailField(label='Email', widget=forms.EmailInput(attrs={'autocomplete': 'email'}))

    class Meta:
        model = User
        fields = ['first_name', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password2'].label = 'Confirm password'

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(username=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user


class EmailLoginForm(AuthenticationForm):
    username = forms.EmailField(label='Email', widget=forms.EmailInput(attrs={'autofocus': True, 'autocomplete': 'email'}))

    def clean(self):
        if self.cleaned_data.get('username'):
            self.cleaned_data['username'] = self.cleaned_data['username'].lower()
        return super().clean()
