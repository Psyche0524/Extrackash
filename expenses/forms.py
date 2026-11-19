from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from .models import Account, Budget, Contribution, Debt, Goal, Household, Investment, Transaction

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


class TransactionForm(UserForm):
    class Meta:
        model = Transaction
        fields = ['kind', 'amount', 'description', 'category', 'account', 'date', 'note', 'shared']
        widgets = {'kind': forms.RadioSelect, 'date': DATE, 'amount': MONEY}

    def __init__(self, user, *args, **kwargs):
        super().__init__(user, *args, **kwargs)
        self.fields['kind'].choices = Transaction.KINDS[:2]  # transfers have their own form
        if not user.households.exists():
            del self.fields['shared']

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if amount <= 0:
            raise forms.ValidationError('Amount must be more than 0.')
        return amount


class TransferForm(UserForm):
    class Meta:
        model = Transaction
        fields = ['account', 'to_account', 'amount', 'date', 'note']
        labels = {'account': 'From', 'to_account': 'To'}
        widgets = {'date': DATE, 'amount': MONEY}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['to_account'].required = True

    def clean_amount(self):
        return positive(self, 'amount')

    def clean(self):
        data = super().clean()
        if data.get('account') and data.get('account') == data.get('to_account'):
            raise forms.ValidationError('Pick two different accounts.')
        return data


class AccountForm(UserForm):
    class Meta:
        model = Account
        fields = ['name', 'kind', 'opening_balance', 'credit_limit', 'due_day']
        widgets = {'opening_balance': MONEY, 'credit_limit': MONEY}


class BudgetForm(UserForm):
    class Meta:
        model = Budget
        fields = ['category', 'limit']
        widgets = {'limit': MONEY}

    def __init__(self, user, *args, **kwargs):
        super().__init__(user, *args, **kwargs)
        self.user = user

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
