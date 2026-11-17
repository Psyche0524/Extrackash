from django import forms

from .models import Transaction


class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['kind', 'amount', 'description', 'category', 'date', 'note']
        widgets = {
            'kind': forms.RadioSelect,
            'date': forms.DateInput(attrs={'type': 'date'}),
            'amount': forms.NumberInput(attrs={'placeholder': '0.00', 'step': '0.01', 'inputmode': 'decimal'}),
        }

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if amount <= 0:
            raise forms.ValidationError('Amount must be more than 0.')
        return amount
