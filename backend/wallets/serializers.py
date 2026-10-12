from django.db.models import Sum
from rest_framework import serializers

from .models import Wallet


class WalletSerializer(serializers.ModelSerializer):
    current_balance = serializers.SerializerMethodField()

    class Meta:
        model = Wallet
        fields = ['id', 'name', 'starting_balance', 'current_balance', 'created_at']
        read_only_fields = ['id', 'created_at']

    def get_current_balance(self, wallet):
        totals = wallet.transactions.values('type').annotate(total=Sum('amount'))
        sums = {row['type']: row['total'] for row in totals}
        return wallet.starting_balance + (sums.get('income') or 0) - (sums.get('expense') or 0)
