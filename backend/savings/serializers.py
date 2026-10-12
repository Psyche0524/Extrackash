from rest_framework import serializers

from .models import SavingsGoal


class SavingsGoalSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavingsGoal
        fields = ['id', 'name', 'target_amount', 'current_amount', 'deadline']
        read_only_fields = ['id']

    def validate_target_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('Target amount must be greater than zero.')
        return value

    def validate_current_amount(self, value):
        if value < 0:
            raise serializers.ValidationError('Current amount cannot be negative.')
        return value
