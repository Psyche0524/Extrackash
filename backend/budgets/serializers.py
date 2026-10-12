from rest_framework import serializers

from .models import Budget


class BudgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Budget
        fields = ['id', 'category', 'amount', 'start_date', 'end_date']
        read_only_fields = ['id']

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('Amount must be greater than zero.')
        return value

    def validate_category(self, category):
        if category.user_id not in (None, self.context['request'].user.id):
            raise serializers.ValidationError('This category is not yours.')
        if category.type != 'expense':
            raise serializers.ValidationError('Budgets can only use expense categories.')
        return category

    def validate(self, data):
        start = data.get('start_date', getattr(self.instance, 'start_date', None))
        end = data.get('end_date', getattr(self.instance, 'end_date', None))
        if start and end and end < start:
            raise serializers.ValidationError('End date must be on or after the start date.')
        return data
